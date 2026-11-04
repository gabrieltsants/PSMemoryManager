# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""High-level access to a PS2 memory card.

Uses mymc++ (GPLv3) as a library for the file system. Every change goes
through :meth:`MemoryCard.edit`, which:

1. copies the card to a temporary file in the same folder;
2. applies the changes to the copy;
3. runs the integrity check on the copy;
4. backs up the original to the user data folder;
5. atomically replaces the original with the copy (``os.replace``).

If any step fails, the original is left untouched.
"""

from __future__ import annotations

import array
import contextlib
import io
import math
import sys
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from mymcplusplus import ps2mc as _ps2mc
from mymcplusplus import ps2iconsys as _iconsys
from mymcplusplus.ps2mc_dir import (
    PS2MC_DIRENT_LENGTH,
    unpack_dirent,
    DF_DIR,
    DF_EXISTS,
    DF_HIDDEN,
    DF_PROTECTED,
    DF_PSX,
    DF_POCKETSTN,
    tod_to_time,
)

from . import backup as _backup
from . import ecc as _ecc  # noqa: F401  (installs the fast ECC into mymc++)
from . import saves as _saves
from .i18n import MESSAGES, LocalizedError, t
from .formats import CardFormat, FormatError, Layout, Platform, detect

MAX_NAME_LEN = 32
_BAD_NAME_CHARS = set('/\\?*:"<>|')
_WIN_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WIN_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# Save folder name: B + region + game code + rest
# ex.: BASLUS-20963GTA, BESLES-52541, BISLPM-65530
_SAVE_DIR_RE = re.compile(r"^B([A-Z])([A-Z]{4})-?(\d{5})(.*)$")
_REGIONS = {"A": "US", "E": "EU", "I": "JP", "K": "KR", "C": "CN"}


class CardError(LocalizedError):
    """Memory card operation error (message key + parameters)."""


class NoSpaceError(CardError):
    pass


class ExistsError(CardError):
    pass


# ---------------------------------------------------------------------------
# Data model


@dataclass
class GameId:
    region: str  # code: "US", "EU", "JP", "KR", "CN"
    serial: str  # "SLUS-20963"
    suffix: str  # rest of the folder name

    @property
    def region_name(self) -> str:
        key = f"region.{self.region}"
        return t(key) if key in MESSAGES else self.region


def parse_game_id(dirname: str) -> GameId | None:
    m = _SAVE_DIR_RE.match(dirname)
    if not m:
        return None
    region = _REGIONS.get(m.group(1), m.group(1))
    return GameId(region=region, serial=f"{m.group(2)}-{m.group(3)}", suffix=m.group(4))


@dataclass
class Entry:
    name: str
    path: str  # absolute path on the card, e.g. "/BASLUS-20963/icon.sys"
    is_dir: bool
    size: int  # files: bytes; folders: space used on the card
    created: datetime | None
    modified: datetime | None
    mode: int
    title: str = ""  # game title (icon.sys), folders only
    file_count: int = 0
    children: list["Entry"] = field(default_factory=list)

    @property
    def protected(self) -> bool:
        return bool(self.mode & DF_PROTECTED)

    @property
    def hidden(self) -> bool:
        return bool(self.mode & DF_HIDDEN)

    @property
    def is_ps1_save(self) -> bool:
        return bool(self.mode & DF_PSX)

    @property
    def is_pocketstation(self) -> bool:
        return bool(self.mode & DF_POCKETSTN)

    @property
    def game_id(self) -> GameId | None:
        return parse_game_id(self.name) if self.is_dir else None

    @property
    def parent_path(self) -> str:
        return parent_of(self.path)

    def attributes(self) -> str:
        flags = []
        if self.protected:
            flags.append(t("attr.protected"))
        if self.hidden:
            flags.append(t("attr.hidden"))
        if self.is_ps1_save:
            flags.append(t("attr.ps1"))
        if self.is_pocketstation:
            flags.append(t("attr.pocketstation"))
        return ", ".join(flags)


@dataclass
class CardInfo:
    path: Path
    format: CardFormat
    total_bytes: int  # allocatable space
    free_bytes: int

    @property
    def used_bytes(self) -> int:
        return self.total_bytes - self.free_bytes


# ---------------------------------------------------------------------------
# Path helpers


def norm_path(path: str) -> str:
    """Normalizes to "/a/b" (root = "/")."""
    parts = [p for p in path.replace("\\", "/").split("/") if p not in ("", ".")]
    return "/" + "/".join(parts)


def join_path(parent: str, name: str) -> str:
    parent = norm_path(parent)
    return (parent.rstrip("/") + "/" + name) if parent != "/" else "/" + name


def parent_of(path: str) -> str:
    path = norm_path(path)
    if path == "/":
        return "/"
    return norm_path(path.rsplit("/", 1)[0])


def validate_name(name: str) -> str:
    """Validates a file/folder name for the card. Returns the name."""
    if not name or name in (".", ".."):
        raise CardError("name.empty")
    try:
        raw = name.encode("ascii")
    except UnicodeEncodeError:
        raise CardError("name.ascii", name=name) from None
    if len(raw) > MAX_NAME_LEN:
        raise CardError("name.too_long", name=name, max=MAX_NAME_LEN)
    if any(c in _BAD_NAME_CHARS or ord(c) < 32 for c in name):
        raise CardError("name.bad_chars", name=name)
    return name


def safe_local_name(name: str) -> str:
    """Name that is safe to write to the PC disk (Windows is the strictest)."""
    clean = _WIN_BAD_CHARS.sub("_", name).rstrip(" .") or "_"
    if clean.split(".")[0].upper() in _WIN_RESERVED:
        clean = "_" + clean
    return clean


def _to_datetime(tod) -> datetime | None:
    try:
        ts = tod_to_time(tod)
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    except (ValueError, OverflowError, OSError):
        return None


def _decode_name(raw: bytes) -> str:
    return raw.decode("ascii", "replace")


def _clean_title(text: str) -> str:
    # Titles use Shift-JIS "full-width" characters (ＡＢＣ, ideographic space)
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_TITLE_FIXES)
    return " ".join(text.split())


_TITLE_FIXES = str.maketrans({"−": "-", "‐": "-", "〜": "~", "�": ""})


# ---------------------------------------------------------------------------
# mymc++ wrapper with the layout (ECC / no ECC) forced by our detection


_ALLOCATED = _ps2mc.PS2MC_FAT_ALLOCATED_BIT
# top byte of a little-endian FAT entry -> 1 if the "allocated" bit is set
_HIGH_BIT_TO_ONE = bytes(1 if b & 0x80 else 0 for b in range(256))


class _PS2MC(_ps2mc.ps2mc):
    _check_table = None  # full FAT while check() runs (read-only)

    def __init__(self, f, layout: Layout, ignore_ecc: bool = False):
        self._psmm_layout = layout
        # On images without ECC, ignore_ecc=True makes mymc++ never read the
        # "spare" bytes (which would actually be the start of the next page).
        super().__init__(f, ignore_ecc=True if layout is Layout.RAW else ignore_ecc)

    def _calculate_derived(self):
        super()._calculate_derived()
        if getattr(self, "_psmm_layout", None) is Layout.RAW:
            self.spare_size = 0
            self.raw_page_size = self.page_size

    # -- fast FAT scans ----------------------------------------------------
    # mymc++ looks FAT entries up one at a time through a 12-cluster LRU
    # cache. Counting free space or checking a 64 MB card that way costs
    # ~200k lookups (over a second in the browser). These versions read the
    # FAT one cluster at a time (through the same cache, so pending changes
    # are seen) and give the same results.

    def _fat_snapshot(self) -> array.array:
        epc = self.entries_per_cluster
        end = self.allocatable_cluster_end
        table = array.array("I")
        for i in range(-(-end // epc)):
            fat, _ = self.read_fat_cluster(i)
            table.extend(fat)
        del table[end:]
        return table

    @staticmethod
    def _allocated_flags(table: array.array) -> bytes:
        """One byte per FAT entry: 1 if the cluster is allocated, else 0."""
        if table.itemsize == 4 and sys.byteorder == "little":
            return table.tobytes()[3::4].translate(_HIGH_BIT_TO_ONE)
        return bytes(1 if v & _ALLOCATED else 0 for v in table)

    def get_free_space(self):
        return self._allocated_flags(self._fat_snapshot()).count(0) * self.cluster_size

    def lookup_fat(self, n):
        table = self._check_table
        if table is not None:
            return table[n]
        return super().lookup_fat(n)

    def check(self):
        """Same checks and messages as mymc++'s check(), with one FAT read."""
        fat_len = self.allocatable_cluster_end
        table = self._fat_snapshot()
        marks = array.array("B", [0]) * fat_len
        self._check_table = table
        try:
            cluster = self.read_allocatable_cluster(0)
            ent = unpack_dirent(cluster[:PS2MC_DIRENT_LENGTH])
            ret = self._check_dir(marks, (0, 0), "/", ent)
        finally:
            self._check_table = None
        allocated = self._allocated_flags(table)
        # allocated but not reached from any file/directory = lost
        if int.from_bytes(allocated, "little") & ~int.from_bytes(marks.tobytes(), "little"):
            lost = [i for i in range(fat_len) if allocated[i] and not marks[i]]
            print(" ".join(map(str, lost)) + " ")  # mymc++ prints "n " per cluster
            print("found", len(lost), "lost clusters")
            ret = False
        return ret

    def read_page(self, n):
        if self._psmm_layout is not Layout.RAW:
            return super().read_page(n)
        # no ECC: plain page (mymc++ would try to check ECC on page 0)
        f = self.f
        f.seek(self.page_size * n)
        page = f.read(self.page_size)
        if len(page) != self.page_size:
            raise _ps2mc.corrupt("attempted to read past EOF (page %05X)" % n, f)
        return page


