# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Card conversion: format (with/without ECC), size, and one card per game.

* Same size: the image is converted page by page (ECC added or stripped), so
  the file system is bit-for-bit the same.
* Different size: a new card is formatted and everything is copied into it,
  keeping attributes and dates (``CardEditor.clone_from``).
* Split by game: save folders are grouped by game code (``BASLUS-20228...``
  -> ``SLUS-20228``) and each group goes to its own new card.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import ecc as _ecc
from .card import CardError, MemoryCard, NoSpaceError
from .formats import Layout
from .sdcard import normalize_game_id

#: target formats: id -> (extension, has ECC, label)
TARGETS = {
    "gen2": (".mcd", False, "PSxMemCard Gen2 / SD2PSX"),
    "opl": (".bin", False, "OPL VMC"),
    "pcsx2": (".ps2", True, "PCSX2"),
    "mcp2": (".mc2", False, "MemCard PRO2"),
}
SIZES_MB = (1, 2, 4, 8, 16, 32, 64)

_ID_IN_TEXT = re.compile(r"([A-Z]{4})[-_ ]?(\d{3})\.?(\d{2})")


def target_for_extension(path: str | os.PathLike) -> str:
    ext = Path(path).suffix.lower()
    for fid, (e, _, _) in TARGETS.items():
        if e == ext:
            return fid
    return "gen2"


def output_name(src_name: str, target: str) -> str:
    return Path(src_name).stem + TARGETS[target][0]


# ---------------------------------------------------------------------------
# format / size


def convert(src: MemoryCard, dst: str | os.PathLike, *, ecc: bool, size_mb: int | None = None) -> Path:
    """Writes ``src`` to ``dst`` with or without ECC and, optionally, another size."""
    dst = Path(dst)
    fmt = src.format
    if fmt.page_size != _ecc.PAGE:
        raise CardError("conv.page_size", size=fmt.page_size)
    size_mb = int(size_mb or fmt.nominal_mb)
    if size_mb not in SIZES_MB + (128,):
        raise CardError("err.bad_size")
    src_ok, _ = src.check()
    tmp = dst.with_name(f".{dst.name}.psmm-conv")
    try:
        if size_mb == fmt.nominal_mb and not fmt.size_mismatch:
            data = src.path.read_bytes()
            if fmt.layout is Layout.ECC and not ecc:
                data = _ecc.strip_ecc(data)
            elif fmt.layout is Layout.RAW and ecc:
                data = _ecc.add_ecc(data)
            tmp.write_bytes(data)
        else:
            used = src.total_bytes() - src.free_bytes()
            new = MemoryCard.create(tmp, size_mb, ecc=ecc, overwrite=True)
            new.make_backups = False
            try:
                if used > new.total_bytes():
                    raise NoSpaceError("conv.no_fit", used=used // 1024, size=size_mb)
                with new.edit() as ed:
                    ed.clone_from(src)
            finally:
                new.close()
        with MemoryCard(tmp, make_backups=False) as check:
            ok, msgs = check.check()
            if src_ok and not ok:
                raise CardError("err.verify_failed", details="\n".join(msgs[:10]))
        os.replace(tmp, dst)
        return dst
    finally:
        if tmp.exists():
            tmp.unlink()


# ---------------------------------------------------------------------------
# games


def opl_vmc_name(game: str, slot: int = 0) -> str:
    """File name OPL uses for a game's virtual card: 'SLUS-20228' -> 'SLUS_202.28_0.bin'."""
    gid = normalize_game_id(game)
    if gid is None:
        raise CardError("conv.no_game_id", name=game)
    code, num = gid.split("-")
    return f"{code}_{num[:3]}.{num[3:]}_{slot}.bin"


def game_id_from_text(text: str) -> str | None:
    """'SLUS_202.28_0.bin' / 'SLUS-20228-1.mcd' -> 'SLUS-20228'."""
    m = _ID_IN_TEXT.search(text.upper())
    return normalize_game_id("".join(m.groups())) if m else None


@dataclass
class GameGroup:
    game: str  # "SLUS-20228"
    paths: list[str] = field(default_factory=list)  # root folders on the card
    titles: list[str] = field(default_factory=list)


def group_by_game(card: MemoryCard) -> tuple[list[GameGroup], list[str]]:
    """Root folders grouped by game code, plus the folders of no game (system, apps...)."""
    groups: dict[str, GameGroup] = {}
    others: list[str] = []
    for e in card.list_dir("/"):
        gid = e.game_id
        if e.is_dir and gid:
            g = groups.setdefault(gid.serial, GameGroup(gid.serial))
            g.paths.append(e.path)
            g.titles.append(e.title or e.name)
        else:
            others.append(e.path)
    return sorted(groups.values(), key=lambda g: g.game), others


def guess_game_id(card: MemoryCard, filename: str = "") -> str | None:
    """Game code for a card: from the file name (OPL: SLUS_202.28_0.bin), else its most common save."""
    gid = game_id_from_text(Path(filename).name) if filename else None
    if gid:
        return gid
    groups, _ = group_by_game(card)
    if not groups:
        return None
    counts = Counter({g.game: len(g.paths) for g in groups})
    return counts.most_common(1)[0][0]


def split_by_game(
    card: MemoryCard,
    out_dir: str | os.PathLike,
    *,
    size_mb: int = 8,
    ecc: bool = False,
    include_others: bool = False,
    extension: str = ".mcd",
) -> list[dict]:
    """Creates one card per game in ``out_dir`` (named ``<GAME><extension>``)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    groups, others = group_by_game(card)
    if not groups:
        raise CardError("conv.no_games")
    result = []
    for g in groups:
        path = out_dir / f"{g.game}{extension}"
        new = MemoryCard.create(path, size_mb, ecc=ecc, overwrite=True)
        new.make_backups = False
        try:
            with new.edit() as ed:
                ed.copy_from(card, g.paths + (others if include_others else []), "/")
            result.append({"game": g.game, "path": str(path), "titles": g.titles, "saves": len(g.paths)})
        except NoSpaceError as e:
            raise CardError("conv.game_no_fit", game=g.game, size=size_mb, error=e) from e
        finally:
            new.close()
    return result
