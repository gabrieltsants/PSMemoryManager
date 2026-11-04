# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Game titles by game code (``SLUS-20228`` -> ``Silent Hill 2``).

The data comes from PCSX2's GameIndex.yaml (see psmm/data/gamedb.source.txt),
regenerated with ``tools/update_gamedb.py``. It is loaded on first use.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "gamedb.json"


@lru_cache(maxsize=1)
def _db() -> dict[str, str]:
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def title(game_code: str | None) -> str | None:
    """Title of a game code like 'SLUS-20228' (None if unknown)."""
    if not game_code:
        return None
    return _db().get(game_code.strip().upper())
