# PSMemoryManager

[English](README.md) · [Português (Brasil)](README.pt-BR.md)

A **PlayStation 2 and PlayStation 1 memory card manager in your browser**. Open a card, see what is taking up space, move saves between cards, or work with a PSxMemCard Gen2 / SD2PSX card. It also handles OPL VMCs, PCSX2 cards and MemCard PRO2, and PS1 cards from DexDrive, PSP/PS Vita and emulators.

**[Open PSMemoryManager](https://gabrieltsants.github.io/PSMemoryManager/)** — nothing to install.

> Everything is processed locally in your browser (Python via [Pyodide](https://pyodide.org)). No file is uploaded to any server.

> **Before editing:** Back up your memory cards and the full SD card first. Use Chrome or Edge to write changes directly to a Gen2 SD card; Firefox and Safari can only open it read-only. PSMemoryManager is provided as-is and used at your own risk. The project and its contributors are not responsible for lost or corrupted saves, damaged cards, or other data loss or damage resulting from its use.

![PSMemoryManager showing a Gen2 SD card, its memory cards and the saves on an open card](docs/img/hero-light.png)

## What it does

Browse and edit PS2 and PS1 memory cards, import and export saves, convert between common card formats, and manage the cards and channels on a Gen2 SD card. Work on one card or keep two open side by side:

![Copying a save between two memory cards](docs/img/two-cards.gif)

It works on desktop and mobile, in light or dark mode. The interface is available in English and Portuguese, follows the browser language (`pt-*` uses Portuguese), and can be changed in the top bar.

<p align="center">
  <img src="docs/img/import-opl.png" width="49%" alt="Importing OPL virtual memory cards to a Gen2 SD card" />
  <img src="docs/img/convert.png" width="49%" alt="Converting a memory card to the PCSX2 format" />
</p>
<p align="center">
  <img src="docs/img/folder-per-game.png" width="49%" alt="Assigning a memory card folder to a game on the Gen2 SD card" />
  <img src="docs/img/mobile.png" width="25%" alt="PSMemoryManager open on a phone" />
</p>

## Features

- Opens `.mcd` (Gen2/SD2PSX), `.bin` / `.vmc` (OPL), `.ps2` (PCSX2) and `.mc2` (MemCard PRO2) cards.
- Detects automatically whether the image has **ECC**, from the header and the file size.
- Shows saves with the **game name** (read from `icon.sys`), game code, region, size and dates.
- Shows used/free space and flags protected folders (FreeMcBoot, PS2BBL).
- Adds files and folders with the buttons or by **dragging them from your PC** into a folder.
- Extracts a single file as-is, or folders and multiple items as a `.zip`.
- Creates folders, renames and deletes, with **undo** (Ctrl+Z).
- **Saves:**
  - Import `.psu`, `.max`, `.cbs`, `.sps`, `.xps` and `.psv` saves with the button or by dropping them onto a card. Invalid files are listed and skipped.
  - Export saves as `.psu` (recommended: works with wLaunchELF, OPL and PCSX2, and keeps dates and attributes) or `.max` (Action Replay MAX). Several saves are exported as a `.zip`.
- **Two cards side by side:** copy saves between cards with the "Copy" button or by dragging them from one side to the other. Saves copied to the root keep their dates and attributes (including the FreeMcBoot "protected" flag).
- **Gen2 SD card mode:** open the root folder of the SD card and get a side list of every card and channel (PS2, PS1, arcade), with the channel names shown on the device.
  - Click a channel to open it. "Save" writes it straight back to the SD card.
  - Create cards (next `CardN`, or a folder for a game ID such as `SLUS-20963`) and new channels, and delete channels.
  - Edit `settings.ini`, the channel names (`CardN.ini` / `BootCard.ini`) and `Game2Folder.ini`. Unknown keys are kept.
  - For direct editing and writing to the SD card, use **Chrome or Edge**. Firefox and Safari can inspect it read-only; card files can still be downloaded as copies.
- **Whole cards and conversion:**
  - "Import save" also takes whole cards (an OPL VMC `.bin`, a `.mcd`, a PCSX2 `.ps2`…). You can copy their saves into the open card (merging cards), put them on the SD card as the game's card (`MemoryCards/PS2/SLUS-20228/SLUS-20228-1.mcd`; the game code comes from the OPL file name or the saves; an existing game folder gets a new channel), or download a `.zip` laid out for the Gen2 SD card.
  - Convert a card between Gen2 `.mcd`, OPL `.bin`, PCSX2 `.ps2` (with ECC) and MemCard PRO2 `.mc2`, and/or to another size. Same-size conversions are bit-for-bit; resizing copies everything with its dates and attributes.
  - Split a card by game: one card per game, straight to the Gen2 SD card, as a `.zip` for the Gen2 SD card, or as a `.zip` for OPL (`VMC/SLUS_202.28_0.bin`, the names OPL itself uses).
  - Converting to OPL `.bin` suggests OPL's file name for the game (`SLUS_202.28_0.bin`).
  - Resize the open card (1–64 MB). Everything is kept, the change can be undone, and Save writes it back, also to the SD card.
- **PS1 cards:**
  - Opens raw images (`.mcd` Gen2/SD2PSX/MemCard PRO, `.mcr` ePSXe/DuckStation/Mednafen, `.srm` RetroArch…), DexDrive `.gme` (also files cut after the last used block), PSP/PS Vita `.vmp` and Connectix VGS `.vgs`/`.mem`. The format is detected from the content, not the extension.
  - Shows each save with its animated icon, title (Japanese included), game code, region, blocks and where they are on the card, plus a map of the 15 blocks.
  - Imports `.mcs`, `.psv` (PS3), `.psx`/`.mcb`/`.mcx`/`.pda` (Action Replay, GameShark, Xploder) and raw saves; exports `.mcs` or `.psv`.
  - Deletes like the console does: a deleted save stays on the card until its blocks are reused, and can be restored.
  - Copies saves between two PS1 cards, merges whole cards, converts between all the formats above (the 128 KB stay byte for byte the same) and splits a card by game (`MemoryCards/PS1/SLUS-00067/SLUS-00067-1.mcd`).
  - `.vmp` and `.psv` files are **signed**, so the PSP, PS Vita and PS3 accept them. The signature was checked against files made by a real PSP and a real PS3.
  - Cards with a non-standard directory, such as **FreePSXBoot** boot cards, open read-only so they keep working.
  - On the Gen2 SD card, PS1 cards and channels can be opened, created (identical to the ones the Gen2 makes) and saved back.
- **Game titles:** game folders on the SD card show the game's title under the code (`SLUS-20228` → *Silent Hill 2*) with a game icon, and saves show their game in the details. The list of about 12,700 games is loaded only when needed.
- Checks file system integrity.
- Creates new 1–64 MB cards, with or without ECC.
- Saving:
  - **Chrome and Edge** write straight back to the original file, including on the SD card.
  - **Firefox and Safari** download a copy.
- Every change is made on a copy and verified before it is applied.
- Light and dark theme, and it works on phones.

Shortcuts: `Ctrl+O` open · `Ctrl+S` save · `Ctrl+Z` undo · `Ctrl+E` extract · `Ctrl+Shift+N` new folder · `F2` rename · `Del` delete · `Esc` clear selection.

## Roadmap

| Phase | Scope |
|---|---|
| 1 ✅ | Core, safe reading/editing, web page, English/Portuguese |
| 2 ✅ | Import saves (`.psu`, `.max`, `.cbs`, `.sps`, `.xps`, `.psv`), export `.psu`/`.max`, two cards side by side |
| 3 ✅ | Gen2 SD mode: SD card folder with every card and channel, create cards/channels, edit `settings.ini`, channel names and `Game2Folder.ini` |
| 4 ✅ | Conversion: OPL ↔ Gen2 ↔ PCSX2 ↔ MemCard PRO2 (with/without ECC), resize, split per game, merge, OPL VMC → SD game folder |
| 5 ✅ | PS1 memory cards: `.mcd`/`.mcr`/`.srm`, `.gme`, `.vmp`, `.vgs`; saves `.mcs`, `.psv`, `.psx`, raw; Gen2 SD PS1 cards |

## PS2 formats

| Source | Extension | ECC | Size (8 MB) |
|---|---|---|---|
| PSxMemCard Gen2 / SD2PSX | `.mcd` | no | 8,388,608 bytes |
| OPL (VMC) | `.bin` | no | 8,388,608 bytes |
| MemCard PRO2 | `.mc2` | no | 8,388,608 bytes |
| PCSX2 | `.ps2` | yes | 8,650,752 bytes |

On the Gen2, cards live at `MemoryCards/PS2/<folder>/<folder>-<channel>.mcd`. Examples: `MemoryCards/PS2/BOOT/BootCard-1.mcd` and `MemoryCards/PS2/SLUS-20963/SLUS-20963-1.mcd`.

## PS1 formats

| Source | Extension | Size |
|---|---|---|
| PSxMemCard Gen2 / SD2PSX, MemCard PRO, DuckStation | `.mcd` (raw) | 131,072 bytes |
| ePSXe, Mednafen, other emulators | `.mcr` (raw) | 131,072 bytes |
| RetroArch | `.srm` (raw) | 131,072 bytes |
| DexDrive | `.gme` | 134,976 bytes (often shorter) |
| PSP / PS Vita (PS1 Classics) | `.vmp` (signed) | 131,200 bytes |
| Connectix VGS | `.vgs` / `.mem` | 131,136 bytes |

A PS1 card has 15 blocks of 8 KB. On the Gen2, PS1 cards live at `MemoryCards/PS1/<folder>/<folder>-<channel>.mcd`.

## Command line

The same core works in a terminal (Linux and Windows, Python 3.10+). Messages follow the system language, or `--lang en|pt`:

```bash
pip install .
psmm Card1-1.mcd info
psmm Card1-1.mcd ls -r
psmm Card1-1.mcd extract BASLUS-20963 -o saves/
psmm Card1-1.mcd add MySave/ -d /
psmm Card1-1.mcd rm -r BASLUS-20963
psmm Card1-1.mcd check
psmm new New.mcd --size 8
psmm sd /media/SDCARD          # read-only overview of a Gen2 SD card
psmm convert SLUS_202.28_0.bin sh2.ps2          # OPL VMC -> PCSX2 (extension picks the format)
psmm convert card.ps2 card.mcd --size 16        # PCSX2 -> Gen2, 16 MB
psmm split all.mcd /media/SDCARD                # one card per game, in the SD card layout
psmm Card1-1.mcd merge SLUS_202.28_0.bin other.ps2   # copy everything from other cards
psmm Card1-1.mcd resize 16                      # change the size in place (with a backup)

# PS1 (the format is detected from the content)
psmm card.mcr ls                                # saves, blocks, deleted saves
psmm card.mcr import save.mcs other.gme         # saves, or every save of other cards
psmm card.mcr export 3 -o saves/ --format psv   # block number or save name; psv is signed
psmm card.mcr rm BASLUS-00067DRAX00             # restorable: psmm card.mcr restore 1
psmm new Card1-1.vmp --ps1                      # the extension picks the format
psmm convert card.gme SCEVMC0.VMP               # DexDrive -> PSP/Vita
psmm split card.mcr /media/SDCARD               # MemoryCards/PS1/<game>/
```

In the terminal, every change backs up the card first:

- Linux: `~/.local/share/PSMemoryManager/backups`
- Windows: `%LOCALAPPDATA%\PSMemoryManager\backups`

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
python tools/build_site.py          # builds the site into _site/
python -m http.server -d _site 8000 # http://localhost:8000
```

Layout:

- `psmm/core/`: UI-independent core (formats, card, saves, SD card layout and INI files, conversion, fast ECC, PS1 cards and saves, .vmp/.psv signing, backups, translations).
- `psmm/web_api.py`: bridge used by the web page.
- `psmm/cli.py`: command line.
- `web/`: the page (HTML/CSS/JS, no build step). Pyodide runs in a Web Worker. UI strings are in `web/i18n.js`.
- `tools/build_site.py`: builds the site. It also stamps a build id (a hash of the site's content) into every asset URL (`app.js?v=<id>`) and writes `version.json`. The page checks that file when it opens, when the tab becomes visible again and every 10 minutes. On a new deploy it updates by itself if nothing is open, or shows an "update now" bar, so open cards are never lost. Source files use the `__BUILD__` placeholder.
- `.github/workflows/pages.yml`: runs the tests and publishes the site to the `gh-pages` branch (served by GitHub Pages) on every push to `main`.

To add a language, add a column to `psmm/core/i18n.py` (core messages) and a block to `web/i18n.js` (interface).

## Notes

- PS2 `.psv` (PS3) saves can be imported but not exported; mymc++ does not implement writing them. PS1 `.psv` saves are exported (signed).
- Creating cards on the SD card works for PS2, PS1 and arcade (COH). SoulCalibur II Conquest cards use their own format.
- PS1 game titles come from each save's own title; the game list (from PCSX2) only covers PS2 games.
- PS1 saves are not renamed: the name holds the game code the game looks for.
- `.max` export does not keep file dates (the format has no room for them), and its LZARI compression runs in pure Python. Typical game saves take a few seconds, while a multi-megabyte folder can take minutes. Prefer `.psu`.

## Credits and license

Game titles come from PCSX2's [GameIndex.yaml](https://github.com/PCSX2/pcsx2/blob/master/bin/resources/GameIndex.yaml) (PCSX2 is GPL-3.0; its game data credits sonyindex, serialstation, psxdatacenter and redump). Only the code and title are kept, in `psmm/data/gamedb.json`, regenerated with `python tools/update_gamedb.py`.


The PS1 formats follow nocash's PSX specifications and [MemcardRex](https://github.com/ShendoXT/memcardrex) (GPLv3); the `.vmp`/`.psv` signature follows [vita-mcr2vmp](https://github.com/dots-tb/vita-mcr2vmp) (GPLv3). The PS1 test files come from [save-file-converter](https://github.com/euan-forrester/save-file-converter) and [psx_mc_cli](https://github.com/G4Vi/psx_mc_cli) (see `tests/data/ps1/README.md`).

GPLv3. Uses [mymc++](https://github.com/Adubbz/mymcplusplus) by Florian Märkl and others, based on Ross Ridge's mymc (also GPLv3). Inspired by [mcd_viewer](https://github.com/gamebitfunx/mcdviewer), made for the PSxMemCard Gen2.
