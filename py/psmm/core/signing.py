# This file is part of PSMemoryManager.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Signatures of PS1 virtual memory cards (.vmp, PSP / PS Vita) and PS3 saves (.psv).

Both files carry a 20-byte "salt seed" and a 20-byte signature in their
header. The signature is HMAC-SHA1 of the whole file (with the signature
field zeroed), keyed with 20 bytes derived from the seed through AES-128 and
a fixed key/IV pair. This is the algorithm used by vita-mcr2vmp and MemcardRex
(both GPLv3), written here as a plain HMAC.

The PSP and the PS3 refuse files whose signature does not match, so every
.vmp and .psv written by PSMemoryManager is signed.

AES is implemented here (one 16-byte block at a time is all that is needed)
because the browser build (Pyodide) ships no AES module.
"""

from __future__ import annotations

import hashlib
import hmac

KEY = bytes.fromhex("AB5ABC9FC1F49DE6A051DBAEFA518859")
IV = bytes.fromhex("B30FFEEDB7DC5EB7133DA60D1B6B2CDC")

# ---------------------------------------------------------------------------
# AES-128, one block (FIPS-197)


def _xtime(a: int) -> int:
    a <<= 1
    return (a ^ 0x11B) if a & 0x100 else a


def _mul(a: int, b: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r


def _make_sbox() -> tuple[bytes, bytes]:
    # multiplicative inverses through log/antilog tables (generator 3): fast enough at import time
    exp = [0] * 255
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x ^= _xtime(x)  # x * 3
    sbox = bytearray(256)
    for x in range(256):
        b = exp[(255 - log[x]) % 255] if x else 0
        s = b
        for _ in range(4):
            b = ((b << 1) | (b >> 7)) & 0xFF
            s ^= b
        sbox[x] = s ^ 0x63
    inv_sbox = bytearray(256)
    for i, v in enumerate(sbox):
        inv_sbox[v] = i
    return bytes(sbox), bytes(inv_sbox)


_SBOX, _INV_SBOX = _make_sbox()
_RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _expand_key(key: bytes) -> list[list[int]]:
    w = [list(key[i:i + 4]) for i in range(0, 16, 4)]
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[b] for b in t]
            t[0] ^= _RCON[i // 4 - 1]
        w.append([a ^ b for a, b in zip(w[i - 4], t)])
    return [sum(w[r * 4:r * 4 + 4], []) for r in range(11)]


def _add(state: list[int], rk: list[int]) -> list[int]:
    return [a ^ b for a, b in zip(state, rk)]


# state is column-major: byte i = row (i % 4), column (i // 4)
_SHIFT = [((i % 4) + 4 * (((i // 4) + (i % 4)) % 4)) for i in range(16)]
_INV_SHIFT = [0] * 16
for _i, _s in enumerate(_SHIFT):
    _INV_SHIFT[_s] = _i


def _mix(col: list[int], m: tuple[int, int, int, int]) -> list[int]:
    return [
        _mul(col[0], m[(0 - r) % 4]) ^ _mul(col[1], m[(1 - r) % 4]) ^ _mul(col[2], m[(2 - r) % 4]) ^ _mul(col[3], m[(3 - r) % 4])
        for r in range(4)
    ]


def _mix_columns(s: list[int], m) -> list[int]:
    out: list[int] = []
    for c in range(4):
        out += _mix(s[c * 4:c * 4 + 4], m)
    return out


def aes_encrypt_block(key: bytes, block: bytes) -> bytes:
    rk = _expand_key(key)
    s = _add(list(block), rk[0])
    for r in range(1, 11):
        s = [_SBOX[b] for b in s]
        s = [s[_SHIFT[i]] for i in range(16)]
        if r != 10:
            s = _mix_columns(s, (2, 3, 1, 1))
        s = _add(s, rk[r])
    return bytes(s)


def aes_decrypt_block(key: bytes, block: bytes) -> bytes:
    rk = _expand_key(key)
    s = _add(list(block), rk[10])
    for r in range(9, -1, -1):
        s = [s[_INV_SHIFT[i]] for i in range(16)]
        s = [_INV_SBOX[b] for b in s]
        s = _add(s, rk[r])
        if r != 0:
            s = _mix_columns(s, (14, 11, 13, 9))
    return bytes(s)


# ---------------------------------------------------------------------------
# Sony save signature


def hmac_key(seed: bytes) -> bytes:
    """The 20-byte HMAC key derived from a 20-byte salt seed."""
    if len(seed) != 20:
        raise ValueError("the salt seed has 20 bytes")
    head = seed[:16]
    k1 = bytes(a ^ b for a, b in zip(aes_decrypt_block(KEY, head), IV))
    k2 = bytes(a ^ b for a, b in zip(aes_encrypt_block(KEY, head)[:4], seed[16:20]))
    return k1 + k2


def signature(data: bytes, seed_offset: int, sig_offset: int) -> bytes:
    """Signature of ``data`` (a whole .vmp/.psv file); the signature field is ignored."""
    buf = bytearray(data)
    buf[sig_offset:sig_offset + 20] = bytes(20)
    seed = bytes(buf[seed_offset:seed_offset + 20])
    return hmac.new(hmac_key(seed), bytes(buf), hashlib.sha1).digest()


def sign(data: bytes, seed_offset: int, sig_offset: int) -> bytes:
    """``data`` with its signature field filled in."""
    buf = bytearray(data)
    buf[sig_offset:sig_offset + 20] = signature(data, seed_offset, sig_offset)
    return bytes(buf)


def is_signed(data: bytes, seed_offset: int, sig_offset: int) -> bool:
    return hmac.compare_digest(bytes(data[sig_offset:sig_offset + 20]), signature(data, seed_offset, sig_offset))
