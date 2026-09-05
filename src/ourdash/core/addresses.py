"""Dash address validation (Dash crypto from dash.org — not Plotly Dash).

Pure-offline Base58Check validation reporting validity, network, and kind
before any funds move. Version bytes are fixed per Dash Core v23.1.8
``src/chainparams.cpp`` ``base58Prefixes[PUBKEY_ADDRESS]`` /
``[SCRIPT_ADDRESS]``: mainnet P2PKH ``0x4c`` (76, addresses start with
``'X'``), mainnet P2SH ``0x10`` (16, start with ``'7'``), testnet P2PKH
``0x8c`` (140, start with ``'y'``), testnet P2SH ``0x13`` (19, start with
``'8'``/``'9'``). Regtest and devnet reuse the testnet prefixes.

Only P2PKH/P2SH Base58Check is handled here (v0.1 scope). Checksum rule:
4-byte double-SHA-256 checksum over a 21-byte payload (1 version byte +
20-byte hash).
"""

from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel

from ourdash.errors import AddressError
from ourdash.redact import redact
from ourdash.utils import b58check_decode, b58check_encode

Network = Literal["mainnet", "testnet", "regtest", "devnet"]
AddressKind = Literal["p2pkh", "p2sh"]
AddressReason = Literal[
    "ok", "bad_charset", "bad_length", "bad_checksum", "wrong_network", "unknown_prefix"
]

_NETWORKS: tuple[str, ...] = ("mainnet", "testnet", "regtest", "devnet")

# Version byte -> (family, kind). regtest/devnet reuse the testnet prefixes.
_VERSION_TABLE: dict[int, tuple[str, AddressKind]] = {
    0x4C: ("mainnet", "p2pkh"),
    0x10: ("mainnet", "p2sh"),
    0x8C: ("testnet", "p2pkh"),
    0x13: ("testnet", "p2sh"),
}

# Network -> P2PKH version byte (single source of version-byte truth).
_P2PKH_VERSION: dict[str, int] = {
    "mainnet": 0x4C,
    "testnet": 0x8C,
    "regtest": 0x8C,
    "devnet": 0x8C,
}

MAINNET_P2PKH_VERSION = 0x4C
MAINNET_P2SH_VERSION = 0x10
TESTNET_P2PKH_VERSION = 0x8C
TESTNET_P2SH_VERSION = 0x13

_PAYLOAD_LEN = 21  # 1 version byte + 20-byte hash


class AddressInfo(BaseModel):
    """Validation verdict for one Dash address input."""

    valid: bool
    network: Network | None = None
    kind: AddressKind | None = None
    reason: AddressReason = "ok"


def _family_of(network: str) -> str:
    """Map a network to its prefix family (``mainnet`` vs ``testnet``)."""
    if network == "mainnet":
        return "mainnet"
    return "testnet"  # testnet, regtest, devnet share prefixes


def validate_address(addr: str, expected_network: str | None = None) -> AddressInfo:
    """Validate a Dash address, reporting network and kind.

    Without ``expected_network``, a testnet-family prefix reports the
    ``testnet`` family label. With ``expected_network="regtest"`` (or
    ``"devnet"``), the prefix is validated against that network and the
    specific network is reported. A prefix from the other family returns
    ``valid=False, reason="wrong_network"`` — never raised.

    Raises :class:`ourdash.errors.AddressError` only for non-string or
    empty input (and for an unknown ``expected_network`` value).
    """
    if not isinstance(addr, str) or not addr:
        raise AddressError(f"invalid address input {redact(addr)!r}")
    if expected_network is not None and expected_network not in _NETWORKS:
        raise AddressError(f"unknown network {redact(expected_network)!r}")

    try:
        payload = b58check_decode(addr)
    except AddressError as exc:
        message = str(exc)
        if "bad charset" in message:
            return AddressInfo(valid=False, reason="bad_charset")
        if "bad length" in message:
            return AddressInfo(valid=False, reason="bad_length")
        return AddressInfo(valid=False, reason="bad_checksum")
    if len(payload) != _PAYLOAD_LEN:
        return AddressInfo(valid=False, reason="bad_length")

    entry = _VERSION_TABLE.get(payload[0])
    if entry is None:
        return AddressInfo(valid=False, reason="unknown_prefix")
    family, kind = entry

    if expected_network is None:
        return AddressInfo(valid=True, network=cast(Network, family), kind=kind)
    if _family_of(expected_network) != family:
        return AddressInfo(
            valid=False,
            network=cast(Network, family),
            kind=kind,
            reason="wrong_network",
        )
    return AddressInfo(valid=True, network=cast(Network, expected_network), kind=kind)


def derive_p2pkh(pubkey_hash20: bytes, network: str = "mainnet") -> str:
    """Build the P2PKH address for a 20-byte hash on ``network``."""
    if not isinstance(pubkey_hash20, bytes) or len(pubkey_hash20) != 20:
        raise AddressError("pubkey hash must be exactly 20 bytes")
    if network not in _P2PKH_VERSION:
        raise AddressError(f"unknown network {redact(network)!r}")
    return b58check_encode(bytes([_P2PKH_VERSION[network]]) + pubkey_hash20)
