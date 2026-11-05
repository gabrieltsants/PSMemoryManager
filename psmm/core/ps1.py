# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""PS1 memory cards: images, saves, icons, editing and checking.

A PS1 card has 128 KB: 16 blocks of 8 KB, each block 64 frames of 128 bytes.

* Block 0 is the directory. Frame 0 holds "MC" and frames 1-15 describe
  blocks 1-15 (state, size, next block of the save, file name), each frame
  with an XOR checksum in its last byte.
* A save takes one or more blocks, chained through the directory. Its first
  block starts with the title frame ("SC", icon flags, Shift-JIS title,
  16-colour palette) followed by 1-3 icon frames (16x16, 4 bits per pixel).
* Deleting a save (as the console does) only flips the state of its blocks
  to "deleted": the data stays there until those blocks are reused, so it
  can be restored.

Card images wrap the 128 KB in different containers: raw (.mcd Gen2/SD2PSX,
.mcr ePSXe/DuckStation, .srm RetroArch...), DexDrive (.gme, 3904-byte
header with per-block comments), Connectix VGS (.vgs/.mem, 64-byte header)
and PSP/PS Vita (.vmp, 128-byte signed header). Single saves come as .mcs
(directory frame + blocks), Action Replay/GameShark/Xploder (.psx/.mcb/.mcx/
.pda, 54-byte header), PS3 .psv (signed) or raw blocks.

The layout details follow nocash's PSX specifications and MemcardRex (GPLv3).
Cards with a non-standard directory (FreePSXBoot exploit cards, damaged
directories) open read-only: rewriting them would break them.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import struct
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Iterator

from . import backup as _backup
from . import signing
from .i18n import LocalizedError, t
from .formats import CardFormat, FormatError, Layout, Origin, Platform

FRAME = 128
BLOCK = 8192
BLOCKS = 15  # save blocks, numbered 1..15
CARD_SIZE = 16 * BLOCK  # 131072

GME_HEADER = 3904
VGS_HEADER = 64
VMP_HEADER = 0x80
PSV_HEADER = 0x84
AR_HEADER = 54

GME_MAGIC = b"123-456-STD"
CONTAINER_SIZES = {"raw": 16 * 8192, "gme": 3904 + 16 * 8192, "vgs": 64 + 16 * 8192, "vmp": 0x80 + 16 * 8192}
VGS_MAGIC = b"VgsM"
VMP_MAGIC = b"\x00PMV"
PSV_MAGIC = b"\x00VSP"

ST_FREE = 0xA0
ST_FIRST, ST_MIDDLE, ST_LAST = 0x51, 0x52, 0x53
ST_DEL_FIRST, ST_DEL_MIDDLE, ST_DEL_LAST = 0xA1, 0xA2, 0xA3
_KNOWN_STATES = {ST_FREE, ST_FIRST, ST_MIDDLE, ST_LAST, ST_DEL_FIRST, ST_DEL_MIDDLE, ST_DEL_LAST}
NO_NEXT = 0xFFFF
NAME_LEN = 20

#: card image extensions (detection is by content; these only feed file pickers)
CARD_EXTENSIONS = (".mcd", ".mcr", ".gme", ".vmp", ".vgs", ".mem", ".srm", ".mc", ".ps", ".psm", ".ddf", ".mci", ".vm1", ".bin")
#: single save extensions
SAVE_EXTENSIONS = (".mcs", ".ps1", ".psx", ".mcb", ".mcx", ".pda", ".psv")
#: export formats: id -> extension
EXPORT_FORMATS = {"mcs": ".mcs", "psv": ".psv"}

_REGIONS = {"BA": "US", "BE": "EU", "BI": "JP"}
_SAVE_NAME_IN_TEXT = re.compile(r"(B[AEI])([A-Z]{4})[-_ ]?(\d{5})([^.\s/\\]*)", re.IGNORECASE)


class Ps1Error(LocalizedError):
    pass


def _card_errors():
    from .card import CardError, ExistsError, NoSpaceError  # card imports formats; keep it lazy

    return CardError, ExistsError, NoSpaceError


def _xor(frame: bytes | bytearray) -> int:
    x = 0
    for b in frame[:127]:
        x ^= b
    return x


# ---------------------------------------------------------------------------
# Containers


@dataclass
class Unwrapped:
    container: str  # "raw" | "gme" | "vgs" | "vmp"
    raw: bytes  # the 128 KB card
    header: bytes = b""  # container header (DexDrive comments, VMP seed...)
    size_mismatch: bool = False  # file shorter/longer than the container expects
    signed: bool | None = None  # .vmp: does the signature match?


def sniff(head: bytes, size: int) -> str | None:
    """Container of a PS1 card image from its first bytes and size, or None."""
    if head.startswith(GME_MAGIC):
        return "gme"
    if head.startswith(VGS_MAGIC):
        return "vgs"
    if head.startswith(VMP_MAGIC) and len(head) > 4 and head[4] == VMP_HEADER:
        return "vmp"
    if head.startswith(b"MC") and BLOCK <= size <= 2 * CARD_SIZE:
        return "raw"
    # DexDrive file with a damaged header (seen on the Internet)
    if size == GME_HEADER + CARD_SIZE and head[GME_HEADER:GME_HEADER + 2] == b"MC":
        return "gme"
    return None


