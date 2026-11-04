# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""PS2 save files: import (.psu, .max, .cbs, .sps, .xps, .psv) and export (.psu, .max).

Parsing and writing is done by mymc++. A loaded save is a ``PS2SaveFile``:
one directory entry plus its files (with their original modes and dates).
"""

from __future__ import annotations

import contextlib
import io
import math
from dataclasses import dataclass
from pathlib import PurePath

from mymcplusplus.save import format_ems, format_max_drive, ps2save

from .i18n import t

#: extensions accepted when importing
IMPORT_EXTENSIONS = (".psu", ".max", ".cbs", ".sps", ".xps", ".psv")
#: export formats: id -> (extension, mymc++ module)
EXPORT_FORMATS = {"psu": (".psu", format_ems), "max": (".max", format_max_drive)}

_FORMAT_NAMES = {
    "psu": "EMS / uLaunchELF (.psu)",
    "max": "Action Replay MAX (.max)",
    "cbs": "CodeBreaker (.cbs)",
    "sps": "SharkPort / X-Port (.sps/.xps)",
    "psv": "PS3 (.psv)",
}

SaveFile = ps2save.PS2SaveFile


@dataclass
class SaveInfo:
    name: str  # directory name it will get on the card
    title: str
    files: int
    size: int  # payload bytes
    format: str  # "psu", "max", ...

    @property
    def format_name(self) -> str:
        return _FORMAT_NAMES.get(self.format, self.format)


def is_save_filename(name: str) -> bool:
    return PurePath(name).suffix.lower() in IMPORT_EXTENSIONS


def load(data: bytes, filename: str = "") -> tuple[SaveFile, str]:
    """Parses a save file. Returns (save, format id)."""
    from .card import CardError  # local import: card imports this module

    f = io.BytesIO(data)
    fmt = ps2save.poll_format(f)
    if fmt is None:
        raise CardError("save.unknown", name=filename or "?")
    f.seek(0)
    sf = ps2save.PS2SaveFile()
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            fmt.load(sf, f)
            # .max saves are decompressed lazily; force it now so errors show up here
            for i in range(len(sf)):
                sf.get_file(i)
    except Exception as e:
        raise CardError("save.corrupt", name=filename or "?", error=e) from e
    return sf, fmt.FORMAT_ID


def dirname(sf: SaveFile) -> str:
    return sf.get_directory()[8].decode("ascii", "replace")


def rename(sf: SaveFile, new_name: str) -> None:
    ent = list(sf.get_directory())
    ent[8] = new_name.encode("ascii")
    sf.dirent = ent


def title(sf: SaveFile) -> str:
    from .card import _clean_title

    try:
        icon = sf.get_icon_sys()
        if icon is None:
            return ""
        t1, t2 = icon.get_title("unicode")
        return _clean_title(f"{t1} {t2}")
    except Exception:
        return ""


def payload_size(sf: SaveFile) -> int:
    return sum(len(sf.get_file(i)[1]) for i in range(len(sf)))


def info(sf: SaveFile, fmt: str) -> SaveInfo:
    return SaveInfo(name=dirname(sf), title=title(sf), files=len(sf), size=payload_size(sf), format=fmt)


def space_needed(sf: SaveFile, cluster_size: int) -> int:
    """Bytes the save takes on a card: file clusters + directory entries."""
    files = sum(math.ceil(len(sf.get_file(i)[1]) / cluster_size) for i in range(len(sf)))
    dir_clusters = math.ceil((len(sf) + 2) * 512 / cluster_size)
    return (files + dir_clusters) * cluster_size


def dump(sf: SaveFile, fmt: str) -> bytes:
    """Serializes ``sf`` in an export format ("psu" or "max")."""
    from .card import CardError

    if fmt not in EXPORT_FORMATS:
        raise CardError("save.bad_format", format=fmt)
    module = EXPORT_FORMATS[fmt][1]
    out = io.BytesIO()
    target = _AsciiTitleSave(sf) if fmt == "max" else sf
    try:
        # lzari (used by .max) prints progress to stdout/stderr
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            module.save(target, out)
    except Exception as e:
        raise CardError("save.export_failed", name=dirname(sf), format=fmt, error=e) from e
    return out.getvalue()


class _AsciiTitleSave:
    """Wraps a save so its icon.sys title is pure ASCII.

    mymc++ writes the title into the .max header with ``.encode("ascii")`` and
    crashes on titles with characters outside ASCII.
    """

    def __init__(self, sf: SaveFile):
        self._sf = sf
        self.dirent = sf.dirent

    def __getattr__(self, name):
        return getattr(self._sf, name)

    def get_icon_sys(self):
        icon = self._sf.get_icon_sys()
        if icon is None:
            return None

        class _Icon:
            def get_title(self, encoding):
                return tuple(
                    part.encode("ascii", "replace").decode("ascii") for part in icon.get_title(encoding)
                )

        return _Icon()


def export_filename(sf: SaveFile, fmt: str) -> str:
    from .card import safe_local_name

    return safe_local_name(dirname(sf)) + EXPORT_FORMATS[fmt][0]
