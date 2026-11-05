#!/usr/bin/env python3
# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds the static site (GitHub Pages) into ``_site/``.

    python tools/build_site.py [destino]

Copies ``web/``, the Python modules used in the browser and the mymc++ wheel,
and writes ``py/manifest.json``, which the worker uses to load everything.

Cache busting: the build id is a hash of everything that goes into the site.
It replaces the ``__BUILD__`` placeholder in HTML/JS/CSS, so every asset URL
changes when its content changes (``app.js?v=<id>``), and it is written to
``version.json``, which the page polls to offer the new version.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_FILES = [
    "psmm/__init__.py",
    "psmm/web_api.py",
    "psmm/core/__init__.py",
    "psmm/core/formats.py",
    "psmm/core/card.py",
    "psmm/core/backup.py",
    "psmm/core/i18n.py",
    "psmm/core/saves.py",
    "psmm/core/sdcard.py",
    "psmm/core/ecc.py",
    "psmm/core/convert.py",
    "psmm/core/ps1.py",
    "psmm/core/signing.py",
]


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "web", out, ignore=shutil.ignore_patterns("vendor"))

    py = out / "py"
    for rel in PY_FILES:
        dest = py / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)

    wheels = sorted((ROOT / "web" / "vendor").glob("mymcplusplus-*.whl"))
    if not wheels:
        sys.exit("mymc++ wheel not found in web/vendor/")
    wheel = wheels[-1]
    shutil.copy2(wheel, py / wheel.name)
    shutil.copy2(ROOT / "LICENSE", out / "LICENSE.txt")
    shutil.copy2(ROOT / "psmm" / "data" / "gamedb.json", out / "gamedb.json")

    ns: dict = {}
    exec((ROOT / "psmm" / "__init__.py").read_text(), ns)
    (py / "manifest.json").write_text(
        json.dumps({"version": ns["__version__"], "wheel": "py/" + wheel.name, "files": PY_FILES}, indent=2)
    )
    (out / ".nojekyll").write_text("")

    build = _build_id(out)
    for f in out.rglob("*"):
        if f.suffix in (".html", ".js", ".css") and f.is_file():
            text = f.read_text(encoding="utf-8")
            if PLACEHOLDER in text:
                f.write_text(text.replace(PLACEHOLDER, build), encoding="utf-8")
    (out / "version.json").write_text(json.dumps({"build": build, "version": ns["__version__"]}))
    print(f"site built at {out} (build {build})")


PLACEHOLDER = "__BUILD__"


def _build_id(site: Path) -> str:
    """Hash of every file of the site (before the placeholder is filled in)."""
    h = hashlib.sha256()
    for f in sorted(p for p in site.rglob("*") if p.is_file()):
        h.update(f.relative_to(site).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


if __name__ == "__main__":
    main()