def unwrap(data: bytes) -> Unwrapped:
    """The 128 KB card inside a card image. Raises :class:`FormatError`."""
    kind = sniff(data[:GME_HEADER + 2], len(data))
    if kind is None:
        raise FormatError("fmt.unknown")
    offset = {"raw": 0, "gme": GME_HEADER, "vgs": VGS_HEADER, "vmp": VMP_HEADER}[kind]
    body = data[offset:offset + CARD_SIZE]
    if len(body) < BLOCK or body[:2] != b"MC":
        raise FormatError("ps1.truncated", size=len(data))
    mismatch = len(data) != offset + CARD_SIZE
    if len(body) < CARD_SIZE:
        # DexDrive files are often cut after the last used block
        body = body + b"\xff" * (CARD_SIZE - len(body))
    signed = signing.is_signed(data[:VMP_HEADER + CARD_SIZE], 0x0C, 0x20) if kind == "vmp" and not mismatch else None
    return Unwrapped(container=kind, raw=bytes(body), header=bytes(data[:offset]), size_mismatch=mismatch, signed=signed)


def gme_comments(header: bytes) -> list[str]:
    out = []
    for i in range(BLOCKS):
        raw = header[64 + 256 * i:64 + 256 * (i + 1)]
        out.append(raw.split(b"\0", 1)[0].decode("latin-1").strip() if raw else "")
    return out


def wrap(raw: bytes, container: str, header: bytes = b"", comments: list[str] | None = None) -> bytes:
    """A 128 KB card in a container. ``header`` is the original one (kept where it makes sense)."""
    if len(raw) != CARD_SIZE:
        raise ValueError("a PS1 card has 128 KB")
    if container == "raw":
        return bytes(raw)
    if container == "vgs":
        h = bytearray(VGS_HEADER)
        h[0:4] = VGS_MAGIC
        h[4] = h[8] = h[12] = 1
        h[17] = 2
        return bytes(h) + raw
    if container == "gme":
        h = bytearray(GME_HEADER)
        h[0:11] = GME_MAGIC
        h[18] = 1
        h[20] = 1
        h[21] = 0x4D  # "M"
        for i in range(BLOCKS):
            frame = raw[FRAME * (i + 1):FRAME * (i + 2)]
            h[22 + i] = frame[0]
            h[38 + i] = frame[8]
            text = ((comments or [""] * BLOCKS)[i] or "").encode("latin-1", "replace")[:255]
            h[64 + 256 * i:64 + 256 * i + len(text)] = text
        return bytes(h) + raw
    if container == "vmp":
        h = bytearray(VMP_HEADER)
        h[0:4] = VMP_MAGIC
        h[4] = VMP_HEADER
        seed = header[0x0C:0x20] if header.startswith(VMP_MAGIC) and len(header) >= 0x20 else b""
        if len(seed) != 20 or not any(seed):
            seed = hashlib.sha1(raw).digest()  # any value works; this one is reproducible
        h[0x0C:0x20] = seed
        return signing.sign(bytes(h) + raw, 0x0C, 0x20)
    raise ValueError(f"unknown container {container!r}")


#: conversion targets: id -> (container, extension)
TARGETS = {
    "gen2": ("raw", ".mcd"),
    "mcr": ("raw", ".mcr"),
    "srm": ("raw", ".srm"),
    "gme": ("gme", ".gme"),
    "vmp": ("vmp", ".vmp"),
    "vgs": ("vgs", ".vgs"),
}

_ORIGIN_BY_CONTAINER = {"gme": Origin.DEXDRIVE, "vgs": Origin.VGS, "vmp": Origin.PSP}
_ORIGIN_BY_EXT = {".mcd": Origin.GEN2, ".mcr": Origin.EPSXE, ".srm": Origin.RETROARCH}


def origin_of(container: str, filename: str) -> Origin:
    if container in _ORIGIN_BY_CONTAINER:
        return _ORIGIN_BY_CONTAINER[container]
    return _ORIGIN_BY_EXT.get(PurePath(filename).suffix.lower(), Origin.RAW)


def target_for_extension(name: str) -> str:
    ext = PurePath(name).suffix.lower()
    for tid, (_, e) in TARGETS.items():
        if e == ext:
            return tid
    return "gen2"


def blank_card() -> bytes:
    """A formatted, empty card, byte for byte as the PSxMemCard Gen2 creates it."""
    raw = bytearray(b"\xff" * CARD_SIZE)
    raw[0:BLOCK] = bytes(BLOCK)
    raw[0:2] = b"MC"
    raw[127] = 0x0E
    for i in range(1, 16):
        f = bytearray(FRAME)
        f[0] = ST_FREE
        f[8:10] = b"\xff\xff"
        f[127] = _xor(f)
        raw[FRAME * i:FRAME * (i + 1)] = f
    for i in range(16, 36):  # broken sector list: none
        raw[FRAME * i:FRAME * i + 4] = b"\xff\xff\xff\xff"
    raw[FRAME * 56:FRAME * 63] = b"\xff" * (FRAME * 7)
    return bytes(raw)


