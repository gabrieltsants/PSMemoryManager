#!/usr/bin/env python3
# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds psmm/data/gamedb.json (game code -> title) from PCSX2's GameIndex.yaml.

    python tools/update_gamedb.py [GameIndex.yaml]

Without an argument the file is downloaded from the PCSX2 repository. Only
the serial and the title are kept (English title when the index has one), so
the result is small enough for the web page to load on demand.

GameIndex.yaml is part of PCSX2 (GPL-3.0); its game data credits sonyindex,
serialstation, psxdatacenter and redump.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

URL = "https://raw.githubusercontent.com/PCSX2/pcsx2/master/bin/resources/GameIndex.yaml"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "psmm" / "data" / "gamedb.json"

_KEY = re.compile(r"^([A-Z]{4}-\d{5}):\s*$")
_FIELD = re.compile(r"^  (name|name-en):\s*(.+?)\s*$")


def _value(raw: str) -> str:
    if raw.startswith('"'):
        return json.loads(raw)  # YAML double-quoted strings are JSON-compatible here
    if raw.startswith("'"):
        return raw[1:-1].replace("''", "'")
    return raw


def parse(text: str) -> dict[str, str]:
    db: dict[str, str] = {}
    serial = None
    names: dict[str, str] = {}

    def flush():
        if serial and names:
            title = names.get("name-en") or names.get("name")
            if title:
                db[serial] = " ".join(title.split())

    for line in text.splitlines():
        m = _KEY.match(line)
        if m:
            flush()
            serial, names = m.group(1), {}
            continue
        if line and not line.startswith(" "):
            flush()
            serial, names = None, {}
            continue
        f = _FIELD.match(line)
        if f and serial:
            try:
                names[f.group(1)] = _value(f.group(2))
            except (ValueError, IndexError):
                pass
    flush()
    return db


def main() -> None:
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
        source = sys.argv[1]
    else:
        with urllib.request.urlopen(URL, timeout=60) as r:
            text = r.read().decode("utf-8")
        source = URL
    db = parse(text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(db.items())), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT.parent / "gamedb.source.txt").write_text(
        f"Generated {date.today()} by tools/update_gamedb.py from {URL}\n"
        "PCSX2 GameIndex.yaml (PCSX2 is GPL-3.0). Game data credits: sonyindex, serialstation,\n"
        f"psxdatacenter, redump. Entries: {len(db)}\n",
        encoding="utf-8",
    )
    print(f"{OUT}: {len(db)} games, {OUT.stat().st_size // 1024} KB (source: {source})")


if __name__ == "__main__":
    main()
