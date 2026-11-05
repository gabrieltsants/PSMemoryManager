#!/usr/bin/env python3
# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Downloads the Pyodide files the page needs, for the offline (local app) build.

    python tools/fetch_pyodide.py

The web page loads Pyodide from a CDN; the local app ships it instead. The
files come from the official npm package, pinned by version and SHA-256, and
are cached in ``.cache/pyodide-<version>/``.
"""

from __future__ import annotations

import hashlib
import io
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "0.27.2"  # keep in step with PYODIDE_VERSION in web/worker.js
PACKAGE_URL = f"https://registry.npmjs.org/pyodide/-/pyodide-{VERSION}.tgz"
PACKAGE_SHA256 = "20b9dcca68bbdbf41515ae9c842469142c2333a8c4e59d53a76842c76ff780ba"
LICENSE_URL = f"https://raw.githubusercontent.com/pyodide/pyodide/{VERSION}/LICENSE"
LICENSE_SHA256 = "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5"
# what loadPyodide() fetches when no extra packages are loaded
FILES = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]


def _download(url: str, sha256: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        sys.exit(f"{url}: SHA-256 mismatch (got {got}, expected {sha256})")
    return data


def ensure() -> Path:
    """The folder with the Pyodide files (downloaded on first use)."""
    dest = ROOT / ".cache" / f"pyodide-{VERSION}"
    if all((dest / f).is_file() for f in [*FILES, "LICENSE"]):
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    print(f"downloading Pyodide {VERSION}...")
    with tarfile.open(fileobj=io.BytesIO(_download(PACKAGE_URL, PACKAGE_SHA256)), mode="r:gz") as tar:
        for name in FILES:
            member = tar.extractfile(f"package/{name}")
            if member is None:
                sys.exit(f"{name} not found in the Pyodide package")
            (dest / name).write_bytes(member.read())
    (dest / "LICENSE").write_bytes(_download(LICENSE_URL, LICENSE_SHA256))
    return dest


if __name__ == "__main__":
    print(ensure())
