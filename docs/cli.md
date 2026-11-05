# Command line

[English](cli.md) · [Português (Brasil)](cli.pt-BR.md) · [Back to the README](../README.md)

PSMemoryManager also runs in a terminal, on Windows and Linux (macOS should work too). It has the same features as the web page and is handy for scripts and batches of cards.

## 1. Install Python

You need **Python 3.10 or newer**.

- **Windows:** download it from [python.org](https://www.python.org/downloads/). In the installer, tick **“Add python.exe to PATH”**.
- **Linux:** Python is usually installed already. Check with `python3 --version`.

## 2. Download PSMemoryManager

Either clone the repository:

```bash
git clone https://github.com/gabrieltsants/PSMemoryManager.git
```

or, on the [GitHub page](https://github.com/gabrieltsants/PSMemoryManager), click **Code → Download ZIP** and extract it.

## 3. Install it

Open a terminal in the `PSMemoryManager` folder and run:

```bash
pip install .
```

On Windows, if `pip` is not found, use `py -m pip install .`. On some Linux systems you may need a virtual environment first:

```bash
python3 -m venv ~/.psmm && . ~/.psmm/bin/activate
pip install .
```

## 4. Check that it works

```bash
psmm --help
```

If the `psmm` command is not found, `python -m psmm --help` (Windows: `py -m psmm --help`) does the same.

## Using it

Commands have this shape:

```bash
psmm <card file> <command> [options]
```

Messages follow the system language. Add `--lang en` or `--lang pt` to choose. Any command accepts `-h` for its help, for example `psmm Card1-1.mcd export -h`.

**Backups:** every command that changes a card first saves a copy of it in:

- Linux: `~/.local/share/PSMemoryManager/backups`
- Windows: `%LOCALAPPDATA%\PSMemoryManager\backups`

Add `--no-backup` to skip it.

### PS2 cards

| What | Command |
|---|---|
| Format and free space | `psmm Card1-1.mcd info` |
| List the contents (`-r`: inside folders too) | `psmm Card1-1.mcd ls -r` |
| Copy saves or files to your PC | `psmm Card1-1.mcd extract BASLUS-20963 -o saves/` |
| Add files or folders from your PC | `psmm Card1-1.mcd add MySave/ -d /` |
| Create a folder | `psmm Card1-1.mcd mkdir /NEWFOLDER` |
| Delete (`-r`: folders with content) | `psmm Card1-1.mcd rm -r BASLUS-20963` |
| Rename | `psmm Card1-1.mcd rename /OLD NEW` |
| Copy everything from other cards into this one | `psmm Card1-1.mcd merge SLUS_202.28_0.bin other.ps2` |
| Change the size (MB) | `psmm Card1-1.mcd resize 16` |
| Check for errors | `psmm Card1-1.mcd check` |
| Create a new card | `psmm new New.mcd --size 8` (`--ecc` for PCSX2) |

### PS1 cards

The format is recognized from the content (`.mcd`, `.mcr`, `.gme`, `.vmp`…). Saves are picked by their block number (as shown by `ls`) or by name.

| What | Command |
|---|---|
| Format and free blocks | `psmm card.mcr info` |
| List saves, including deleted ones | `psmm card.mcr ls` |
| Import saves (`.mcs`, `.psv`, `.psx`, raw) or every save of other cards | `psmm card.mcr import save.mcs other.gme` |
| Export saves (all of them if none is given) | `psmm card.mcr export 3 -o saves/` |
| Export for the PS3 (signed `.psv`) | `psmm card.mcr export 3 -o saves/ --format psv` |
| Delete a save (it can be restored later) | `psmm card.mcr rm BASLUS-00067DRAX00` |
| Restore a deleted save | `psmm card.mcr restore 1` |
| Check for errors | `psmm card.mcr check` |
| Create a new card (the extension picks the format) | `psmm new Card1-1.mcd --ps1` |

### Converting

The extension of the new file picks the format.

```bash
psmm convert SLUS_202.28_0.bin sh2.ps2       # PS2: OPL -> PCSX2
psmm convert card.ps2 card.mcd --size 16     # PS2: PCSX2 -> Gen2, 16 MB
psmm convert card.gme SCEVMC0.VMP            # PS1: DexDrive -> PSP/Vita
psmm convert SCEVMC0.VMP card.mcr            # PS1: PSP/Vita -> emulators
```

PS2: `.mcd`, `.bin` and `.mc2` are written without ECC, `.ps2` with ECC (`--ecc`/`--no-ecc` override it). PS1: `.mcd`, `.mcr`, `.srm`, `.gme`, `.vmp` and `.vgs`.

### PSxMemCard Gen2 / SD2PSX SD card

```bash
psmm sd /media/SDCARD                        # list cards, channels and settings (read-only)
psmm split all.mcd /media/SDCARD             # one card per game, in the SD card layout
```

`split` creates `MemoryCards/PS2/<game>/<game>-1.mcd` (or `MemoryCards/PS1/…` for PS1 cards). If the game already has a folder, the card becomes a new channel there. `--with-others` also copies the non-game folders into every card, and `-s` sets the size of the new PS2 cards.
