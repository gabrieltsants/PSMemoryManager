# Development

[Back to the README](../README.md)

## Running it locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
python tools/build_site.py          # builds the site into _site/
python -m http.server -d _site 8000 # http://localhost:8000
```

The page needs to be served over HTTP (not opened as a file), because it loads Python modules with `fetch`.

## Project layout

- `psmm/core/`: the core, independent of any interface.
  - `formats.py`: detects the card format (PS2/PS1, ECC, origin).
  - `card.py`: PS2 cards (through mymc++), with transactional editing: every change is applied to a copy, checked, backed up and then swapped in.
  - `saves.py`: PS2 save files.
  - `ps1.py`: PS1 cards and saves (containers, directory, icons, editing, checking).
  - `signing.py`: `.vmp`/`.psv` signatures (with a small AES-128 implementation, since Pyodide has none).
  - `convert.py`: PS2 conversion, resizing and splitting by game.
  - `sdcard.py`: Gen2 SD card layout and INI files (works on a file listing, so the browser and the command line share it).
  - `ecc.py`, `backup.py`, `gamedb.py`, `i18n.py`.
- `psmm/web_api.py`: bridge used by the web page. Every function returns JSON.
- `psmm/cli.py`: command line.
- `web/`: the page (HTML/CSS/JS, no build step). Pyodide runs in a Web Worker (`worker.js`). UI strings are in `web/i18n.js`.
  - Start-up: starting Python takes 2–3 s even when everything is in the browser cache. After the first visit, the worker keeps a memory snapshot of Python with `psmm.web_api` already imported (Pyodide's `_makeSnapshot`/`_loadSnapshot`, about 20 MB in Cache Storage under `psmm-python-snapshot`), and later visits restore it in about 0.5 s. The snapshot is tied to the build id and the Pyodide version and is replaced when either changes. If it cannot be read or restored, the worker drops it and starts Python the normal way. The core's files are still written to Pyodide's file system after a restore, because they live outside Python's memory.
  - The worker fetches the core's files in parallel with Python. Their URLs carry the build id, so the browser cache serves them without asking the server again.
- `launcher/`: the local app (Go). One executable that embeds the page and serves it on 127.0.0.1; see [Local app](#local-app).
- `tools/`: `build_site.py` (site build), `build_local.py` and `fetch_pyodide.py` (local app), `update_gamedb.py` (regenerates `psmm/data/gamedb.json` from PCSX2's GameIndex), `readme_media.py` (README screenshots and GIF).
- `tests/`: pytest suite. `tests/data/ps1/` holds real PS1 files (see its README). Some tests also use a Gen2 SD card dump at `~/psxmemcard_novo` (or `PSMM_SAMPLES`) and are skipped without it.

## Publishing

`.github/workflows/pages.yml` runs the tests and, if they pass, builds the site and pushes it to the `gh-pages` branch (served by GitHub Pages) on every push to `main`.

Pyodide is published with the site (`pyodide/`, about 14 MB, served gzipped: about 5.8 MB on a first visit), so the page needs no other server. `tools/fetch_pyodide.py` downloads it from the official npm package, pinned by version and SHA-256, into `.cache/` (cached in CI). To change the Pyodide version, update `VERSION` and both hashes there and `PYODIDE_VERSION` in `web/worker.js`; the build refuses to run if they differ.

`tools/build_site.py` stamps a build id (a hash of the site's content) into every asset URL (`app.js?v=<id>`) and writes `version.json`. Source files use the `__BUILD__` placeholder, and any new asset URL or `fetch` in `web/` must carry `?v=__BUILD__`. The page checks `version.json` when it opens, when the tab becomes visible again and every 10 minutes. On a new deploy it reloads by itself if nothing is open, or shows an "update now" bar, so open cards are never lost.

## Local app

The local app is the same page in a single executable, for people who prefer not to use the website. It needs nothing installed and works without internet.

```bash
python tools/build_local.py --target linux-x86_64   # or windows-x86_64, linux-arm64, windows-arm64; no --target: all. Needs Go 1.22+
./dist/PSMemoryManager-<version>-linux-x86_64       # --no-browser, --port N, --version
```

- `tools/build_local.py` builds the site with `build_site.py` (the same site as GitHub Pages, Pyodide included), gzips every file into `launcher/site/` and compiles `launcher/` into `dist/`. The executable is static (no CGO).
- The launcher listens on `127.0.0.1:47820` only. The port is fixed so the browser keeps the language and theme; if the port is taken by another program it uses a free one, and if PSMemoryManager is already running it just opens the browser again. It answers only requests whose `Host` is its own address (against DNS rebinding) and only `GET`/`HEAD`.
- Files are stored gzipped and sent as they are (`Content-Encoding: gzip`), with the build as ETag.
- The page gets a small script (`/__psmm/local.js`) that keeps a Server-Sent Events connection open. The app quits 45 s after the last tab closes (5 min if no tab ever connects). If it is gone, the page shows a note: what is open keeps working, since everything runs in the browser, but reloading needs the app again.
- `launcher/site/.keep` lets `go vet`/`go test` run without a packed site (CI does this).

## Translations

The interface is in English (default) and Portuguese. Core messages are keys in `psmm/core/i18n.py`; interface strings are in `web/i18n.js`, and both languages must have the same keys. To add a language, add a column to `psmm/core/i18n.py` and a block to `web/i18n.js`.

## README media

```bash
python tools/build_site.py && python -m http.server -d _site 8765 &
python tools/readme_media.py --url http://127.0.0.1:8765/ --sd DEMO_SD [--vmc A.bin B.bin] [--icon-card CARD]
python tools/readme_media.py --url http://127.0.0.1:8765/ --icon-card CARD --only ps2-icons
```

`DEMO_SD` is copied into the browser's private storage; the folder itself is never modified. It needs Playwright, ffmpeg and a GPU (PS2 icons are not drawn with software WebGL). `CARD` is a PS2 card with an animated icon; `ps2-icons.gif` shows the save named by `--icon-save` (Silent Hill 2 by default) turning once, with the page clock driven by hand so the loop is seamless.

## History

| Phase | Scope |
|---|---|
| 1 | Core, safe reading/editing, web page, English/Portuguese |
| 2 | Import saves (`.psu`, `.max`, `.cbs`, `.sps`, `.xps`, `.psv`), export `.psu`/`.max`, two cards side by side |
| 3 | Gen2 SD mode: every card and channel, create cards/channels, `settings.ini`, channel names and `Game2Folder.ini` |
| 4 | Conversion between Gen2, OPL, PCSX2 and MemCard PRO2, resize, split by game, merge |
| 5 | PS1 memory cards and saves, `.vmp`/`.psv` signing, PS1 cards on the Gen2 SD card |
