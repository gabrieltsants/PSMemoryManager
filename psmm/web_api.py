# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bridge between the web page (Pyodide, inside a Web Worker) and the core.

Every public function returns a JSON string:
    {"ok": true, ...}  or  {"ok": false, "error": "...", "kind": "..."}

Up to two cards can be open at once, in slots "A" and "B" (side-by-side
view). Each slot has its own undo history and saved/unsaved state.

Binary data (whole cards, exports, files to add) is exchanged through files
in the Pyodide in-memory file system, which the worker reads and writes
directly. The user's original file only changes when they save/download.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .core import saves as _saves
from .core import sdcard as _sdcard
from .core import convert as _convert
from .core.card import (
    CardError,
    Entry,
    ExistsError,
    MemoryCard,
    NoSpaceError,
    norm_path,
)
from .core.formats import FormatError, Layout
from .core.i18n import set_language as _set_language

WORK = Path("/psmm")
STAGING = WORK / "staging"  # JS writes files to add / saves to import here
INCOMING = WORK / "incoming.bin"  # JS writes the card to open here
EXPORT = WORK / "export.bin"  # and reads downloads from here
HISTORY_LIMIT_BYTES = 192 * 1024 * 1024  # per slot
SLOTS = ("A", "B")


@dataclass
class _Slot:
    card: MemoryCard | None = None
    history: list[bytes] = field(default_factory=list)
    version: int = 0  # incremented on every change
    saved_version: int = 0


_slots: dict[str, _Slot] = {s: _Slot() for s in SLOTS}


# ---------------------------------------------------------------------------
# helpers


def _slot(name: str) -> _Slot:
    if name not in _slots:
        raise CardError("err.bad_slot", slot=name)
    return _slots[name]


def _card(name: str) -> MemoryCard:
    c = _slot(name).card
    if c is None:
        raise CardError("err.no_card")
    return c


def _cards_dir(name: str) -> Path:
    return WORK / "cards" / name


def _entry_dict(e: Entry) -> dict:
    gid = e.game_id
    d = {
        "name": e.name,
        "path": e.path,
        "dir": e.is_dir,
        "size": e.size,
        "title": e.title,
        "created": e.created.isoformat() if e.created else None,
        "modified": e.modified.isoformat() if e.modified else None,
        "attrs": e.attributes(),
        "protected": e.protected,
        "ps1": e.is_ps1_save,
        "files": e.file_count,
        "serial": gid.serial if gid else None,
        "region": gid.region_name if gid else None,
        "regionCode": gid.region if gid else None,
    }
    if e.is_dir:
        d["children"] = [_entry_dict(c) for c in e.children]
        d["flat"] = all(not c.is_dir for c in e.children)
    return d


def _summary(name: str) -> dict:
    s = _slot(name)
    c = _card(name)
    i = c.info()
    f = i.format
    return {
        "slot": name,
        "card": {
            "name": c.path.name,
            "describe": f.describe(),
            "platform": f.platform.value,
            "ecc": f.layout is Layout.ECC,
            "origin": f.origin.label,
            "originId": f.origin.value,
            "sizeMB": f.nominal_mb,
            "fileSize": f.file_size,
            "total": i.total_bytes,
            "free": i.free_bytes,
            "used": i.used_bytes,
            "sizeMismatch": f.size_mismatch,
            "clusterSize": f.cluster_size,
            "game": _convert.guess_game_id(c, c.path.name),
        },
        "tree": [_entry_dict(e) for e in c.tree()],
        "canUndo": bool(s.history),
        "dirty": s.version != s.saved_version,
    }


def _result(fn, *args, **kwargs) -> str:
    try:
        out = fn(*args, **kwargs)
        payload = {"ok": True}
        if isinstance(out, dict):
            payload.update(out)
        return json.dumps(payload)
    except ExistsError as e:
        return json.dumps({"ok": False, "kind": "exists", "error": str(e)})
    except NoSpaceError as e:
        return json.dumps({"ok": False, "kind": "nospace", "error": str(e)})
    except FormatError as e:
        return json.dumps({"ok": False, "kind": "format", "error": str(e)})
    except CardError as e:
        return json.dumps({"ok": False, "kind": "card", "error": str(e)})
    except Exception as e:  # bug: include the type to make reports easier
        return json.dumps({"ok": False, "kind": "internal", "error": f"{type(e).__name__}: {e}"})


