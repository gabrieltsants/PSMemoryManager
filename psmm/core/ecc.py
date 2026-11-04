# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fast PS2 memory card ECC (same results as mymc++'s ps2mc_ecc).

Each 512-byte page carries a 16-byte "spare" area: 3 bytes of Hamming code
per 128-byte chunk (12 bytes) followed by 4 zero bytes. mymc++ computes the
code one byte at a time in Python; here the same parities are computed with
whole-chunk operations:

* column parity: the per-byte column masks are linear over GF(2), so their
  XOR equals the mask of the XOR of all bytes;
* line parities: XOR of the indexes of the bytes with odd parity, computed
  bit by bit with popcounts over precomputed index masks.

Identical chunks (empty/erased pages) are computed once.
"""

from __future__ import annotations

from mymcplusplus import ps2mc as _ps2mc
from mymcplusplus import ps2mc_ecc as _ref

CHUNK = 128
PAGE = 512
SPARE = 16

_PARITY = bytes(_ref._parity_table)  # byte -> 0/1
_COLUMN_MASKS = _ref._column_parity_masks  # byte -> 7-bit column mask
# for line parity bit k: one 0x01 byte at every index whose bit k is set
_INDEX_MASKS = [int.from_bytes(bytes(1 if i >> k & 1 else 0 for i in range(CHUNK)), "big") for k in range(7)]
_cache: dict[bytes, tuple[int, int, int]] = {}


def _xor_bytes(chunk: bytes) -> int:
    v = int.from_bytes(chunk, "big")
    width = len(chunk) * 8
    while width > 8:
        width //= 2
        v ^= v >> width
    return v & 0xFF


def _calc(chunk: bytes) -> tuple[int, int, int]:
    hit = _cache.get(chunk)
    if hit is not None:
        return hit
    if len(chunk) != CHUNK:  # odd sizes: use the reference implementation
        return tuple(_ref._ecc_calculate(chunk))
    column = 0x77 ^ _COLUMN_MASKS[_xor_bytes(chunk)]
    odd = int.from_bytes(chunk.translate(_PARITY), "big")  # one 0/1 byte per input byte
    x = 0
    for k, mask in enumerate(_INDEX_MASKS):
        x |= ((odd & mask).bit_count() & 1) << k
    n_odd = odd.bit_count()
    line0 = (0x7F ^ (0x7F if n_odd & 1 else 0) ^ x) & 0x7F
    line1 = 0x7F ^ x
    result = (column, line0, line1)
    if len(_cache) < 4096:
        _cache[bytes(chunk)] = result
    return result


def ecc_calculate(chunk) -> list[int]:
    """Drop-in replacement for mymc++'s ``ecc_calculate`` (returns a list)."""
    return list(_calc(bytes(chunk)))


def ecc_calculate_page(page) -> list[list[int]]:
    """Drop-in replacement for mymc++'s ``ecc_calculate_page``."""
    page = bytes(page)
    return [list(_calc(page[i:i + CHUNK])) for i in range(0, len(page), CHUNK)]


def spare_for_page(page: bytes) -> bytes:
    """The 16-byte spare area mymc++ writes for a 512-byte page."""
    codes = b"".join(bytes(_calc(page[i:i + CHUNK])) for i in range(0, PAGE, CHUNK))
    return codes + b"\0" * (SPARE - len(codes))


def add_ecc(raw: bytes, page_size: int = PAGE) -> bytes:
    """Raw image (pages only) -> image with a spare area after every page."""
    if page_size != PAGE or len(raw) % PAGE:
        raise ValueError("unsupported page size")
    out = bytearray()
    mv = memoryview(raw)
    for off in range(0, len(raw), PAGE):
        page = bytes(mv[off:off + PAGE])
        out += page
        out += spare_for_page(page)
    return bytes(out)


def strip_ecc(data: bytes, page_size: int = PAGE) -> bytes:
    """Image with spare areas -> raw image (pages only)."""
    step = page_size + SPARE
    if page_size != PAGE or len(data) % step:
        raise ValueError("unsupported page size")
    mv = memoryview(data)
    return b"".join(mv[off:off + page_size] for off in range(0, len(data), step))


def install() -> None:
    """Makes mymc++ use the fast ECC (reading and writing .ps2 cards)."""
    _ref.ecc_calculate = ecc_calculate  # used by ecc_check()
    _ref.ecc_calculate_page = ecc_calculate_page
    _ps2mc.ecc_calculate_page = ecc_calculate_page  # imported by name in ps2mc


install()
