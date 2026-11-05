# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Automatic backups and user data paths (Linux and Windows)."""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

APP_NAME = "PSMemoryManager"
DEFAULT_KEEP = 20


def data_dir() -> Path:
    """User data folder.

    - Windows: %LOCALAPPDATA%\\PSMemoryManager
    - macOS:   ~/Library/Application Support/PSMemoryManager
    - Linux:   $XDG_DATA_HOME/PSMemoryManager (default ~/.local/share)
    """
    override = os.environ.get("PSMM_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / APP_NAME


def backup_dir() -> Path:
    return data_dir() / "backups"


def _card_key(card: Path) -> str:
    # Card folder + name: ".../PS2/SLUS-20963/SLUS-20963-1.mcd" becomes
    # "PS2_SLUS-20963__SLUS-20963-1", so cards with the same name in different
    # folders (BOOT/BootCard-1 for PS1 and PS2) don't get mixed up.
    parts = [card.parent.parent.name, card.parent.name]
    prefix = "_".join(p for p in parts if p)
    return f"{prefix}__{card.stem}" if prefix else card.stem


def make_backup(card: str | os.PathLike, keep: int = DEFAULT_KEEP) -> Path:
    """Copies ``card`` to the backup folder and keeps only the ``keep`` newest."""
    src = Path(card)
    dest_dir = backup_dir() / _card_key(src)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"{src.stem}_{stamp}{src.suffix}"
    n = 1
    while dest.exists():
        dest = dest_dir / f"{src.stem}_{stamp}-{n}{src.suffix}"
        n += 1
    shutil.copy2(src, dest)
    prune(dest_dir, keep)
    return dest


def prune(folder: Path, keep: int) -> None:
    files = sorted(
        (p for p in folder.iterdir() if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in files[keep:]:
        try:
            old.unlink()
        except OSError:
            pass


def list_backups(card: str | os.PathLike) -> list[Path]:
    folder = backup_dir() / _card_key(Path(card))
    if not folder.is_dir():
        return []
    return sorted(
        (p for p in folder.iterdir() if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