def _push_history(s: _Slot, data: bytes) -> None:
    s.history.append(data)
    total = sum(len(h) for h in s.history)
    while len(s.history) > 1 and total > HISTORY_LIMIT_BYTES:
        total -= len(s.history.pop(0))


def _edit(name: str, fn) -> dict:
    """Applies ``fn(editor)`` to the card in ``name`` as one undoable step."""
    s = _slot(name)
    c = _card(name)
    before = c.path.read_bytes()
    with c.edit() as ed:
        fn(ed)
        changes = list(ed.changes)
    if changes:
        _push_history(s, before)
        s.version += 1
    out = _summary(name)
    out["changes"] = changes
    return out


def _close(name: str) -> None:
    s = _slot(name)
    if s.card is not None:
        s.card.close()
    s.card = None
    s.history.clear()
    s.version = s.saved_version = 0
    shutil.rmtree(_cards_dir(name), ignore_errors=True)


def _prepare_slot(name: str) -> Path:
    _close(name)
    d = _cards_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename(name: str) -> str:
    return os.path.basename(name.replace("\\", "/")) or "card.mcd"


def _staged_files() -> list[Path]:
    return sorted(STAGING.iterdir()) if STAGING.exists() else []


# ---------------------------------------------------------------------------
# cards


def open_card(slot: str, name: str) -> str:
    """Opens the card that JS wrote to ``INCOMING`` in ``slot``."""

    def run():
        path = _prepare_slot(slot) / _safe_filename(name)
        shutil.move(str(INCOMING), path)
        try:
            _slot(slot).card = MemoryCard(path, make_backups=False)
        except Exception:
            _close(slot)
            raise
        return _summary(slot)

    return _result(run)


def new_card(slot: str, name: str, size_mb: int, ecc: bool) -> str:
    def run():
        path = _prepare_slot(slot) / _safe_filename(name)
        s = _slot(slot)
        s.card = MemoryCard.create(path, int(size_mb), ecc=bool(ecc))
        s.card.make_backups = False
        s.saved_version = -1  # a new card has not been saved yet
        return _summary(slot)

    return _result(run)


def close_card(slot: str) -> str:
    return _result(lambda: (_close(slot), {})[1])


def set_language(lang: str) -> str:
    """Changes the language of core messages ("en" or "pt")."""
    return _result(lambda: {"lang": _set_language(lang)})


def summary(slot: str) -> str:
    return _result(_summary, slot)


def card_file(slot: str) -> str:
    """Path (in the Pyodide FS) of the card in ``slot``, for JS to read and save."""

    def run():
        c = _card(slot)
        return {"path": str(c.path), "name": c.path.name}

    return _result(run)


def mark_saved(slot: str) -> str:
    def run():
        s = _slot(slot)
        s.saved_version = s.version
        return {"dirty": False}

    return _result(run)


def undo(slot: str) -> str:
    def run():
        s = _slot(slot)
        c = _card(slot)
        if not s.history:
            raise CardError("err.nothing_to_undo")
        data = s.history.pop()
        c.close()
        c.path.write_bytes(data)
        c.reload()
        s.version += 1  # differs from the saved state (unless it happens to match)
        return _summary(slot)

    return _result(run)


def check(slot: str) -> str:
    def run():
        ok, msgs = _card(slot).check()
        return {"healthy": ok, "messages": msgs}

    return _result(run)


# ---------------------------------------------------------------------------
# editing


def staging_dir() -> str:
    """Clears and returns the folder where JS writes files to add or import."""
    shutil.rmtree(STAGING, ignore_errors=True)
    STAGING.mkdir(parents=True)
    return str(STAGING)


def add_staged(slot: str, dest_dir: str, overwrite: bool = False) -> str:
    def apply(ed):
        items = _staged_files()
        if not items:
            raise CardError("err.nothing_to_add")
        for item in items:
            ed.add_local(item, norm_path(dest_dir), overwrite=bool(overwrite))

    return _result(_edit, slot, apply)


