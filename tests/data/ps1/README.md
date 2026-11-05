# PS1 test files

Real PS1 card images and saves, used by `tests/test_ps1.py` to check that
PSMemoryManager reads, writes and signs them like the original devices.

| File | What it is | Source |
|---|---|---|
| `sotn-dexdrive.gme` | DexDrive card, 2 saves | [save-file-converter](https://github.com/euan-forrester/save-file-converter) (GPLv3), `ps1/dexdrive/castlevania-symphony-of-the-night.1782.gme` |
| `sotn-dexdrive-truncated.gme` | DexDrive card cut after its last used block | save-file-converter, `ps1/dexdrive/castlevania-symphony-of-the-night.1368.gme` |
| `gt-deleted-saves.gme` | DexDrive card with deleted saves and a save split over non-contiguous blocks | save-file-converter, `ps1/dexdrive/gran-turismo.26537.gme` |
| `suikoden2-psp.vmp` | Virtual memory card signed by a real PSP | save-file-converter, `ps1/psp/Suikoden 2-psp-signature.VMP` |
| `BASLUS-0110553595354454D.PSV` | Single save exported by a real PS3 | save-file-converter, `ps1/ps3/Street Fighter EX2 Plus-BASLUS-0110553595354454D.PSV` |
| `sotn.mcr` | Raw card (emulator) | save-file-converter, `ps1/memcard/Castlevania - Symphony of the Night (USA).0.mcr` |
| `gran-turismo-BASCUS-94194RT.srm` | Raw 3-block save without a header | save-file-converter, `ps1/dexdrive/gran-turismo.26537-BASCUS-94194RT.srm` |
| `diablo-jp.mcd` | Raw card with Japanese (Shift-JIS) titles, a 10-block save | [psx_mc_cli](https://github.com/G4Vi/psx_mc_cli) (Perl license: GPL or Artistic), `testdata/Diablo (Japan).mcd` |
| `diablo-10-blocks.mcs` | 10-block `.mcs` save | psx_mc_cli, `testdata/diab1_01.mcs` |
| `tonyhax.mcs` | 1-block `.mcs` save | psx_mc_cli, `testdata/thx.mcs` |
