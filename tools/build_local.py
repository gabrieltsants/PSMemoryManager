#!/usr/bin/env python3
# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Builds the local app: one executable per system with the whole page inside.

    python tools/build_local.py [--target linux-x86_64] ... [--archive]

Builds the site in offline mode (Pyodide included), gzips every file into
``launcher/site/`` and compiles ``launcher/`` with Go into ``dist/``. Needs Go
1.22+; the result runs without anything installed. Without ``--target`` it
builds every target. ``--archive`` also packs each one for download
(``.tar.gz`` on Linux, which keeps the file executable).
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "launcher"
TARGETS = {  # name -> (GOOS, GOARCH, file suffix)
    "linux-x86_64": ("linux", "amd64", ""),
    "linux-arm64": ("linux", "arm64", ""),
}

sys.path.insert(0, str(ROOT / "tools"))
import build_site  # noqa: E402


def pack_site() -> None:
    """Offline site -> launcher/site/<path>.gz (reproducible: no timestamps)."""
    dest = LAUNCHER / "site"
    for old in dest.iterdir() if dest.exists() else []:
        if old.name != ".keep":  # .keep lets Go compile (and test) without a packed site
            shutil.rmtree(old) if old.is_dir() else old.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "site"
        build_site.build(site, offline=True)
        for f in sorted(p for p in site.rglob("*") if p.is_file()):
            out = dest / (f.relative_to(site).as_posix() + ".gz")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(gzip.compress(f.read_bytes(), compresslevel=9, mtime=0))


def compile_target(name: str, version: str) -> Path:
    goos, goarch, suffix = TARGETS[name]
    out = ROOT / "dist" / f"PSMemoryManager-{version}-{name}{suffix}"
    env = {**os.environ, "GOOS": goos, "GOARCH": goarch, "CGO_ENABLED": "0"}
    subprocess.run(
        ["go", "build", "-trimpath", "-ldflags", f"-s -w -X main.version={version}", "-o", str(out), "."],
        cwd=LAUNCHER, env=env, check=True,
    )
    return out


def archive(binary: Path, name: str, version: str) -> Path:
    """dist/PSMemoryManager-<version>-<target>.tar.gz with an executable PSMemoryManager inside."""
    out = ROOT / "dist" / f"PSMemoryManager-{version}-{name}.tar.gz"
    info = tarfile.TarInfo("PSMemoryManager")
    info.size, info.mode, info.mtime = binary.stat().st_size, 0o755, 0
    with tarfile.open(out, "w:gz") as tar, binary.open("rb") as f:
        tar.addfile(info, f)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--target", action="append", choices=sorted(TARGETS), help="system to build for (repeatable)")
    ap.add_argument("--archive", action="store_true", help="also pack each executable for download")
    args = ap.parse_args()
    if not shutil.which("go"):
        sys.exit("Go not found: install Go 1.22 or newer (https://go.dev/dl/)")
    ns: dict = {}
    exec((ROOT / "psmm" / "__init__.py").read_text(), ns)
    version = ns["__version__"]
    pack_site()
    for name in args.target or sorted(TARGETS):
        out = compile_target(name, version)
        if args.archive:
            out = archive(out, name, version)
        print(f"{out.relative_to(ROOT)}  ({out.stat().st_size / 2**20:.1f} MB)")


if __name__ == "__main__":
    main()
