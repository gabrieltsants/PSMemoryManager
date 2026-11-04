# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Memory card image format detection.

Detection uses the header (superblock) plus the file size, not ECC trial and
error like mymc++ does. The superblock's "supports ECC" bit (card_flags 0x01)
is set even on images without ECC (Gen2/SD2PSX, OPL), so it cannot be used
to decide.
"""

from __future__ import annotations

import enum
import os
import struct
from dataclasses import dataclass
from pathlib import Path

from .i18n import LocalizedError, t

PS2_MAGIC = b"Sony PS2 Memory Card Format "
PS1_MAGIC = b"MC"
PS1_CARD_SIZE = 128 * 1024

# Superblock offsets (little endian)
_SB_STRUCT = struct.Struct("<28s12sHHHHLLLLLL")
#   magic, version, page_len, pages_per_cluster, pages_per_block, 0xFF00,
#   clusters_per_card, alloc_offset, alloc_end, rootdir_cluster,
#   backup_block1, backup_block2
_CARD_FLAGS_OFFSET = 0x151


class Layout(enum.Enum):
    RAW = "raw"  # data only, 512-byte pages (Gen2/SD2PSX, OPL, MemCard PRO2)
    ECC = "ecc"  # 512-byte pages + 16 bytes of ECC (PCSX2, real card dumps)


class Platform(enum.Enum):
    PS2 = "PS2"
    PS1 = "PS1"


class Origin(enum.Enum):
    """Where the file probably came from (by extension)."""

    GEN2 = "gen2"
    OPL = "opl"
    PCSX2 = "pcsx2"
    MCP2 = "mcp2"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return t(f"origin.{self.value}")


_EXT_ORIGIN = {
    ".mcd": Origin.GEN2,
    ".bin": Origin.OPL,
    ".vmc": Origin.OPL,
    ".ps2": Origin.PCSX2,
    ".mc2": Origin.MCP2,
}

#: extensions accepted by the open dialog
PS2_EXTENSIONS = tuple(_EXT_ORIGIN)


class FormatError(LocalizedError):
    """The file is not a supported memory card image."""


@dataclass(frozen=True)
class CardFormat:
    platform: Platform
    layout: Layout
    origin: Origin
    file_size: int
    page_size: int = 0
    pages_per_cluster: int = 0
    pages_per_block: int = 0
    clusters_per_card: int = 0
    card_flags: int = 0
    version: str = ""
    size_mismatch: bool = False  # file size does not match the superblock

    @property
    def cluster_size(self) -> int:
        return self.page_size * self.pages_per_cluster

    @property
    def nominal_size(self) -> int:
        """Nominal capacity (8 MB, 64 MB...) in bytes, without ECC."""
        return self.clusters_per_card * self.cluster_size

    @property
    def nominal_mb(self) -> int:
        return self.nominal_size // (1024 * 1024)

    def describe(self) -> str:
        if self.platform is Platform.PS1:
            return t("fmt.describe_ps1")
        ecc = t("ecc.yes" if self.layout is Layout.ECC else "ecc.no")
        return t("fmt.describe_ps2", mb=self.nominal_mb, ecc=ecc, origin=self.origin.label)


def raw_size(clusters_per_card: int, page_size: int, pages_per_cluster: int) -> int:
    return clusters_per_card * pages_per_cluster * page_size


def ecc_size(clusters_per_card: int, page_size: int, pages_per_cluster: int) -> int:
    spare = ((page_size + 127) // 128) * 4
    return clusters_per_card * pages_per_cluster * (page_size + spare)


def origin_for(path: str | os.PathLike) -> Origin:
    return _EXT_ORIGIN.get(Path(path).suffix.lower(), Origin.UNKNOWN)


def detect(path: str | os.PathLike) -> CardFormat:
    """Identifies the format of the image at ``path``.

    Raises :class:`FormatError` if it is not a recognized memory card.
    """
    p = Path(path)
    if p.is_dir():
        raise FormatError("fmt.folder_unsupported")
    try:
        size = p.stat().st_size
        with open(p, "rb") as f:
            head = f.read(0x154)
    except OSError as e:
        raise FormatError("fmt.read_failed", error=e) from e

    origin = origin_for(p)

    if head.startswith(PS2_MAGIC) and len(head) >= _SB_STRUCT.size:
        sb = _SB_STRUCT.unpack_from(head)
        version = sb[1].split(b"\0", 1)[0].decode("ascii", "replace")
        page_size, ppc, ppb = sb[2], sb[3], sb[4]
        clusters = sb[6]
        flags = head[_CARD_FLAGS_OFFSET] if len(head) > _CARD_FLAGS_OFFSET else 0
        if page_size not in (512, 1024) or ppc < 1 or ppb < 1 or clusters < 1:
            raise FormatError("fmt.bad_superblock")

        rsize = raw_size(clusters, page_size, ppc)
        esize = ecc_size(clusters, page_size, ppc)
        mismatch = False
        if size == rsize:
            layout = Layout.RAW
        elif size == esize:
            layout = Layout.ECC
        else:
            # unexpected size (truncated or with trailing garbage): pick the
            # closest layout and flag it
            mismatch = True
            layout = Layout.RAW if abs(size - rsize) <= abs(size - esize) else Layout.ECC
            if size < min(rsize, esize) // 2:
                raise FormatError("fmt.truncated", size=size, raw=rsize, ecc=esize)

        return CardFormat(
            platform=Platform.PS2,
            layout=layout,
            origin=origin,
            file_size=size,
            page_size=page_size,
            pages_per_cluster=ppc,
            pages_per_block=ppb,
            clusters_per_card=clusters,
            card_flags=flags,
            version=version,
            size_mismatch=mismatch,
        )

    if head.startswith(PS1_MAGIC) and size in (PS1_CARD_SIZE,):
        return CardFormat(
            platform=Platform.PS1, layout=Layout.RAW, origin=origin, file_size=size
        )

    if size in (0, 8 * 1024 * 1024) and head.strip(b"\xff\x00") == b"":
        raise FormatError("fmt.blank")
    raise FormatError("fmt.unknown")