def mkdir(slot: str, path: str) -> str:
    return _result(_edit, slot, lambda ed: ed.mkdir(path))


def remove(slot: str, paths_json: str) -> str:
    paths = json.loads(paths_json)

    def apply(ed):
        # parents before children: removing a parent already removes its children
        done: list[str] = []
        for p in sorted((norm_path(p) for p in paths), key=len):
            if any(p == d or p.startswith(d.rstrip("/") + "/") for d in done):
                continue
            ed.remove(p)
            done.append(p)

    return _result(_edit, slot, apply)


def rename(slot: str, path: str, new_name: str) -> str:
    return _result(_edit, slot, lambda ed: ed.rename(path, new_name))


def copy_items(src_slot: str, paths_json: str, dst_slot: str, dest_dir: str = "/", overwrite: bool = False) -> str:
    """Copies items from the card in ``src_slot`` to the card in ``dst_slot``."""

    def run():
        if src_slot == dst_slot:
            raise CardError("err.same_card")
        src = _card(src_slot)
        paths = [norm_path(p) for p in json.loads(paths_json)]
        if not paths:
            raise CardError("err.nothing_selected")
        return _edit(dst_slot, lambda ed: ed.copy_from(src, paths, dest_dir, bool(overwrite)))

    return _result(run)


# ---------------------------------------------------------------------------
# saves


def inspect_staged_saves() -> str:
    """Parses the save files in ``STAGING`` (without importing them)."""

    def run():
        items = []
        for p in _staged_files():
            try:
                sf, fmt = _saves.load(p.read_bytes(), p.name)
                i = _saves.info(sf, fmt)
                items.append({"file": p.name, "ok": True, "name": i.name, "title": i.title,
                              "files": i.files, "size": i.size, "format": i.format_name})
            except CardError as e:
                items.append({"file": p.name, "ok": False, "error": str(e)})
        return {"saves": items}

    return _result(run)


def import_staged_saves(slot: str, overwrite: bool = False) -> str:
    """Imports every save file in ``STAGING`` into the root of the card in ``slot``."""

    def apply(ed):
        items = _staged_files()
        if not items:
            raise CardError("err.nothing_to_add")
        loaded = [_saves.load(p.read_bytes(), p.name)[0] for p in items]
        for sf in loaded:
            ed.import_save(sf, overwrite=bool(overwrite))

    return _result(_edit, slot, apply)


def export_saves(slot: str, paths_json: str, fmt: str = "psu") -> str:
    """Exports save folders as .psu/.max into ``EXPORT`` (one file, or a .zip for several)."""

    def run():
        c = _card(slot)
        paths = [norm_path(p) for p in json.loads(paths_json)]
        if not paths:
            raise CardError("err.nothing_selected")
        files = []
        for p in paths:
            sf = c.export_save(p)
            files.append((_saves.export_filename(sf, fmt), _saves.dump(sf, fmt)))
        if len(files) == 1:
            name, data = files[0]
            kind = "file"
        else:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                used: set[str] = set()
                for fname, data in files:
                    base, n = fname, 1
                    while fname in used:
                        fname = f"{Path(base).stem}-{n}{Path(base).suffix}"
                        n += 1
                    used.add(fname)
                    z.writestr(fname, data)
            name, data, kind = f"{c.path.stem}-saves-{fmt}.zip", buf.getvalue(), "zip"
        EXPORT.write_bytes(data)
        return {"path": str(EXPORT), "name": name, "kind": kind, "size": len(data)}

    return _result(run)


# ---------------------------------------------------------------------------
# raw export


def export(slot: str, paths_json: str) -> str:
    """Writes the raw export to ``EXPORT``. A single file is exported as-is; anything else becomes a .zip."""

    def run():
        c = _card(slot)
        paths = [norm_path(p) for p in json.loads(paths_json)]
        if not paths:
            raise CardError("err.nothing_selected")
        if len(paths) == 1 and paths[0] != "/" and not c.is_dir(paths[0]):
            name, data = paths[0].rsplit("/", 1)[1], c.read_file(paths[0])
            kind = "file"
        else:
            if len(paths) == 1 and paths[0] != "/":
                name = paths[0].rsplit("/", 1)[1] + ".zip"
            else:
                name = c.path.stem + "-export.zip"
            data = c.export_zip(paths)
            kind = "zip"
        EXPORT.write_bytes(data)
        return {"path": str(EXPORT), "name": name, "kind": kind, "size": len(data)}

    return _result(run)