@contextlib.contextmanager
def _captured_stdout() -> Iterator[io.StringIO]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def _wrap_errors(e: Exception) -> CardError:
    if isinstance(e, CardError):
        return e
    if isinstance(e, _ps2mc.path_not_found):
        return CardError("err.path_not_found", path=getattr(e, "filename", ""))
    if isinstance(e, _ps2mc.file_not_found):
        return CardError("err.file_not_found", path=getattr(e, "filename", ""))
    if isinstance(e, _ps2mc.dir_not_found):
        return CardError("err.dir_not_found", path=getattr(e, "filename", ""))
    if isinstance(e, _ps2mc.corrupt):
        return CardError("err.corrupt", error=e)
    if isinstance(e, _ps2mc.error):
        return CardError("{error}", error=e)
    if isinstance(e, OSError):
        return CardError("err.io", error=e)
    return CardError("{kind}: {error}", kind=type(e).__name__, error=e)


# ---------------------------------------------------------------------------
# Read operations (shared by the normal and the editing session)


class _Reader:
    _mc: _PS2MC

    # -- listing -----------------------------------------------------------

    def _raw_entries(self, path: str):
        path = norm_path(path)
        try:
            d = self._mc.dir_open(path)
        except Exception as e:
            raise _wrap_errors(e) from e
        try:
            ents = [list(ent) for ent in d]
        finally:
            d.close()
        for ent in ents:
            if not (ent[0] & DF_EXISTS):
                continue
            name = _decode_name(ent[8])
            if name in (".", ".."):
                continue
            yield name, ent

    def _make_entry(self, parent: str, name: str, ent, recursive: bool) -> Entry:
        path = join_path(parent, name)
        is_dir = bool(ent[0] & DF_DIR)
        e = Entry(
            name=name,
            path=path,
            is_dir=is_dir,
            size=ent[2],
            created=_to_datetime(ent[3]),
            modified=_to_datetime(ent[6]),
            mode=ent[0],
        )
        if is_dir:
            children = [
                self._make_entry(path, n, c, recursive) for n, c in self._raw_entries(path)
            ]
            e.file_count = sum(1 for c in children if not c.is_dir)
            e.size = self._dir_size(children)
            e.title = self.title(path)
            if recursive:
                e.children = children
        return e

    def _dir_size(self, children: list[Entry]) -> int:
        cs = self._mc.cluster_size
        # directory entries: 512 bytes each, including "." and ".."
        total = math.ceil((len(children) + 2) * 512 / cs) * cs
        for c in children:
            total += c.size if c.is_dir else math.ceil(c.size / cs) * cs
        return total

    def list_dir(self, path: str = "/") -> list[Entry]:
        path = norm_path(path)
        return [self._make_entry(path, n, ent, False) for n, ent in self._raw_entries(path)]

    def tree(self) -> list[Entry]:
        """The whole card tree, starting at the root."""
        return [self._make_entry("/", n, ent, True) for n, ent in self._raw_entries("/")]

    def stat(self, path: str) -> Entry:
        path = norm_path(path)
        if path == "/":
            raise CardError("err.root_entry")
        parent, name = parent_of(path), path.rsplit("/", 1)[1]
        for n, ent in self._raw_entries(parent):
            if n == name:
                return self._make_entry(parent, n, ent, True)
        raise CardError("err.not_found", path=path)

    def exists(self, path: str) -> bool:
        try:
            return self._mc.get_mode(norm_path(path)) is not None
        except Exception:
            return False

    def is_dir(self, path: str) -> bool:
        path = norm_path(path)
        if path == "/":
            return True
        mode = self._mc.get_mode(path)
        return bool(mode is not None and mode & DF_DIR)

    def title(self, dirpath: str) -> str:
        try:
            data = self._mc.get_icon_sys(norm_path(dirpath))
            if not data:
                return ""
            t1, t2 = _iconsys.IconSys(data).get_title("unicode")
            return _clean_title(f"{t1} {t2}")
        except Exception:
            return ""

    # -- space --------------------------------------------------------------

    @property
    def cluster_size(self) -> int:
        return self._mc.cluster_size

    def free_bytes(self) -> int:
        return self._mc.get_free_space()

    def total_bytes(self) -> int:
        return self._mc.get_allocatable_space()

    # -- reading files ---------------------------------------------------

    def read_file(self, path: str) -> bytes:
        try:
            with contextlib.closing(self._mc.open(norm_path(path), "rb")) as f:
                return f.read()
        except Exception as e:
            raise _wrap_errors(e) from e

    def extract(self, path: str, dest_dir: str | os.PathLike, overwrite: bool = False) -> list[Path]:
        """Extracts a file or folder (recursively) to ``dest_dir``.

        If ``overwrite`` is false and something already exists at the
        destination, raises :class:`ExistsError` before writing anything.
        """
        return self.extract_many([path], dest_dir, overwrite)

    def extract_many(
        self, paths: list[str], dest_dir: str | os.PathLike, overwrite: bool = False
    ) -> list[Path]:
        dest_dir = Path(dest_dir)
        plan = self._plan_many(paths, dest_dir)
        if not overwrite:
            clash = [str(p) for p, src in plan if src is not None and p.exists()]
            if clash:
                raise ExistsError(
                    "err.exists_dest",
                    items="\n".join(clash[:10]) + ("\n…" if len(clash) > 10 else ""),
                )
        written = []
        for local, src in plan:
            if src is None:
                local.mkdir(parents=True, exist_ok=True)
            else:
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_bytes(self.read_file(src))
                written.append(local)
        return written

    def export_zip(self, paths: list[str]) -> bytes:
        """Packs card files/folders into a .zip (in memory)."""
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for local, src in self._plan_many(paths, Path("")):
                arc = local.as_posix()
                if src is None:
                    z.writestr(arc.rstrip("/") + "/", b"")
                else:
                    e = self.stat(src)
                    info = zipfile.ZipInfo(arc)
                    if e.modified and e.modified.year >= 1980:
                        info.date_time = e.modified.timetuple()[:6]
                    info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, self.read_file(src))
        return buf.getvalue()

    def _plan_many(self, paths: list[str], dest: Path) -> list[tuple[Path, str | None]]:
        plan: list[tuple[Path, str | None]] = []
        for path in paths:
            path = norm_path(path)
            if path == "/":
                for n, _ in self._raw_entries("/"):
                    plan += self._plan_extract(join_path("/", n), dest)
            else:
                plan += self._plan_extract(path, dest)
        return plan

    def _plan_extract(self, path: str, dest: Path) -> list[tuple[Path, str | None]]:
        name = path.rsplit("/", 1)[1]
        local = dest / safe_local_name(name)
        if not self.is_dir(path):
            return [(local, path)]
        plan: list[tuple[Path, str | None]] = [(local, None)]
        for n, ent in self._raw_entries(path):
            plan += self._plan_extract(join_path(path, n), local)
        return plan

    # -- saves -------------------------------------------------------------

    def export_save(self, path: str) -> "_saves.SaveFile":
        """Reads a folder as a save (directory entry + files, with modes and dates)."""
        path = norm_path(path)
        if path == "/" or not self.is_dir(path):
            raise CardError("save.not_a_folder", path=path)
        if not self.is_flat_dir(path):
            raise CardError("save.has_subfolders", path=path)
        try:
            with _captured_stdout():
                return self._mc.export_save_file(path)
        except Exception as e:
            raise _wrap_errors(e) from e

    def is_flat_dir(self, path: str) -> bool:
        """True if the folder only contains files (the shape of a game save)."""
        return all(not (ent[0] & DF_DIR) for _, ent in self._raw_entries(path))

    # -- checking --------------------------------------------------------

    def check(self) -> tuple[bool, list[str]]:
        """File system check. Returns (ok, messages)."""
        with _captured_stdout() as out:
            try:
                ok = bool(self._mc.check())
            except Exception as e:  # non-ASCII names, broken chains...
                ok = False
                print(t("err.check_exception", error=e))
        msgs = [line.strip() for line in out.getvalue().splitlines() if line.strip()]
        return ok, msgs


