# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""PSxMemCard Gen2 / SD2PSX (sd2psXtd firmware) SD card layout.

The SD card looks like this::

    .sd2psx/settings.ini            general settings
    .sd2psx/Game2Folder.ini         optional game ID -> folder mapping
    MemoryCards/PS2/Card1/Card1-1.mcd        card 1, channel 1
    MemoryCards/PS2/Card1/Card1.ini          channel names / per-card settings
    MemoryCards/PS2/BOOT/BootCard-1.mcd      boot card (files use the "BootCard" prefix)
    MemoryCards/PS2/BOOT/BootCard.ini
    MemoryCards/PS2/SLUS-20963/SLUS-20963-1.mcd   card created for a game ID
    MemoryCards/PS1/...                      PS1 cards (same scheme)
    MemoryCards/COH/... , MemoryCards/SC2/...  arcade / Conquest variants

This module only works on a *listing* (relative paths + sizes) and on the
text of the INI files, so the same code serves the browser (which reads the
SD through the File System Access API) and local folders (command line).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT_CARDS = "MemoryCards"
CONFIG_DIR = ".sd2psx"
SETTINGS_FILE = f"{CONFIG_DIR}/settings.ini"
GAME2FOLDER_FILE = f"{CONFIG_DIR}/Game2Folder.ini"
MAX_CHANNELS = 8
PS2_SIZES_MB = (1, 2, 4, 8, 16, 32, 64, 128)
PS1_CARD_SIZE = 128 * 1024

VARIANT_LABELS = {
    "PS2": "PS2",
    "PS1": "PS1",
    "COH": "PS2 Arcade (COH)",
    "SC2": "SoulCalibur II Conquest",
}
VARIANT_ORDER = ["PS2", "PS1", "COH", "SC2"]

_CHANNEL_RE = re.compile(r"^(?P<prefix>.+)-(?P<ch>\d+)\.mcd$", re.IGNORECASE)
_CARDN_RE = re.compile(r"^Card(?P<n>\d+)$", re.IGNORECASE)
# Game IDs as folders: SLUS-20963, SCES-53851, SLPM-65530... (letters, separator, digits)
_GAME_ID_RE = re.compile(r"^(?P<code>[A-Z]{4})[-_ ]?(?P<num>\d{3})\.?(?P<num2>\d{2})$")
_SAFE_FOLDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()\-]{0,63}$")


# ---------------------------------------------------------------------------
# INI files (order, comments and unknown keys are preserved)


class IniFile:
    """Minimal INI reader/writer in the format the sd2psXtd firmware uses."""

    def __init__(self, text: str = ""):
        # each line: ("section", name) | ("kv", key, value) | ("raw", text)
        self.lines: list[tuple] = []
        for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = raw.strip()
            if line.startswith("[") and line.endswith("]"):
                self.lines.append(("section", line[1:-1].strip()))
            elif "=" in line and not line.startswith((";", "#")):
                k, v = line.split("=", 1)
                self.lines.append(("kv", k.strip(), v.strip()))
            else:
                self.lines.append(("raw", raw.rstrip()))
        # drop trailing blank lines; serialize() adds the ending itself
        while self.lines and self.lines[-1] == ("raw", ""):
            self.lines.pop()

    def sections(self) -> list[str]:
        return [ln[1] for ln in self.lines if ln[0] == "section"]

    def _section_range(self, section: str) -> tuple[int, int] | None:
        start = None
        for i, ln in enumerate(self.lines):
            if ln[0] == "section":
                if start is not None:
                    return start, i
                if ln[1].lower() == section.lower():
                    start = i + 1
        return (start, len(self.lines)) if start is not None else None

    def items(self, section: str) -> list[tuple[str, str]]:
        r = self._section_range(section)
        if r is None:
            return []
        return [(ln[1], ln[2]) for ln in self.lines[r[0]:r[1]] if ln[0] == "kv"]

    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        for k, v in self.items(section):
            if k.lower() == key.lower():
                return v
        return default

    def set(self, section: str, key: str, value: str) -> None:
        r = self._section_range(section)
        if r is None:
            self.lines.append(("section", section))
            self.lines.append(("kv", key, value))
            return
        last_kv = r[0] - 1
        for i in range(r[0], r[1]):
            ln = self.lines[i]
            if ln[0] == "kv":
                last_kv = i
                if ln[1].lower() == key.lower():
                    self.lines[i] = ("kv", ln[1], value)
                    return
        self.lines.insert(last_kv + 1, ("kv", key, value))

    def remove(self, section: str, key: str) -> None:
        r = self._section_range(section)
        if r is None:
            return
        self.lines[r[0]:r[1]] = [
            ln for ln in self.lines[r[0]:r[1]] if not (ln[0] == "kv" and ln[1].lower() == key.lower())
        ]

    def replace_section(self, section: str, items: list[tuple[str, str]]) -> None:
        """Replaces all keys of ``section`` (creating it if needed), keeping its position."""
        r = self._section_range(section)
        new = [("kv", k, v) for k, v in items]
        if r is None:
            self.lines.append(("section", section))
            self.lines.extend(new)
        else:
            self.lines[r[0]:r[1]] = new + [ln for ln in self.lines[r[0]:r[1]] if ln[0] == "raw" and ln[1].strip()]

    def serialize(self) -> str:
        out = []
        for ln in self.lines:
            if ln[0] == "section":
                out.append(f"[{ln[1]}]")
            elif ln[0] == "kv":
                out.append(f"{ln[1]}={ln[2]}")
            else:
                out.append(ln[1])
        # the firmware docs ask for an empty line at the end of the file
        return "\n".join(out) + "\n\n"