# ---------------------------------------------------------------------------
# Gen2 SD card (the page reads/writes the SD; Python does layout and INI logic)

_sd_files: list[dict] = []
_sd_texts: dict[str, str] = {}


def _sd_layout():
    return _sdcard.parse_listing(_sd_files, _sd_texts)


def sd_load(files_json: str, texts_json: str) -> str:
    """Receives the SD listing (paths + sizes) and INI texts; returns the layout."""

    def run():
        global _sd_files, _sd_texts
        _sd_files = json.loads(files_json)
        _sd_texts = json.loads(texts_json)
        layout = _sd_layout()
        settings_text = _sd_texts.get(_sdcard.SETTINGS_FILE, "")
        out = _sdcard.layout_to_dict(layout)
        out["settings"] = _sdcard.read_settings(settings_text)
        out["game2folder"] = _sdcard.read_game2folder(_sd_texts.get(_sdcard.GAME2FOLDER_FILE, ""))
        out["defaultSizeMB"] = _sdcard.default_card_size_mb(settings_text)
        out["settingsPath"] = _sdcard.SETTINGS_FILE
        out["game2folderPath"] = _sdcard.GAME2FOLDER_FILE
        return out

    return _result(run)


def sd_write_settings(values_json: str) -> str:
    def run():
        try:
            text = _sdcard.write_settings(_sd_texts.get(_sdcard.SETTINGS_FILE, ""), json.loads(values_json))
        except ValueError as e:
            raise CardError("sd.bad_setting", error=e) from e
        return {"path": _sdcard.SETTINGS_FILE, "text": text}

    return _result(run)


def sd_write_channel_names(ini_path: str, names_json: str) -> str:
    def run():
        names = {int(k): v for k, v in json.loads(names_json).items()}
        try:
            text = _sdcard.write_channel_names(_sd_texts.get(ini_path, ""), names)
        except ValueError as e:
            raise CardError("sd.bad_name", error=e) from e
        return {"path": ini_path, "text": text}

    return _result(run)


def sd_remove_channel_name(ini_path: str, channel: int) -> str:
    """After a channel is deleted: its name, if any, is removed from the INI."""

    def run():
        text = _sdcard.remove_channel_name(_sd_texts.get(ini_path, ""), int(channel))
        return {"path": ini_path, "text": text} if text is not None else {"path": None}

    return _result(run)


def sd_write_game2folder(rows_json: str) -> str:
    def run():
        try:
            text = _sdcard.write_game2folder(_sd_texts.get(_sdcard.GAME2FOLDER_FILE, ""), json.loads(rows_json))
        except ValueError as e:
            raise CardError("sd.bad_folder", error=e) from e
        return {"path": _sdcard.GAME2FOLDER_FILE, "text": text}

    return _result(run)


_SD_CREATABLE = ("PS2", "COH")  # PS1 cards come in phase 5; Conquest cards use their own format


def sd_plan_card(variant: str, game_id: str = "") -> str:
    """Where a new card goes (next CardN, or a game ID folder)."""

    def run():
        if variant.upper() not in _SD_CREATABLE:
            raise CardError("sd.variant_unsupported", variant=variant)
        try:
            return _sdcard.plan_new_card(_sd_layout(), variant, game_id or None)
        except FileExistsError as e:
            raise CardError("sd.folder_exists", folder=str(e)) from e
        except ValueError as e:
            raise CardError("sd.bad_game_id", game=game_id) from e

    return _result(run)


def sd_plan_channel(variant: str, folder: str) -> str:
    def run():
        if variant.upper() not in _SD_CREATABLE:
            raise CardError("sd.variant_unsupported", variant=variant)
        try:
            return _sdcard.plan_new_channel(_sd_layout(), variant, folder)
        except FileNotFoundError as e:
            raise CardError("err.not_found", path=str(e)) from e
        except ValueError as e:
            raise CardError("sd.no_channels", max=_sdcard.MAX_CHANNELS) from e

    return _result(run)