# ---------------------------------------------------------------------------
# Editing session


class CardEditor(_Reader):
    """Changes applied to the temporary copy. Use via ``MemoryCard.edit()``."""

    def __init__(self, mc: _PS2MC):
        self._mc = mc
        self.changes: list[str] = []

    def _need_space(self, nbytes: int, extra_clusters: int = 1) -> None:
        cs = self.cluster_size
        need = math.ceil(nbytes / cs) * cs + extra_clusters * cs
        free = self.free_bytes()
        if need > free:
            raise NoSpaceError("err.no_space", need=need // 1024, free=free // 1024)

    def mkdir(self, path: str) -> None:
        path = norm_path(path)
        validate_name(path.rsplit("/", 1)[1])
        if self.exists(path):
            raise ExistsError("err.exists", path=path)
        if not self.is_dir(parent_of(path)):
            raise CardError("err.dest_missing", path=parent_of(path))
        self._need_space(0)
        try:
            self._mc.mkdir(path)
        except Exception as e:
            raise _wrap_errors(e) from e
        self.changes.append(t("change.mkdir", path=path))

    def write_file(self, path: str, data: bytes, overwrite: bool = False) -> None:
        path = norm_path(path)
        validate_name(path.rsplit("/", 1)[1])
        if not self.is_dir(parent_of(path)):
            raise CardError("err.dest_missing", path=parent_of(path))
        if self.exists(path):
            if self.is_dir(path):
                raise ExistsError("err.exists_dir", path=path)
            if not overwrite:
                raise ExistsError("err.exists", path=path)
            old = len(self.read_file(path))
            self._need_space(max(0, len(data) - old), 0)
        else:
            self._need_space(len(data))
        try:
            with contextlib.closing(self._mc.open(path, "wb")) as f:
                f.write(data)
        except Exception as e:
            raise _wrap_errors(e) from e
        self.changes.append(t("change.write", path=path))

    def add_local(self, local: str | os.PathLike, dest_dir: str = "/", overwrite: bool = False) -> None:
        """Adds a file or folder from the PC (folders are copied recursively)."""
        local = Path(local)
        target = join_path(dest_dir, local.name)
        if local.is_dir():
            if self.exists(target):
                if not self.is_dir(target):
                    raise ExistsError("err.exists_file", path=target)
                if not overwrite:
                    raise ExistsError("err.exists", path=target)
            else:
                self.mkdir(target)
            for child in sorted(local.iterdir()):
                self.add_local(child, target, overwrite)
        elif local.is_file():
            self.write_file(target, local.read_bytes(), overwrite)
        else:
            raise CardError("err.not_file_or_dir", path=local)

    def import_save(self, sf: "_saves.SaveFile", overwrite: bool = False, name: str | None = None) -> str:
        """Imports a save into the card root. Returns the folder path it got."""
        if name is not None:
            _saves.rename(sf, name)
        name = validate_name(_saves.dirname(sf))
        target = "/" + name
        freed = 0
        if self.exists(target):
            if not overwrite:
                raise ExistsError("err.exists", path=target)
            freed = self.stat(target).size if self.is_dir(target) else 0
        need = _saves.space_needed(sf, self.cluster_size)
        free = self.free_bytes() + freed
        if need > free:
            raise NoSpaceError("err.no_space", need=need // 1024, free=free // 1024)
        if self.exists(target):
            self.remove(target)
        try:
            self._mc.import_save_file(sf, False)
        except Exception as e:
            raise _wrap_errors(e) from e
        self.changes.append(t("change.import", path=target))
        return target

    def copy_from(self, src: "_Reader", paths: list[str], dest_dir: str = "/", overwrite: bool = False) -> None:
        """Copies items from another card.

        Save-shaped folders copied to the root keep their modes and dates
        (same as exporting + importing); anything else is copied file by file.
        """
        dest_dir = norm_path(dest_dir)
        if not self.is_dir(dest_dir):
            raise CardError("err.dest_missing", path=dest_dir)
        for path in paths:
            path = norm_path(path)
            if path == "/":
                for n, _ in src._raw_entries("/"):
                    self.copy_from(src, [join_path("/", n)], dest_dir, overwrite)
                continue
            if dest_dir == "/" and src.is_dir(path) and src.is_flat_dir(path):
                self.import_save(src.export_save(path), overwrite)
            else:
                self._copy_generic(src, path, dest_dir, overwrite)

    def clone_from(self, src: "_Reader") -> None:
        """Copies the whole content of ``src`` into this (empty) card.

        Every file and folder keeps its attributes and dates, at any depth.
        """
        for name, _ in src._raw_entries("/"):
            self._clone_entry(src, join_path("/", name), "/")

    def _clone_entry(self, src: "_Reader", path: str, dest_dir: str) -> None:
        target = join_path(dest_dir, path.rsplit("/", 1)[1])
        ent = src._mc.get_dirent(path)
        if ent[0] & DF_DIR:
            self.mkdir(target)
            for name, _ in src._raw_entries(path):
                self._clone_entry(src, join_path(path, name), target)
        else:
            self.write_file(target, src.read_file(path))
        # set after the children: adding entries updates a folder's dates
        # (mode/created/modified/attr; type bits and name are kept by mymc++)
        try:
            self._mc.set_dirent(target, [ent[0], ent[1], None, ent[3], None, None, ent[6], ent[7], None])
        except Exception as e:
            raise _wrap_errors(e) from e

    def _copy_generic(self, src: "_Reader", path: str, dest_dir: str, overwrite: bool) -> None:
        name = path.rsplit("/", 1)[1]
        target = join_path(dest_dir, name)
        if not src.is_dir(path):
            self.write_file(target, src.read_file(path), overwrite)
            return
        if self.exists(target):
            if not self.is_dir(target):
                raise ExistsError("err.exists_file", path=target)
            if not overwrite:
                raise ExistsError("err.exists", path=target)
        else:
            self.mkdir(target)
        for n, _ in src._raw_entries(path):
            self._copy_generic(src, join_path(path, n), target, overwrite)

    def remove(self, path: str) -> None:
        path = norm_path(path)
        if path == "/":
            raise CardError("err.delete_root")
        if not self.exists(path):
            raise CardError("err.not_found", path=path)
        try:
            if self.is_dir(path):
                self._mc.rmdir(path)
            else:
                self._mc.remove(path)
        except Exception as e:
            raise _wrap_errors(e) from e
        self.changes.append(t("change.remove", path=path))

    def rename(self, path: str, new_name: str) -> None:
        path = norm_path(path)
        validate_name(new_name)
        target = join_path(parent_of(path), new_name)
        if self.exists(target):
            raise ExistsError("err.exists", path=target)
        mc = self._mc
        try:
            # mymc++'s set_dirent() does not change the name; write the entry directly
            dirloc, ent, _ = mc.path_search(path)
            if ent is None:
                raise CardError("err.not_found", path=path)
            d = mc._opendir_parent_dirloc(dirloc, "r+b")
            try:
                raw = list(d[dirloc[1]])
                raw[8] = new_name.encode("ascii")
                d.write_raw_ent(dirloc[1], raw, True)
            finally:
                d.close()
            mc.flush()
        except CardError:
            raise
        except Exception as e:
            raise _wrap_errors(e) from e
        self.changes.append(t("change.rename", path=path, name=new_name))


# ---------------------------------------------------------------------------
# Card


class MemoryCard(_Reader):
    """A PS2 memory card open for reading; changes go through :meth:`edit`."""

    def __init__(self, path: str | os.PathLike, make_backups: bool = True):
        self.path = Path(path).resolve()
        self.make_backups = make_backups
        self.format: CardFormat = detect(self.path)
        if self.format.platform is not Platform.PS2:
            raise FormatError("fmt.ps1_unsupported")
        self._f = None
        self._mc = None
        self._initial_check: bool | None = None
        self.last_backup: Path | None = None
        self._open()

    # -- lifecycle -------------------------------------------------------

    def _open(self) -> None:
        self._f = open(self.path, "rb")
        try:
            self._mc = _PS2MC(self._f, self.format.layout)
        except Exception as e:
            self._f.close()
            self._f = None
            raise _wrap_errors(e) from e

    def close(self) -> None:
        if self._mc is not None:
            try:
                self._mc.close()
            except Exception:
                pass
            self._mc = None
        if self._f is not None:
            self._f.close()
            self._f = None

    def reload(self) -> None:
        self.close()
        self.format = detect(self.path)
        self._open()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def info(self) -> CardInfo:
        return CardInfo(
            path=self.path,
            format=self.format,
            total_bytes=self.total_bytes(),
            free_bytes=self.free_bytes(),
        )

    # -- safe editing -----------------------------------------------------

    @contextlib.contextmanager
    def edit(self) -> Iterator[CardEditor]:
        """Opens a transactional editing session (see the module docstring)."""
        if self._initial_check is None:
            self._initial_check, _ = self.check()

        tmp = self.path.with_name(f".{self.path.name}.psmm-tmp")
        try:
            shutil.copyfile(self.path, tmp)
        except OSError as e:
            raise CardError("err.workcopy", error=e) from e

        tf = None
        committed = False
        try:
            tf = open(tmp, "r+b")
            try:
                mc = _PS2MC(tf, self.format.layout)
            except Exception as e:
                raise _wrap_errors(e) from e
            editor = CardEditor(mc)
            try:
                yield editor
            finally:
                # always close to flush caches; on error the copy is
                # discarded below
                try:
                    mc.close()
                except Exception:
                    pass
            tf.flush()
            try:
                os.fsync(tf.fileno())
            except (OSError, AttributeError):  # e.g. the browser in-memory FS
                pass
            tf.close()
            tf = None

            if not editor.changes:
                return

            # verify the copy before replacing the original
            with open(tmp, "rb") as vf:
                vmc = _PS2MC(vf, self.format.layout)
                try:
                    ok, msgs = _Reader.check(_as_reader(vmc))
                finally:
                    vmc.close()
            if self._initial_check and not ok:
                raise CardError("err.verify_failed", details="\n".join(msgs[:10]))
            if os.path.getsize(tmp) != os.path.getsize(self.path):
                raise CardError("err.size_changed")

            if self.make_backups:
                self.last_backup = _backup.make_backup(self.path)

            # Windows cannot replace a file that is still open
            self.close()
            try:
                os.replace(tmp, self.path)
                _fsync_dir(self.path.parent)
            finally:
                self._open()
            committed = True
        finally:
            if tf is not None:
                tf.close()
            if not committed and tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    # -- creation -----------------------------------------------------------

    @staticmethod
    def create(
        path: str | os.PathLike,
        size_mb: int = 8,
        ecc: bool = False,
        overwrite: bool = False,
    ) -> "MemoryCard":
        """Creates a new, formatted PS2 card."""
        if size_mb not in (1, 2, 4, 8, 16, 32, 64, 128):
            raise CardError("err.bad_size")
        path = Path(path)
        if path.exists() and not overwrite:
            raise ExistsError("err.exists", path=path)
        pages = size_mb * 1024 * 1024 // _ps2mc.PS2MC_STANDARD_PAGE_SIZE
        params = (
            ecc,
            _ps2mc.PS2MC_STANDARD_PAGE_SIZE,
            _ps2mc.PS2MC_STANDARD_PAGES_PER_ERASE_BLOCK,
            pages,
        )
        tmp = path.with_name(f".{path.name}.psmm-tmp")
        try:
            with open(tmp, "w+b") as f:
                mc = _ps2mc.ps2mc(f, params=params)
                mc.close()
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()
        return MemoryCard(path)


def _as_reader(mc: _PS2MC) -> _Reader:
    r = _Reader.__new__(_Reader)
    r._mc = mc
    return r


def _fsync_dir(folder: Path) -> None:
    if os.name != "posix":
        return
    try:
        fd = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)