# ---------------------------------------------------------------------------
# settings.ini


@dataclass(frozen=True)
class SettingSpec:
    section: str
    key: str
    kind: str  # "onoff" | "choice" | "int"
    choices: tuple[str, ...] = ()
    default: str = ""


SETTINGS_SPEC: tuple[SettingSpec, ...] = (
    SettingSpec("General", "Mode", "choice", ("PS2", "PS1"), "PS2"),
    SettingSpec("General", "FlippedScreen", "onoff", default="OFF"),
    SettingSpec("PS1", "Autoboot", "onoff", default="ON"),
    SettingSpec("PS1", "GameID", "onoff", default="ON"),
    SettingSpec("PS1", "EnableControllerCombo", "onoff", default="ON"),
    SettingSpec("PS2", "Autoboot", "onoff", default="ON"),
    SettingSpec("PS2", "GameID", "onoff", default="ON"),
    SettingSpec("PS2", "CardSize", "choice", tuple(str(s) for s in PS2_SIZES_MB), "8"),
    SettingSpec("PS2", "Variant", "choice", ("RETAIL", "PROTO", "ARCADE", "CONQUEST"), "RETAIL"),
)


def read_settings(text: str) -> dict:
    """Known settings with their current (or default) values, plus extra keys."""
    ini = IniFile(text)
    known = []
    for s in SETTINGS_SPEC:
        value = ini.get(s.section, s.key)
        known.append({
            "section": s.section, "key": s.key, "kind": s.kind, "choices": list(s.choices),
            "default": s.default, "value": value if value is not None else s.default, "present": value is not None,
        })
    spec_keys = {(s.section.lower(), s.key.lower()) for s in SETTINGS_SPEC}
    extra = [
        {"section": sec, "key": k, "value": v}
        for sec in ini.sections() for k, v in ini.items(sec) if (sec.lower(), k.lower()) not in spec_keys
    ]
    return {"settings": known, "extra": extra}


def write_settings(text: str, values: dict[str, str]) -> str:
    """Applies ``{"Section.Key": value}`` to settings.ini text, keeping everything else."""
    ini = IniFile(text)
    specs = {f"{s.section}.{s.key}": s for s in SETTINGS_SPEC}
    for name, value in values.items():
        spec = specs.get(name)
        if spec is None:
            raise ValueError(f"unknown setting {name}")
        value = str(value).strip()
        if spec.kind == "onoff":
            value = "ON" if value.upper() in ("ON", "TRUE", "1") else "OFF"
        elif spec.kind == "choice" and value not in spec.choices:
            raise ValueError(f"invalid value for {name}: {value}")
        ini.set(spec.section, spec.key, value)
    return ini.serialize()


def default_card_size_mb(settings_text: str) -> int:
    try:
        size = int(IniFile(settings_text).get("PS2", "CardSize", "8"))
    except ValueError:
        return 8
    return size if size in PS2_SIZES_MB else 8


# ---------------------------------------------------------------------------
# Channel names (CardN.ini / BootCard.ini / <GameID>.ini)


def read_channel_names(text: str) -> dict[int, str]:
    names = {}
    for k, v in IniFile(text).items("ChannelName"):
        if k.isdigit() and v:
            names[int(k)] = v
    return names


def write_channel_names(text: str, names: dict[int, str]) -> str:
    ini = IniFile(text)
    items = [(str(ch), name.strip()) for ch, name in sorted(names.items()) if name and name.strip()]
    for _, name in items:
        if "\n" in name or "\r" in name:
            raise ValueError("channel names must be a single line")
    ini.replace_section("ChannelName", items)
    return ini.serialize()