def blank_card(size_mb: int, ecc: bool = False) -> str:
    """Formats an empty PS2 card into ``EXPORT`` (the page writes it to the SD)."""

    def run():
        tmp = WORK / "blank.mcd"
        tmp.unlink(missing_ok=True)
        MemoryCard.create(tmp, int(size_mb), ecc=bool(ecc)).close()
        os.replace(tmp, EXPORT)
        return {"path": str(EXPORT), "name": "blank.mcd", "size": EXPORT.stat().st_size}

    return _result(run)


# ---------------------------------------------------------------------------
# Whole cards: import (OPL VMCs, other cards), convert, split by game


def _staged_card(name: str) -> MemoryCard:
    path = STAGING / os.path.basename(name)
    if not path.is_file():
        raise CardError("err.not_found", path=name)
    return MemoryCard(path, make_backups=False)


def _zip_cards(items: list[tuple[str, Path]], layout: str = "gen2") -> bytes:
    """(game, card file) pairs -> .zip ready to extract.

    gen2: Gen2 SD card layout, MemoryCards/PS2/<game>/<game>-N.mcd (N = channel)
    opl:  OPL layout, VMC/<CODE_123.45>_N.bin (N = 0, 1... like OPL's own names)
    """
    buf = io.BytesIO()
    used: dict[str, int] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for game, path in items:
            n = used.get(game, 0)
            used[game] = n + 1
            if layout == "opl":
                z.write(path, "VMC/" + _convert.opl_vmc_name(game, n))
            else:
                z.write(path, _sdcard.channel_path("PS2", game, n + 1))
    return buf.getvalue()


def inspect_staged_cards() -> str:
    """Describes the card images in ``STAGING`` (format, game guess, saves)."""

    def run():
        cards = []
        for p in _staged_files():
            try:
                with _staged_card(p.name) as c:
                    groups, others = _convert.group_by_game(c)
                    saves = [
                        {"name": e.name, "title": e.title, "serial": e.game_id.serial if e.game_id else None}
                        for e in c.list_dir("/")
                    ]
                    cards.append({
                        "file": p.name, "ok": True, "describe": c.format.describe(),
                        "ecc": c.format.layout is Layout.ECC, "sizeMB": c.format.nominal_mb,
                        "game": _convert.guess_game_id(c, p.name), "games": [g.game for g in groups],
                        "entries": saves, "used": c.total_bytes() - c.free_bytes(),
                    })
            except (CardError, FormatError) as e:
                cards.append({"file": p.name, "ok": False, "error": str(e)})
        return {"cards": cards}

    return _result(run)


def import_staged_cards(slot: str, files_json: str, overwrite: bool = False) -> str:
    """Copies everything from the staged cards in ``files_json`` into the card in ``slot`` (merge)."""

    def apply(ed):
        for name in json.loads(files_json):
            with _staged_card(name) as src:
                ed.copy_from(src, ["/"], "/", overwrite=bool(overwrite))

    return _result(_edit, slot, apply)


def prepare_staged_card(name: str) -> str:
    """A staged card as a Gen2 card (no ECC, same size) in ``EXPORT``."""

    def run():
        with _staged_card(name) as src:
            _convert.convert(src, EXPORT, ecc=False)
        return {"path": str(EXPORT), "size": EXPORT.stat().st_size}

    return _result(run)


def staged_cards_zip(items_json: str, layout: str = "gen2") -> str:
    """``[{"file", "game"}]`` -> .zip for the Gen2 SD card or for OPL (``layout``), in ``EXPORT``."""

    def run():
        items = []
        out_dir = WORK / "zipcards"
        shutil.rmtree(out_dir, ignore_errors=True)
        out_dir.mkdir(parents=True)
        for i, it in enumerate(json.loads(items_json)):
            game = _sdcard.normalize_game_id(it["game"] or "")
            if not game:
                raise CardError("conv.no_game_id", name=it["file"])
            dest = out_dir / f"{i}.mcd"
            with _staged_card(it["file"]) as src:
                _convert.convert(src, dest, ecc=False)
            items.append((game, dest))
        EXPORT.write_bytes(_zip_cards(items, layout))
        shutil.rmtree(out_dir, ignore_errors=True)
        name = "OPL-VMC.zip" if layout == "opl" else "Gen2-MemoryCards.zip"
        return {"path": str(EXPORT), "name": name, "kind": "zip", "size": EXPORT.stat().st_size}

    return _result(run)