# ---------------------------------------------------------------------------
# Names, titles and icons


def decode_title(raw: bytes) -> str:
    """Shift-JIS title of a save (64 bytes), normalized to plain text."""
    from .card import _clean_title

    # ends at the first NUL that is a character of its own (not the 2nd byte of a Shift-JIS pair)
    i = 0
    while i < len(raw) and raw[i] != 0:
        i += 2 if (0x81 <= raw[i] <= 0x9F or 0xE0 <= raw[i] <= 0xFC) else 1
    raw = raw[:min(i, len(raw))]
    try:
        text = raw.decode("shift_jis")
    except (UnicodeDecodeError, LookupError):
        try:
            text = raw.decode("cp932", "replace")
        except LookupError:
            text = raw.decode("ascii", "replace")
    return _clean_title(unicodedata.normalize("NFKC", text))


def split_name(name: str) -> tuple[str | None, str | None, str]:
    """'BASLUS-00067DRAX00' -> ('US', 'SLUS-00067', 'DRAX00')."""
    from .sdcard import normalize_game_id

    region = _REGIONS.get(name[:2].upper())
    serial = normalize_game_id(name[2:12]) if len(name) >= 12 else None
    return region, serial, name[12:] if serial else name[2:]


def _palette(title_frame: bytes) -> list[int | None]:
    """16 colours as 0xRRGGBB (None = transparent)."""
    out: list[int | None] = []
    for i in range(16):
        v = title_frame[0x60 + 2 * i] | (title_frame[0x61 + 2 * i] << 8)
        r, g, b = (v & 0x1F) << 3, ((v >> 5) & 0x1F) << 3, ((v >> 10) & 0x1F) << 3
        out.append(None if v == 0 else (r << 16) | (g << 8) | b)
    return out


@dataclass
class Icon:
    frames: int  # 1-3 (0: no icon)
    palette: list[int | None]
    pixels: bytes  # frames * 128 bytes, 4 bits per pixel, low nibble first

    def to_dict(self) -> dict:
        return {
            "n": self.frames,
            "pal": [None if c is None else f"#{c:06x}" for c in self.palette],
            "px": self.pixels.hex(),
        }


def read_icon(first_block: bytes) -> Icon | None:
    if first_block[:2].upper() != b"SC":
        return None
    frames = {0x11: 1, 0x12: 2, 0x13: 3}.get(first_block[2], 1)
    return Icon(frames=frames, palette=_palette(first_block[:FRAME]), pixels=bytes(first_block[FRAME:FRAME * (1 + frames)]))


def _is_pocketstation(name: bytes, first_block: bytes) -> bool:
    return len(name) > 6 and name[6:7] == b"P" and first_block[0x52:0x55] == b"MCX" and first_block[0x55:0x56] in (b"0", b"1")


# ---------------------------------------------------------------------------
# Directory


@dataclass
class Ps1Entry:
    """A save on the card (live or deleted)."""

    block: int  # first block, 1..15
    blocks: list[int]
    name: str
    title: str
    declared_size: int
    deleted: bool
    icon: Icon | None
    pocketstation: bool = False
    problems: list[str] = field(default_factory=list)  # message keys
    restorable: bool = False
    comment: str = ""

    @property
    def path(self) -> str:
        return f"/{self.block}"

    @property
    def size(self) -> int:
        return len(self.blocks) * BLOCK

    @property
    def region(self) -> str | None:
        return split_name(self.name)[0]

    @property
    def serial(self) -> str | None:
        return split_name(self.name)[1]

    def region_name(self) -> str | None:
        from .i18n import MESSAGES

        r = self.region
        return t(f"region.{r}") if r and f"region.{r}" in MESSAGES else r


@dataclass
class Directory:
    saves: list[Ps1Entry]
    states: list[int]  # state byte of blocks 1..15 (index 0 = block 1)
    errors: list[str] = field(default_factory=list)  # localized messages
    warnings: list[str] = field(default_factory=list)
    nonstandard: bool = False  # unknown states or cross-linked saves: read-only
    freepsxboot: bool = False
    lost: list[int] = field(default_factory=list)  # in-use blocks no save reaches

    def free_blocks(self) -> list[int]:
        """Blocks a new save can use: free first, then deleted and lost ones (lowest number first)."""
        free = [b for b in range(1, 16) if self.states[b - 1] == ST_FREE]
        reusable = [b for b in range(1, 16) if self.states[b - 1] in (ST_DEL_FIRST, ST_DEL_MIDDLE, ST_DEL_LAST) or b in self.lost]
        return free + [b for b in reusable if b not in free]

    def live(self) -> list[Ps1Entry]:
        return [s for s in self.saves if not s.deleted]


def _frame(raw: bytes, block: int) -> bytes:
    return raw[FRAME * block:FRAME * (block + 1)]


def _block(raw: bytes, block: int) -> bytes:
    return raw[BLOCK * block:BLOCK * (block + 1)]


