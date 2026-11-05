# Technical details

[English](formats.md) · [Português (Brasil)](formats.pt-BR.md) · [Back to the README](../README.md)

## PS2 memory cards

| Source | Extension | ECC | Size (8 MB card) |
|---|---|---|---|
| PSxMemCard Gen2 / SD2PSX | `.mcd` | no | 8,388,608 bytes |
| OPL (VMC) | `.bin` / `.vmc` | no | 8,388,608 bytes |
| MemCard PRO2 | `.mc2` | no | 8,388,608 bytes |
| PCSX2, real card dumps | `.ps2` | yes | 8,650,752 bytes |

- **ECC** (error correction) adds 16 bytes to every 512-byte page. Whether an image has it is detected from its header and size, not from the extension. A file whose size does not match its header is opened anyway and flagged as "unexpected size".
- Cards from 1 to 128 MB can be opened. New cards and resizing go from 1 to 64 MB.
- Conversions to the same size are bit for bit (only ECC is added or removed). A resize formats a new card and copies everything, keeping dates and attributes.
- Every change is made on a copy, which is checked (file system check) before it replaces the original. If the card had no errors before, a change that would introduce one is refused.
- File and folder names on the card are ASCII, up to 32 characters.

### PS2 save files

| Format | Import | Export |
|---|---|---|
| uLaunchELF / wLaunchELF / EMS (`.psu`) | yes | yes (recommended: keeps dates and attributes) |
| Action Replay MAX (`.max`) | yes | yes (no dates; compression is slow for large saves) |
| CodeBreaker (`.cbs`) | yes | no |
| SharkPort / X-Port (`.sps`, `.xps`) | yes | no |
| PS3 (`.psv`) | yes | no (mymc++ does not write it) |

Save folders are named like `BASLUS-20963…`: `B` + region letter (`A` America, `E` Europe, `I` Japan, `K` Korea, `C` China) + game code. Saves copied to the root of another card keep their dates and attributes, including the FreeMcBoot "protected" flag.

## PS1 memory cards

A PS1 card has 128 KB: 16 blocks of 8 KB. Block 0 is the directory; blocks 1–15 hold saves, and a save takes one or more blocks (not always next to each other). Each save's first block holds its title (in Shift-JIS, so Japanese titles show correctly) and a 16×16 icon with 1 to 3 animation frames.

| Source | Extension | Size |
|---|---|---|
| PSxMemCard Gen2 / SD2PSX, MemCard PRO, DuckStation | `.mcd` (raw) | 131,072 bytes |
| ePSXe, Mednafen and other emulators | `.mcr` (raw) | 131,072 bytes |
| RetroArch (Beetle PSX, PCSX ReARMed) | `.srm` (raw) | 131,072 bytes |
| Other raw images | `.mc`, `.ps`, `.psm`, `.ddf`, `.mci`, `.vm1`, `.bin` | 131,072 bytes |
| DexDrive | `.gme` | 134,976 bytes (3,904-byte header; often cut after the last used block) |
| PSP / PS Vita (PS1 Classics) | `.vmp` | 131,200 bytes (128-byte signed header) |
| Connectix Virtual Game Station | `.vgs` / `.mem` | 131,136 bytes (64-byte header) |

- The format is detected from the content. A DexDrive file with a damaged header is still recognized.
- Converting between these formats keeps the 128 KB card byte for byte; only the wrapper changes. DexDrive comments are kept when the card stays a `.gme`.
- **Deleting** works like on the console: the save's blocks are only marked as deleted. Until another save reuses them, the save can be restored. New saves use free blocks first, then deleted ones.
- **Signatures:** `.vmp` (PSP/Vita) and `.psv` (PS3) files carry a signature (HMAC-SHA1 with a key derived through AES-128 from a seed in the header). The consoles refuse files whose signature does not match. PSMemoryManager signs every `.vmp` and `.psv` it writes, and the signature was checked against files made by a real PSP and a real PS3.
- **Non-standard cards** open read-only: FreePSXBoot cards (their directory is deliberately broken so the exploit works), and cards whose blocks belong to two saves or have unknown states. Converting them still keeps every byte. Minor problems (wrong checksums, blocks in use by no save, a size that does not match) are reported by **Check** but do not block editing.
- New PS1 cards are byte for byte the same as the empty cards the PSxMemCard Gen2 creates.

