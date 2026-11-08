# PS2 test files

Real PS2 card and save files, used by `tests/test_ps2_real.py` to check that
PSMemoryManager reads, converts, imports and exports them like the original
tools.

All of them come from the test data of [mymc++](https://github.com/Adubbz/mymcplusplus)
(GPLv3), `test/data.tar.gz` (commit `3247c9c`).

| File | What it is |
|---|---|
| `mc01.ps2.gz` | 8 MB card with ECC, holding a Rez save (`BESCES-50501REZ`) and the console's `BEDATA-SYSTEM`. It is gzipped here (it is mostly empty); the tests unpack it. |
| `BESCES-50501REZ.cbs` | The same Rez save, CodeBreaker format |
| `BESCES-50501REZ.max` | The same save, Action Replay MAX format (compressed) |
| `BESCES-50501REZ.psu` | The same save, EMS / uLaunchELF format |
| `BESCES-50501REZ.sps` | The same save, SharkPort format |
| `BESCES-50501REZ.xps` | The same save, X-Port format (same layout as SharkPort) |
| `BESCES-5050152455A.PSV` | A Rez save exported by a PS3, from a later play session (same files, different progress) |