def parse_directory(raw: bytes, comments: list[str] | None = None) -> Directory:
    states = [_frame(raw, b)[0] for b in range(1, 16)]
    d = Directory(saves=[], states=states)
    head = _frame(raw, 0)
    if head[:2] != b"MC":
        d.errors.append(t("ps1.chk.magic"))
        d.nonstandard = True
    elif head[127] != _xor(head):
        d.warnings.append(t("ps1.chk.header_checksum"))

    unknown = [b for b in range(1, 16) if states[b - 1] not in _KNOWN_STATES]
    for b in range(1, 16):
        f = _frame(raw, b)
        if f[127] != _xor(f) and states[b - 1] in _KNOWN_STATES:
            d.errors.append(t("ps1.chk.checksum", block=b))
    if unknown:
        d.nonstandard = True
        d.errors.append(t("ps1.chk.unknown_state", blocks=", ".join(map(str, unknown))))

    owner: dict[int, int] = {}
    for b in range(1, 16):
        st = states[b - 1]
        if st not in (ST_FIRST, ST_DEL_FIRST):
            continue
        deleted = st == ST_DEL_FIRST
        mid, last = (ST_DEL_MIDDLE, ST_DEL_LAST) if deleted else (ST_MIDDLE, ST_LAST)
        f = _frame(raw, b)
        size, nxt = struct.unpack_from("<IH", f, 4)
        name_raw = f[10:10 + NAME_LEN + 1].split(b"\0", 1)[0]
        name = name_raw.decode("ascii", "replace")
        if b"FreePSXBoot" in f[10:31] or b"FREEPSXBOOT" in f[10:31].upper():
            d.freepsxboot = True
        chain = [b]
        problems: list[str] = []
        cur, cur_next = b, nxt
        complete = cur_next == NO_NEXT
        while cur_next != NO_NEXT:
            if cur_next > 14:
                problems.append("ps1.p.bad_link")
                break
            nb = cur_next + 1
            if nb in chain:
                problems.append("ps1.p.loop")
                break
            if states[nb - 1] not in (mid, last):
                problems.append("ps1.p.broken_chain")
                break
            chain.append(nb)
            cur = nb
            cur_next = struct.unpack_from("<H", _frame(raw, nb), 8)[0]
            if states[nb - 1] == last:
                complete = True
                if cur_next != NO_NEXT:
                    problems.append("ps1.p.bad_link")
                break
        if not complete and not problems:
            problems.append("ps1.p.broken_chain")
        if size != len(chain) * BLOCK:
            problems.append("ps1.p.size")
        first = _block(raw, b)
        if first[:2].upper() != b"SC":
            problems.append("ps1.p.no_title")
        entry = Ps1Entry(
            block=b, blocks=chain, name=name, title=decode_title(first[4:68]) if first[:2].upper() == b"SC" else "",
            declared_size=size, deleted=deleted, icon=read_icon(first),
            pocketstation=_is_pocketstation(name_raw, first), problems=problems,
            comment=(comments[b - 1] if comments else ""),
        )
        d.saves.append(entry)
        if not deleted:
            for x in chain:
                if x in owner:
                    d.nonstandard = True
                    d.errors.append(t("ps1.chk.cross_link", block=x))
                owner[x] = b

    reached = {x for s in d.saves for x in s.blocks}
    d.lost = [b for b in range(1, 16) if states[b - 1] in (ST_MIDDLE, ST_LAST) and b not in reached]
    if d.lost:
        d.warnings.append(t("ps1.chk.lost", blocks=", ".join(map(str, d.lost))))

    live_names = {}
    for s in d.saves:
        if s.deleted:
            continue
        if s.name in live_names:
            d.warnings.append(t("ps1.chk.duplicate", name=s.name))
        live_names[s.name] = s
        for p in s.problems:
            (d.errors if p in ("ps1.p.broken_chain", "ps1.p.loop", "ps1.p.bad_link") else d.warnings).append(
                t(p, name=s.name, block=s.block))
    for s in d.saves:
        if s.deleted:
            # restorable while its chain is intact (no block reused by another save)
            s.restorable = (
                not set(s.problems) & {"ps1.p.broken_chain", "ps1.p.loop", "ps1.p.bad_link"}
                and s.name not in live_names and all(x not in owner for x in s.blocks)
            )

    for i in range(16, 36):  # broken sector list
        if _frame(raw, i)[:4] not in (b"\xff\xff\xff\xff", b"\x00\x00\x00\x00"):
            d.warnings.append(t("ps1.chk.bad_sectors"))
            break
    if d.freepsxboot:
        d.nonstandard = True
    d.saves.sort(key=lambda s: s.block)
    return d


# ---------------------------------------------------------------------------
# Single saves