### PS1 save files

| Format | Import | Export |
|---|---|---|
| MemcardRex / PSXGameEdit (`.mcs`, `.ps1`) | yes | yes (recommended) |
| PS3 (`.psv`) | yes | yes (signed) |
| Action Replay / GameShark / Xploder / Smart Link (`.psx`, `.mcx`, `.pda`, `.mcb`) | yes | no |
| Raw save (blocks only, any extension) | yes | no |

Save names look like `BASLUS-00067DRAX00`: `BA`/`BE`/`BI` (America/Europe/Japan) + game code + an identifier chosen by the game. A raw save has no name inside, so it is taken from the file name. Exported `.psv` files get the name the PS3 expects (`BASLUS-00067` + the rest of the name in hexadecimal).

## PSxMemCard Gen2 / SD2PSX SD card

```
.sd2psx/settings.ini                     device settings
.sd2psx/Game2Folder.ini                  optional: game code -> folder
MemoryCards/PS2/BOOT/BootCard-1.mcd      boot card (files use the "BootCard" prefix)
MemoryCards/PS2/BOOT/BootCard.ini        channel names
MemoryCards/PS2/Card1/Card1-1.mcd        card 1, channel 1
MemoryCards/PS2/SLUS-20963/SLUS-20963-1.mcd   card for a game code
MemoryCards/PS1/...                      PS1 cards (same scheme)
MemoryCards/COH/... , MemoryCards/SC2/...     arcade / SoulCalibur II Conquest
```

- Each folder has up to 8 channels. Channel names are kept in `<folder>.ini` (`BootCard.ini` for BOOT), in a `[ChannelName]` section.
- With **GameID** switching on, the device opens the folder named after the game's code when the game starts. `Game2Folder.ini` can send a game to another folder.
- When PSMemoryManager edits an INI file it keeps the order, comments and unknown keys.
- Cards can be created for PS2, PS1 and arcade (COH). SoulCalibur II Conquest cards use their own format and are only listed.
- Writing to the SD card needs the File System Access API (Chrome, Edge). Other browsers open it read-only.

## Game titles

PS2 game folders and saves show the game's title, from PCSX2's GameIndex (about 12,700 games, loaded only when needed). It only covers PS2 games: PS1 saves show the title the game wrote into the save.

## Known limitations

- PS2 `.psv` saves can be imported but not exported.
- `.max` export does not keep file dates, and its compression runs in Python: a typical save takes a few seconds, a folder of several MB can take minutes. Prefer `.psu`.
- PS1 saves cannot be renamed: the name holds the code the game looks for.
- PCSX2 folder memory cards are not supported.

## Credits

- [mymc++](https://github.com/Adubbz/mymcplusplus) (GPLv3) by Florian Märkl and others, based on Ross Ridge's mymc: PS2 file system and save formats.
- PS1 formats follow nocash's PSX specifications and [MemcardRex](https://github.com/ShendoXT/memcardrex) (GPLv3). The `.vmp`/`.psv` signature follows [vita-mcr2vmp](https://github.com/dots-tb/vita-mcr2vmp) (GPLv3).
- Game titles come from PCSX2's [GameIndex.yaml](https://github.com/PCSX2/pcsx2/blob/master/bin/resources/GameIndex.yaml) (GPLv3; its game data credits sonyindex, serialstation, psxdatacenter and redump). Only the code and title are kept, in `psmm/data/gamedb.json`.
- The PS1 test files come from [save-file-converter](https://github.com/euan-forrester/save-file-converter) and [psx_mc_cli](https://github.com/G4Vi/psx_mc_cli) (see `tests/data/ps1/README.md`).
- Inspired by [mcd_viewer](https://github.com/gamebitfunx/mcdviewer), made for the PSxMemCard Gen2.