def sd_plan_import(game: str, size: int) -> str:
    """Where a card for ``game`` goes on the SD: a new game folder, or the next channel if it exists.

    The planned file is added to the listing right away, so several cards for
    the same game in one batch get channels 1, 2, 3...
    """

    def run():
        gid = _sdcard.normalize_game_id(game or "")
        if not gid:
            raise CardError("sd.bad_game_id", game=game)
        layout = _sd_layout()
        v = layout.variant("PS2")
        existing = v.find(gid) if v else None
        if existing:
            try:
                plan = _sdcard.plan_new_channel(layout, "PS2", existing.folder)
            except ValueError as e:
                raise CardError("sd.no_channels", max=_sdcard.MAX_CHANNELS) from e
            plan["existing"] = True
        else:
            plan = _sdcard.plan_new_card(layout, "PS2", gid)
            plan["existing"] = False
        _sd_files.append({"path": plan["path"], "size": int(size)})
        return plan

    return _result(run)


def convert_card(slot: str, target: str, size_mb: int = 0) -> str:
    """The card in ``slot`` converted to ``target`` (gen2/opl/pcsx2/mcp2) and size, in ``EXPORT``."""

    def run():
        if target not in _convert.TARGETS:
            raise CardError("save.bad_format", format=target)
        c = _card(slot)
        _convert.convert(c, EXPORT, ecc=_convert.TARGETS[target][1], size_mb=int(size_mb) or None)
        return {"path": str(EXPORT), "name": _convert.output_name(c.path.name, target),
                "kind": "file", "size": EXPORT.stat().st_size}

    return _result(run)


def split_card(slot: str, size_mb: int, include_others: bool, mode: str) -> str:
    """One card per game. mode "files": cards left in WORK/split (for the SD);
    "zip": Gen2 SD layout .zip in EXPORT; "zip-opl": OPL VMC/ layout .zip in EXPORT."""

    def run():
        out_dir = WORK / "split"
        shutil.rmtree(out_dir, ignore_errors=True)
        cards = _convert.split_by_game(_card(slot), out_dir, size_mb=int(size_mb), include_others=bool(include_others))
        if mode in ("zip", "zip-opl"):
            layout = "opl" if mode == "zip-opl" else "gen2"
            EXPORT.write_bytes(_zip_cards([(c["game"], Path(c["path"])) for c in cards], layout))
            shutil.rmtree(out_dir, ignore_errors=True)
            name = f"{_card(slot).path.stem}-{'OPL-VMC' if layout == 'opl' else 'Gen2'}.zip"
            return {"path": str(EXPORT), "name": name, "kind": "zip",
                    "size": EXPORT.stat().st_size, "cards": [{k: v for k, v in c.items() if k != "path"} for c in cards]}
        return {"cards": cards}

    return _result(run)


def resize_card(slot: str, size_mb: int) -> str:
    """Resizes the open card in place, as one undoable change (Save writes it back)."""

    def run():
        s = _slot(slot)
        c = _card(slot)
        size_mb_i = int(size_mb)
        if size_mb_i == c.format.nominal_mb:
            raise CardError("conv.same_size", size=size_mb_i)
        before = c.path.read_bytes()
        tmp = c.path.with_name(f".{c.path.name}.resize")
        _convert.convert(c, tmp, ecc=c.format.layout is Layout.ECC, size_mb=size_mb_i)
        c.close()
        os.replace(tmp, c.path)
        c.reload()
        _push_history(s, before)
        s.version += 1
        return _summary(slot)

    return _result(run)


def split_preview(slot: str) -> str:
    def run():
        groups, others = _convert.group_by_game(_card(slot))
        return {"games": [{"game": g.game, "titles": g.titles} for g in groups],
                "others": [p.rsplit("/", 1)[1] for p in others]}

    return _result(run)