@dataclass
class Ps1SaveFile:
    """One save outside a card: its directory frame (name...) and its blocks."""

    frame: bytes  # 128 bytes; only the name (and unknown extra bytes) matter
    data: bytes  # n * 8192
    format: str = "mcs"
    signed: bool | None = None  # .psv

    @property
    def name(self) -> str:
        return self.frame[10:10 + NAME_LEN + 1].split(b"\0", 1)[0].decode("ascii", "replace")

    @property
    def blocks(self) -> int:
        return len(self.data) // BLOCK

    @property
    def title(self) -> str:
        return decode_title(self.data[4:68]) if self.data[:2].upper() == b"SC" else ""

    @property
    def serial(self) -> str | None:
        return split_name(self.name)[1]

    def renamed(self, name: str) -> "Ps1SaveFile":
        f = bytearray(self.frame)
        f[10:10 + NAME_LEN + 1] = bytes(NAME_LEN + 1)
        f[10:10 + len(name)] = name.encode("ascii")
        return Ps1SaveFile(frame=bytes(f), data=self.data, format=self.format, signed=self.signed)


_FORMAT_NAMES = {
    "mcs": "PSXGameEdit / MemcardRex (.mcs)",
    "psx": "Action Replay / GameShark / Xploder (.psx)",
    "psv": "PS3 (.psv)",
    "raw": "Raw save",
}


def format_name(fmt: str) -> str:
    return _FORMAT_NAMES.get(fmt, fmt)


def validate_save_name(name: str) -> str:
    CardError, _, _ = _card_errors()
    try:
        raw = name.encode("ascii")
    except UnicodeEncodeError:
        raise CardError("name.ascii", name=name) from None
    if not raw or len(raw) > NAME_LEN or any(c < 0x20 or c > 0x7E for c in raw):
        raise CardError("ps1.bad_name", name=name, max=NAME_LEN)
    return name


def _make_frame(name: bytes) -> bytes:
    f = bytearray(FRAME)
    f[0] = ST_FIRST
    f[10:10 + min(len(name), NAME_LEN)] = name[:NAME_LEN]
    return bytes(f)


def _pad_blocks(data: bytes) -> bytes:
    rem = len(data) % BLOCK
    return data + bytes(BLOCK - rem) if rem else data


def sniff_save(data: bytes) -> str | None:
    """Format of a single PS1 save, or None."""
    if data.startswith(PSV_MAGIC) and len(data) > PSV_HEADER and data[0x3C] == 1:
        return "psv"
    if len(data) >= FRAME + BLOCK and data[0] == ST_FIRST and data[FRAME:FRAME + 2].upper() == b"SC":
        return "mcs"
    if len(data) >= AR_HEADER + 2 and data[AR_HEADER:AR_HEADER + 2].upper() == b"SC":
        return "psx"
    if data[:2].upper() == b"SC" and len(data) >= FRAME * 2:
        return "raw"
    return None


def is_ps2_psv(data: bytes) -> bool:
    return data.startswith(PSV_MAGIC) and len(data) > 0x40 and data[0x3C] == 2


def name_from_filename(filename: str) -> str:
    """Save name for a raw save, from its file name ('...-BASLUS-00067DRAX00.srm' -> 'BASLUS-00067DRAX00')."""
    base = PurePath(filename).name
    matches = list(_SAVE_NAME_IN_TEXT.finditer(base))
    if matches:
        m = matches[-1]  # file names often start with the game's name
        return f"{m.group(1).upper()}{m.group(2).upper()}-{m.group(3)}{m.group(4)}"[:NAME_LEN]
    stem = PurePath(base).stem
    clean = "".join(c for c in stem if 0x20 <= ord(c) < 0x7F)
    return (clean or "SAVE")[:NAME_LEN]


def load_save(data: bytes, filename: str = "") -> Ps1SaveFile:
    """Parses a single PS1 save. Raises CardError."""
    CardError, _, _ = _card_errors()
    fmt = sniff_save(data)
    if fmt is None:
        if is_ps2_psv(data):
            raise CardError("ps1.save_is_ps2", name=filename or "?")
        raise CardError("ps1.save_unknown", name=filename or "?")
    signed = None
    if fmt == "mcs":
        frame, body = data[:FRAME], data[FRAME:]
    elif fmt == "psv":
        start = struct.unpack_from("<I", data, 0x44)[0] or PSV_HEADER
        size = struct.unpack_from("<I", data, 0x40)[0]
        body = data[start:start + size] if size else data[start:]
        frame = _make_frame(data[0x64:0x64 + NAME_LEN].split(b"\0", 1)[0])
        signed = signing.is_signed(data, 0x08, 0x1C)
    elif fmt == "psx":
        frame = _make_frame(data[0:NAME_LEN].split(b"\0", 1)[0])
        body = data[AR_HEADER:]
    else:
        frame = _make_frame(name_from_filename(filename).encode("ascii", "replace"))
        body = data
    body = _pad_blocks(bytes(body))
    if not body or len(body) > BLOCKS * BLOCK:
        raise CardError("ps1.save_size", name=filename or "?", size=len(body))
    sf = Ps1SaveFile(frame=bytes(frame), data=body, format=fmt, signed=signed)
    if not sf.name.strip():
        sf = sf.renamed(name_from_filename(filename))
    return sf