def remove_channel_name(text: str, channel: int) -> str | None:
    """INI text without the name of ``channel``; None if there was nothing to remove."""
    names = read_channel_names(text)
    if channel not in names:
        return None
    del names[channel]
    return write_channel_names(text, names)


# ---------------------------------------------------------------------------
# Game2Folder.ini


def read_game2folder(text: str) -> list[dict]:
    ini = IniFile(text)
    out = []
    for sec in ini.sections():
        if sec.upper() in ("PS1", "PS2"):
            out += [{"platform": sec.upper(), "game": k, "folder": v} for k, v in ini.items(sec)]
    return out


def write_game2folder(text: str, rows: list[dict]) -> str:
    ini = IniFile(text)
    for platform in ("PS1", "PS2"):
        items = []
        for r in rows:
            if r.get("platform", "").upper() != platform:
                continue
            game = normalize_game_id(r["game"]) or r["game"].strip().upper()
            folder = r["folder"].strip()
            if not game or not folder:
                continue
            check_folder_name(folder)
            items.append((game, folder))
        if items or platform in [s.upper() for s in ini.sections()]:
            ini.replace_section(platform, items)
    return ini.serialize()


# ---------------------------------------------------------------------------
# Names and paths


def normalize_game_id(text: str) -> str | None:
    """'slus_209.63' / 'SLUS20963' -> 'SLUS-20963'; None if it does not look like a game ID."""
    m = _GAME_ID_RE.match(text.strip().upper())
    if not m:
        return None
    return f"{m.group('code')}-{m.group('num')}{m.group('num2')}"


def check_folder_name(name: str) -> str:
    if not _SAFE_FOLDER_RE.match(name):
        raise ValueError(f"invalid folder name: {name!r}")
    return name


def file_prefix(folder: str) -> str:
    """The BOOT folder stores BootCard-N.mcd; every other folder uses its own name."""
    return "BootCard" if folder.upper() == "BOOT" else folder


def channel_path(variant: str, folder: str, channel: int) -> str:
    return f"{ROOT_CARDS}/{variant}/{folder}/{file_prefix(folder)}-{channel}.mcd"


def ini_path(variant: str, folder: str) -> str:
    return f"{ROOT_CARDS}/{variant}/{folder}/{file_prefix(folder)}.ini"


# ---------------------------------------------------------------------------
# Layout


@dataclass
class Channel:
    number: int
    path: str
    size: int
    name: str = ""


@dataclass
class CardFolder:
    variant: str
    folder: str
    kind: str  # "boot" | "numbered" | "game" | "other"
    index: int | None = None  # N for CardN
    channels: list[Channel] = field(default_factory=list)
    ini: str | None = None  # path of the channel-name INI, if present
    others: list[str] = field(default_factory=list)  # unrelated files (splash images...)
    names: dict[int, str] = field(default_factory=dict)  # every name in the INI, even without a file

    @property
    def label(self) -> str:
        if self.kind == "boot":
            return "BOOT"
        if self.kind == "numbered":
            return f"Card {self.index}"
        return self.folder

    def next_channel(self) -> int | None:
        used = {c.number for c in self.channels}
        for n in range(1, MAX_CHANNELS + 1):
            if n not in used:
                return n
        return None


@dataclass
class Variant:
    name: str
    folders: list[CardFolder] = field(default_factory=list)

    @property
    def label(self) -> str:
        return VARIANT_LABELS.get(self.name.upper(), self.name)

    @property
    def platform(self) -> str:
        return "PS1" if self.name.upper() == "PS1" else "PS2"

    def next_card_index(self) -> int:
        used = {f.index for f in self.folders if f.index is not None}
        n = 1
        while n in used:
            n += 1
        return n

    def find(self, folder: str) -> CardFolder | None:
        return next((f for f in self.folders if f.folder.lower() == folder.lower()), None)


@dataclass
class Layout:
    variants: list[Variant]
    has_settings: bool
    has_game2folder: bool
    root_ok: bool  # MemoryCards/ or .sd2psx/ found

    def variant(self, name: str) -> Variant | None:
        return next((v for v in self.variants if v.name.lower() == name.lower()), None)


def _folder_kind(folder: str) -> tuple[str, int | None]:
    if folder.upper() == "BOOT":
        return "boot", None
    m = _CARDN_RE.match(folder)
    if m:
        return "numbered", int(m.group("n"))
    if normalize_game_id(folder):
        return "game", None
    return "other", None


