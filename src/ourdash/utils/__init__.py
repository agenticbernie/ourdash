"""Shared hashing / checksum helpers for the ourdash SDK.

This is Dash (dash.org crypto — not Plotly Dash) plumbing: double-SHA-256
checksums and Base58Check encode/decode used by address validation
(:mod:`ourdash.core.addresses`).

Hashing boundary (v0.1): X11 (the eleven-hash chain) is **block-hashing
only**. Transactions, Merkle trees, and addresses use SHA-256 / RIPEMD-160
via :mod:`hashlib`. X11 is explicitly NOT implemented here or anywhere in
v0.1 — do not add it to a transaction or address path.

This module is stdlib-only (:mod:`hashlib`; manual Base58, no third-party
``base58`` import) so it stays importable from every layer, including the
pydantic-free transport seam.
"""

from __future__ import annotations

import hashlib

from ourdash.errors import AddressError
from ourdash.redact import redact

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {char: index for index, char in enumerate(_B58_ALPHABET)}
_CHECKSUM_LEN = 4


def sha256d(data: bytes) -> bytes:
    """Return double-SHA-256 (SHA-256 of SHA-256) of ``data``."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def b58_encode(raw: bytes) -> str:
    """Encode bytes as plain Base58 (no checksum)."""
    if not raw:
        return ""
    leading_ones = len(raw) - len(raw.lstrip(b"\x00"))
    number = int.from_bytes(raw, "big")
    encoded = ""
    while number > 0:
        number, remainder = divmod(number, 58)
        encoded = _B58_ALPHABET[remainder] + encoded
    return "1" * leading_ones + encoded


def b58check_encode(payload: bytes) -> str:
    """Encode ``payload`` (e.g. version byte + 20-byte hash) with a Base58Check checksum."""
    return b58_encode(payload + sha256d(payload)[:_CHECKSUM_LEN])


def b58check_decode(addr: str) -> bytes:
    """Decode a Base58Check string, returning the payload (without checksum).

    Raises :class:`ourdash.errors.AddressError` on bad charset, degenerate
    length (fewer than 1 payload byte + 4 checksum bytes), or checksum
    mismatch.
    """
    if not isinstance(addr, str) or not addr:
        raise AddressError(f"invalid Base58Check input {redact(addr)!r}")
    number = 0
    for char in addr:
        digit = _B58_INDEX.get(char)
        if digit is None:
            raise AddressError(f"Base58Check address has bad charset {redact(addr)!r}")
        number = number * 58 + digit
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    leading_ones = len(addr) - len(addr.lstrip("1"))
    raw = b"\x00" * leading_ones + raw
    if len(raw) < 1 + _CHECKSUM_LEN:
        raise AddressError(f"Base58Check address has bad length {redact(addr)!r}")
    payload, checksum = raw[:-_CHECKSUM_LEN], raw[-_CHECKSUM_LEN:]
    if sha256d(payload)[:_CHECKSUM_LEN] != checksum:
        raise AddressError(f"Base58Check address has bad checksum {redact(addr)!r}")
    return payload