def dump_save(sf: Ps1SaveFile, fmt: str) -> bytes:
    CardError, _, _ = _card_errors()
    if fmt == "mcs":
        f = bytearray(sf.frame)
        f[0] = ST_FIRST
        f[4:8] = struct.pack("<I", len(sf.data))
        f[8:10] = b"\xff\xff" if sf.blocks == 1 else struct.pack("<H", 0)  # MemcardRex writes the next pointer of the source; it is not used
        f[127] = _xor(f)
        return bytes(f) + sf.data
    if fmt == "psv":
        h = bytearray(PSV_HEADER)
        h[0:4] = PSV_MAGIC
        h[0x08:0x1C] = hashlib.sha1(sf.data).digest()  # salt seed: any value works
        struct.pack_into("<I", h, 0x38, 0x14)
        struct.pack_into("<I", h, 0x3C, 1)  # PS1
        struct.pack_into("<I", h, 0x40, len(sf.data))
        struct.pack_into("<I", h, 0x44, PSV_HEADER)
        struct.pack_into("<I", h, 0x48, 0x200)  # title + icon frames
        struct.pack_into("<I", h, 0x5C, len(sf.data))
        struct.pack_into("<I", h, 0x60, 0x9003)
        name = sf.name.encode("ascii", "replace")[:NAME_LEN]
        h[0x64:0x64 + len(name)] = name
        return signing.sign(bytes(h) + sf.data, 0x08, 0x1C)
    raise CardError("save.bad_format", format=fmt)


def export_filename(sf: Ps1SaveFile, fmt: str) -> str:
    from .card import safe_local_name

    if fmt == "psv":
        # PS3 style: product code + the rest of the name in hex (BASLUS-00067 + 4452415830 ...)
        name = sf.name
        return safe_local_name(name[:12] + name[12:].encode("ascii", "replace").hex().upper()) + ".PSV"
    return safe_local_name(sf.name) + EXPORT_FORMATS[fmt]


# ---------------------------------------------------------------------------
# Editing


class Ps1Editor:
    """Changes to a copy of the card. Use through ``Ps1Card.edit()``."""

    def __init__(self, raw: bytearray, comments: list[str]):
        self.raw = raw
        self.comments = comments
        self.changes: list[str] = []

    # -- reading ---------------------------------------------------------

    def directory(self) -> Directory:
        return parse_directory(bytes(self.raw), self.comments)

    def find(self, path: str) -> Ps1Entry:
        CardError, _, _ = _card_errors()
        block = _path_block(path)
        for s in self.directory().saves:
            if s.block == block:
                return s
        raise CardError("err.not_found", path=path)

    def export_save(self, path: str) -> Ps1SaveFile:
        return _export(bytes(self.raw), self.find(path))

    # -- writing ---------------------------------------------------------

    def _write_frame(self, block: int, frame: bytes | bytearray) -> None:
        f = bytearray(frame)
        f[127] = _xor(f)
        self.raw[FRAME * block:FRAME * (block + 1)] = f

    def _free(self, blocks: list[int]) -> None:
        for b in blocks:
            f = bytearray(FRAME)
            f[0] = ST_FREE
            f[8:10] = b"\xff\xff"
            self._write_frame(b, f)
            self.comments[b - 1] = ""

    def import_save(self, sf: Ps1SaveFile, overwrite: bool = False, name: str | None = None) -> str:
        CardError, ExistsError, NoSpaceError = _card_errors()
        if name is not None:
            sf = sf.renamed(validate_save_name(name))
        validate_save_name(sf.name)
        n = sf.blocks
        if n < 1 or n > BLOCKS or len(sf.data) != n * BLOCK:
            raise CardError("ps1.save_size", name=sf.name, size=len(sf.data))
        d = self.directory()
        same = [s for s in d.live() if s.name == sf.name]
        if same and not overwrite:
            raise ExistsError("err.exists", path=sf.name)
        # an overwritten save gives its blocks back first
        freed = sorted(b for s in same for b in s.blocks)
        available = freed + [b for b in d.free_blocks() if b not in freed]
        if len(available) < n:
            raise NoSpaceError("ps1.no_space", need=n, free=len(available))
        self._free(freed)
        blocks = available[:n]
        for i, b in enumerate(blocks):
            last = i == n - 1
            if i == 0:
                f = bytearray(sf.frame)
                f[0] = ST_FIRST
                f[4:8] = struct.pack("<I", n * BLOCK)
            else:
                f = bytearray(FRAME)  # link frames carry no name or size
                f[0] = ST_LAST if last else ST_MIDDLE
            f[8:10] = b"\xff\xff" if last else struct.pack("<H", blocks[i + 1] - 1)
            self._write_frame(b, f)
            self.raw[BLOCK * b:BLOCK * (b + 1)] = sf.data[BLOCK * i:BLOCK * (i + 1)]
            self.comments[b - 1] = ""
        self.changes.append(t("change.import", path=sf.name))
        return f"/{blocks[0]}"

    def remove(self, path: str) -> None:
        """Deletes a save the way the console does (it can be restored until its blocks are reused)."""
        CardError, _, _ = _card_errors()
        s = self.find(path)
        if s.deleted:
            raise CardError("ps1.already_deleted", name=s.name)
        flip = {ST_FIRST: ST_DEL_FIRST, ST_MIDDLE: ST_DEL_MIDDLE, ST_LAST: ST_DEL_LAST}
        self._flip(s.blocks, flip)
        self.changes.append(t("change.remove", path=s.name))

    def restore(self, path: str) -> None:
        CardError, ExistsError, _ = _card_errors()
        s = self.find(path)
        if not s.deleted:
            raise CardError("ps1.not_deleted", name=s.name)
        if not s.restorable:
            if any(x.name == s.name for x in self.directory().live()):
                raise ExistsError("ps1.restore_exists", name=s.name)
            raise CardError("ps1.not_restorable", name=s.name)
        flip = {ST_DEL_FIRST: ST_FIRST, ST_DEL_MIDDLE: ST_MIDDLE, ST_DEL_LAST: ST_LAST}
        self._flip(s.blocks, flip)
        self.changes.append(t("change.restore", path=s.name))

    def _flip(self, blocks: list[int], flip: dict[int, int]) -> None:
        for b in blocks:
            f = bytearray(_frame(self.raw, b))
            f[0] = flip.get(f[0], f[0])
            self._write_frame(b, f)

    def copy_from(self, src: "Ps1Card", paths: list[str], overwrite: bool = False) -> None:
        """Copies saves from another card ("/" = all of them). Deleted and broken saves are skipped."""
        CardError, _, _ = _card_errors()
        d = src.directory()
        if d.freepsxboot:
            raise CardError("ps1.freepsxboot")
        wanted = list(d.live()) if any(_norm(p) == "/" for p in paths) else [src.find(p) for p in paths]
        for s in wanted:
            if s.deleted or set(s.problems) & {"ps1.p.broken_chain", "ps1.p.loop", "ps1.p.bad_link"}:
                continue
            self.import_save(_export(src.raw, s), overwrite=overwrite)

    def format_card(self) -> None:
        self.raw[:] = blank_card()
        self.comments[:] = [""] * BLOCKS
        self.changes.append(t("change.format"))