def parse_listing(files: list[dict], ini_texts: dict[str, str] | None = None) -> Layout:
    """Builds the layout from ``[{"path": "MemoryCards/PS2/Card1/Card1-1.mcd", "size": 8388608}, ...]``.

    ``ini_texts`` maps INI paths to their text (used for channel names).
    Paths are relative to the SD root and use "/".
    """
    ini_texts = ini_texts or {}
    variants: dict[str, Variant] = {}
    has_settings = has_g2f = False
    root_ok = False
    for f in files:
        path = f["path"].replace("\\", "/").strip("/")
        parts = path.split("/")
        low = path.lower()
        if low == SETTINGS_FILE.lower():
            has_settings = True
        elif low == GAME2FOLDER_FILE.lower():
            has_g2f = True
        if parts[0].lower() in (ROOT_CARDS.lower(), CONFIG_DIR):
            root_ok = True
        if len(parts) != 4 or parts[0].lower() != ROOT_CARDS.lower():
            continue
        _, vname, folder, fname = parts
        v = variants.setdefault(vname.upper(), Variant(vname))
        cf = v.find(folder)
        if cf is None:
            kind, index = _folder_kind(folder)
            cf = CardFolder(variant=vname, folder=folder, kind=kind, index=index)
            v.folders.append(cf)
        m = _CHANNEL_RE.match(fname)
        if m and m.group("prefix").lower() == file_prefix(folder).lower():
            cf.channels.append(Channel(number=int(m.group("ch")), path=path, size=int(f.get("size", 0))))
        elif fname.lower() == f"{file_prefix(folder)}.ini".lower():
            cf.ini = path
        else:
            cf.others.append(path)

    for v in variants.values():
        for cf in v.folders:
            cf.channels.sort(key=lambda c: c.number)
            names = read_channel_names(ini_texts.get(cf.ini, "")) if cf.ini else {}
            cf.names = names
            for c in cf.channels:
                c.name = names.get(c.number, "")
        # BOOT first, then CardN by number, then game folders / others by name
        order = {"boot": 0, "numbered": 1, "game": 2, "other": 3}
        v.folders.sort(key=lambda f: (order[f.kind], f.index or 0, f.folder.lower()))

    ordered = sorted(
        variants.values(),
        key=lambda v: (VARIANT_ORDER.index(v.name.upper()) if v.name.upper() in VARIANT_ORDER else 99, v.name),
    )
    return Layout(variants=ordered, has_settings=has_settings, has_game2folder=has_g2f, root_ok=root_ok)


def layout_to_dict(layout: Layout) -> dict:
    return {
        "rootOk": layout.root_ok,
        "hasSettings": layout.has_settings,
        "hasGame2Folder": layout.has_game2folder,
        "variants": [
            {
                "name": v.name, "label": v.label, "platform": v.platform, "nextIndex": v.next_card_index(),
                "folders": [
                    {
                        "folder": f.folder, "label": f.label, "kind": f.kind, "index": f.index,
                        "ini": f.ini, "iniPath": ini_path(v.name, f.folder), "nextChannel": f.next_channel(),
                        "names": {str(k): n for k, n in f.names.items()},
                        "channels": [{"number": c.number, "path": c.path, "size": c.size, "name": c.name} for c in f.channels],
                    }
                    for f in v.folders
                ],
            }
            for v in layout.variants
        ],
    }


def plan_new_card(layout: Layout, variant: str, game_id: str | None = None) -> dict:
    """Where a new card goes: a new CardN folder, or a folder for ``game_id``."""
    v = layout.variant(variant)
    if game_id:
        gid = normalize_game_id(game_id)
        if gid is None:
            raise ValueError(f"not a game ID: {game_id!r}")
        if v and v.find(gid):
            raise FileExistsError(gid)
        folder = gid
    else:
        n = v.next_card_index() if v else 1
        folder = f"Card{n}"
    return {"variant": variant, "folder": folder, "channel": 1, "path": channel_path(variant, folder, 1)}


def plan_new_channel(layout: Layout, variant: str, folder: str) -> dict:
    v = layout.variant(variant)
    cf = v.find(folder) if v else None
    if cf is None:
        raise FileNotFoundError(f"{variant}/{folder}")
    n = cf.next_channel()
    if n is None:
        raise ValueError("all channels in use")
    size = cf.channels[0].size if cf.channels else 0
    return {"variant": variant, "folder": cf.folder, "channel": n, "path": channel_path(variant, cf.folder, n), "size": size}


def scan_local(root: str | Path) -> tuple[list[dict], dict[str, str]]:
    """Lists a local SD folder (command line/tests): files under MemoryCards/ and .sd2psx/, and INI texts."""
    root = Path(root)
    files: list[dict] = []
    texts: dict[str, str] = {}
    for top in (ROOT_CARDS, CONFIG_DIR):
        base = root / top
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            files.append({"path": rel, "size": p.stat().st_size})
            if p.suffix.lower() == ".ini":
                texts[rel] = p.read_text(encoding="utf-8", errors="replace")
    return files, texts
