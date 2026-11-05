#!/usr/bin/env python3
# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds the static site (GitHub Pages) into ``_site/``.

    python tools/build_site.py [destination] [--offline]

Copies ``web/``, the Python modules used in the browser and the mymc++ wheel,
and writes ``py/manifest.json``, which the worker uses to load everything.

Cache busting: the build id is a hash of everything that goes into the site.
It replaces the ``__BUILD__`` placeholder in HTML/JS/CSS, so every asset URL
changes when its content changes (``app.js?v=<id>``), and it is written to
``version.json``, which the page polls to offer the new version.

``--offline`` (used for the local app, see tools/build_local.py) also copies
Pyodide into ``pyodide/`` and makes the worker load it from there instead of
the CDN, so the page works without internet.
"""

from __future__ import annotations

import hashlib
import json
import re
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
    args = [a for a in sys.argv[1:] if a != "--offline"]
    build(Path(args[0]) if args else ROOT / "_site", offline="--offline" in sys.argv[1:])


def build(out: Path, offline: bool = False) -> str:
    """Builds the site into ``out`` and returns its build id."""
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
    if offline:
        _add_pyodide(out)

    build = _build_id(out)
    for f in out.rglob("*"):
        if f.suffix in (".html", ".js", ".css") and f.is_file():
            text = f.read_text(encoding="utf-8")
            if PLACEHOLDER in text:
                f.write_text(text.replace(PLACEHOLDER, build), encoding="utf-8")
    (out / "version.json").write_text(json.dumps({"build": build, "version": ns["__version__"]}))
    print(f"site built at {out} (build {build}{', offline' if offline else ''})")
    return build


PLACEHOLDER = "__BUILD__"
LOCAL_FLAG = "const PYODIDE_LOCAL = false;"


def _add_pyodide(out: Path) -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    import fetch_pyodide

    worker = out / "worker.js"
    text = worker.read_text(encoding="utf-8")
    m = re.search(r'const PYODIDE_VERSION = "([^"]+)"', text)
    if not m or m.group(1) != fetch_pyodide.VERSION:
        sys.exit(f"web/worker.js uses Pyodide {m and m.group(1)}, tools/fetch_pyodide.py {fetch_pyodide.VERSION}")
    if LOCAL_FLAG not in text:
        sys.exit(f"{LOCAL_FLAG!r} not found in web/worker.js")
    worker.write_text(text.replace(LOCAL_FLAG, "const PYODIDE_LOCAL = true;"), encoding="utf-8")
    src = fetch_pyodide.ensure()
    (out / "pyodide").mkdir()
    for name in fetch_pyodide.FILES:
        shutil.copy2(src / name, out / "pyodide" / name)
    shutil.copy2(src / "LICENSE", out / "pyodide" / "LICENSE.txt")


def _build_id(site: Path) -> str:
    """Hash of every file of the site (before the placeholder is filled in)."""
    h = hashlib.sha256()
    for f in sorted(p for p in site.rglob("*") if p.is_file()):
        h.update(f.relative_to(site).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


if __name__ == "__main__":
    main()