def _norm(path: str) -> str:
    return "/" + path.strip().strip("/")


def _path_block(path: str) -> int:
    CardError, _, _ = _card_errors()
    p = _norm(path)[1:]
    if not p.isdigit() or not 1 <= int(p) <= 15:
        raise CardError("err.not_found", path=path)
    return int(p)


def _export(raw: bytes, s: Ps1Entry) -> Ps1SaveFile:
    frame = bytearray(_frame(raw, s.block))
    data = b"".join(_block(raw, b) for b in s.blocks)
    return Ps1SaveFile(frame=bytes(frame), data=data)


# ---------------------------------------------------------------------------
# Card


@dataclass
class Ps1Info:
    path: Path
    format: CardFormat
    total_bytes: int
    free_bytes: int

    @property
    def used_bytes(self) -> int:
        return self.total_bytes - self.free_bytes


class Ps1Card:
    """A PS1 card image open for reading; changes go through :meth:`edit`."""

    platform = Platform.PS1

    def __init__(self, path: str | os.PathLike, make_backups: bool = True):
        self.path = Path(path).resolve()
        self.make_backups = make_backups
        self.last_backup: Path | None = None
        self._initial_ok: bool | None = None
        self.reload()

    def reload(self) -> None:
        CardError, _, _ = _card_errors()
        try:
            data = self.path.read_bytes()
        except OSError as e:
            raise FormatError("fmt.read_failed", error=e) from e
        u = unwrap(data)
        self.container = u.container
        self.raw = u.raw
        self.header = u.header
        self.signed = u.signed
        self.comments = gme_comments(u.header) if u.container == "gme" else [""] * BLOCKS
        self.format = CardFormat(
            platform=Platform.PS1, layout=Layout.RAW, origin=origin_of(u.container, self.path.name),
            file_size=len(data), size_mismatch=u.size_mismatch, container=u.container,
        )

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- reading -------------------------------------------------------------

    def directory(self) -> Directory:
        return parse_directory(self.raw, self.comments)

    @property
    def read_only(self) -> bool:
        return self.directory().nonstandard

    def saves(self) -> list[Ps1Entry]:
        return self.directory().saves

    def find(self, path: str) -> Ps1Entry:
        CardError, _, _ = _card_errors()
        block = _path_block(path)
        for s in self.saves():
            if s.block == block:
                return s
        raise CardError("err.not_found", path=path)

    def export_save(self, path: str) -> Ps1SaveFile:
        CardError, _, _ = _card_errors()
        s = self.find(path)
        if s.deleted:
            raise CardError("ps1.export_deleted", name=s.name)
        return _export(self.raw, s)

    def total_bytes(self) -> int:
        return BLOCKS * BLOCK

    def free_bytes(self) -> int:
        return len(self.directory().free_blocks()) * BLOCK

    def info(self) -> Ps1Info:
        return Ps1Info(path=self.path, format=self.format, total_bytes=self.total_bytes(), free_bytes=self.free_bytes())

    def check(self) -> tuple[bool, list[str]]:
        d = self.directory()
        msgs = list(d.errors) + list(d.warnings)
        if self.container == "vmp" and self.signed is False:
            msgs.append(t("ps1.chk.vmp_signature"))
        if d.freepsxboot:
            msgs.insert(0, t("ps1.freepsxboot"))
        return not d.errors, msgs

    def card_bytes(self, container: str | None = None) -> bytes:
        """The whole image in ``container`` (default: its own)."""
        container = container or self.container
        header = self.header if container == self.container else b""
        return wrap(self.raw, container, header, self.comments)

    # -- editing ---------------------------------------------------------

    @contextlib.contextmanager
    def edit(self) -> Iterator[Ps1Editor]:
        """Changes applied to a copy, checked, then written back atomically (with a backup)."""
        CardError, _, _ = _card_errors()
        d = self.directory()
        if d.nonstandard:
            raise CardError("ps1.freepsxboot" if d.freepsxboot else "ps1.readonly")
        if self._initial_ok is None:
            self._initial_ok = not d.errors
        ed = Ps1Editor(bytearray(self.raw), list(self.comments))
        yield ed
        if not ed.changes:
            return
        new = bytes(ed.raw)
        after = parse_directory(new, ed.comments)
        if (self._initial_ok and after.errors) or after.nonstandard:
            raise CardError("err.verify_failed", details="\n".join((after.errors or [t("ps1.readonly")])[:10]))
        data = wrap(new, self.container, self.header, ed.comments)
        if self.make_backups:
            self.last_backup = _backup.make_backup(self.path)
        tmp = self.path.with_name(f".{self.path.name}.psmm-tmp")
        try:
            tmp.write_bytes(data)
            os.replace(tmp, self.path)
        finally:
            if tmp.exists():
                tmp.unlink()
        self.reload()

    # -- creation / conversion -----------------------------------------------

    @staticmethod
    def create(path: str | os.PathLike, container: str | None = None, overwrite: bool = False) -> "Ps1Card":
        _, ExistsError, _ = _card_errors()
        path = Path(path)
        if path.exists() and not overwrite:
            raise ExistsError("err.exists", path=path)
        container = container or TARGETS[target_for_extension(path.name)][0]
        tmp = path.with_name(f".{path.name}.psmm-tmp")
        try:
            tmp.write_bytes(wrap(blank_card(), container))
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()
        return Ps1Card(path)

    def convert(self, dst: str | os.PathLike, target: str) -> Path:
        """Writes the card in another format (the 128 KB stay byte for byte the same)."""
        CardError, _, _ = _card_errors()
        if target not in TARGETS:
            raise CardError("save.bad_format", format=target)
        dst = Path(dst)
        data = self.card_bytes(TARGETS[target][0])
        if unwrap(data).raw != self.raw:  # never happens; a cheap guarantee
            raise CardError("err.verify_failed", details="PS1")
        tmp = dst.with_name(f".{dst.name}.psmm-conv")
        try:
            tmp.write_bytes(data)
            os.replace(tmp, dst)
        finally:
            if tmp.exists():
                tmp.unlink()
        return dst


