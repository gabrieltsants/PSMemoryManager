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
- `tools/`: `build_site.py` (site build), `update_gamedb.py` (regenerates `psmm/data/gamedb.json` from PCSX2's GameIndex), `readme_media.py` (README screenshots and GIF).
- `tests/`: pytest suite. `tests/data/ps1/` holds real PS1 files (see its README). Some tests also use a Gen2 SD card dump at `~/psxmemcard_novo` (or `PSMM_SAMPLES`) and are skipped without it.

## Publishing

`.github/workflows/pages.yml` runs the tests and, if they pass, builds the site and pushes it to the `gh-pages` branch (served by GitHub Pages) on every push to `main`.

`tools/build_site.py` stamps a build id (a hash of the site's content) into every asset URL (`app.js?v=<id>`) and writes `version.json`. Source files use the `__BUILD__` placeholder, and any new asset URL or `fetch` in `web/` must carry `?v=__BUILD__`. The page checks `version.json` when it opens, when the tab becomes visible again and every 10 minutes. On a new deploy it reloads by itself if nothing is open, or shows an "update now" bar, so open cards are never lost.

## Translations

The interface is in English (default) and Portuguese. Core messages are keys in `psmm/core/i18n.py`; interface strings are in `web/i18n.js`, and both languages must have the same keys. To add a language, add a column to `psmm/core/i18n.py` and a block to `web/i18n.js`.

## README media

```bash
python tools/build_site.py && python -m http.server -d _site 8765 &
python tools/readme_media.py --url http://127.0.0.1:8765/ --sd DEMO_SD [--vmc A.bin B.bin]
```

`DEMO_SD` is copied into the browser's private storage; the folder itself is never modified. It needs Playwright and ffmpeg.

## History

| Phase | Scope |
|---|---|
| 1 | Core, safe reading/editing, web page, English/Portuguese |
| 2 | Import saves (`.psu`, `.max`, `.cbs`, `.sps`, `.xps`, `.psv`), export `.psu`/`.max`, two cards side by side |
| 3 | Gen2 SD mode: every card and channel, create cards/channels, `settings.ini`, channel names and `Game2Folder.ini` |
| 4 | Conversion between Gen2, OPL, PCSX2 and MemCard PRO2, resize, split by game, merge |
| 5 | PS1 memory cards and saves, `.vmp`/`.psv` signing, PS1 cards on the Gen2 SD card |