def output_name(src_name: str, target: str) -> str:
    return PurePath(src_name).stem + TARGETS[target][1]


# ---------------------------------------------------------------------------
# Games


def group_by_game(card: Ps1Card) -> tuple[dict[str, list[Ps1Entry]], list[Ps1Entry]]:
    groups: dict[str, list[Ps1Entry]] = {}
    others: list[Ps1Entry] = []
    for s in card.directory().live():
        if s.serial:
            groups.setdefault(s.serial, []).append(s)
        else:
            others.append(s)
    return dict(sorted(groups.items())), others


def guess_game_id(card: Ps1Card, filename: str = "") -> str | None:
    from .convert import game_id_from_text

    gid = game_id_from_text(PurePath(filename).name) if filename else None
    if gid:
        return gid
    groups, _ = group_by_game(card)
    if not groups:
        return None
    return max(groups.items(), key=lambda kv: sum(len(s.blocks) for s in kv[1]))[0]


def split_by_game(card: Ps1Card, out_dir: str | os.PathLike, include_others: bool = False) -> list[dict]:
    """One new card per game in ``out_dir`` (``<GAME>.mcd``, raw)."""
    CardError, _, _ = _card_errors()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    groups, others = group_by_game(card)
    if not groups:
        raise CardError("conv.no_games")
    result = []
    for game, saves in groups.items():
        path = out_dir / f"{game}.mcd"
        new = Ps1Card.create(path, "raw", overwrite=True)
        new.make_backups = False
        with new.edit() as ed:
            for s in saves + (others if include_others else []):
                ed.import_save(_export(card.raw, s))
        result.append({"game": game, "path": str(path), "titles": [s.title or s.name for s in saves], "saves": len(saves)})
    return result


# ---------------------------------------------------------------------------
# Opening any card


def is_ps1_image(path: str | os.PathLike) -> bool:
    p = Path(path)
    try:
        size = p.stat().st_size
        with open(p, "rb") as f:
            head = f.read(GME_HEADER + 2)
    except OSError:
        return False
    return sniff(head, size) is not None


def copy_file(src: Path, dst: Path) -> None:
    shutil.copyfile(src, dst)
