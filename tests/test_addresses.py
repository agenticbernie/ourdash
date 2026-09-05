"""Phase 2: offline address validation (network + kind + wrong-network).

Fully-Automated, no node, no network.

Fixed vectors below were constructed with this implementation and
cross-checked against an independent reference — the third-party
``base58==2.1.1`` package plus a direct ``hashlib`` double-SHA-256 checksum
(``src/ourdash/utils/`` uses its own manual Base58, so no code is shared
with the reference) — and against the first-letter rules in Dash Core
v23.1.8 ``src/chainparams.cpp`` comments (mainnet P2PKH ``'X'``, testnet
P2PKH ``'y'``, mainnet P2SH ``'7'``, testnet P2SH ``'8'``/``'9'``).
"""

from __future__ import annotations

import hashlib

import base58
import pytest

from ourdash.core.addresses import (
    MAINNET_P2PKH_VERSION,
    MAINNET_P2SH_VERSION,
    TESTNET_P2PKH_VERSION,
    TESTNET_P2SH_VERSION,
    AddressInfo,
    derive_p2pkh,
    validate_address,
)
from ourdash.errors import AddressError
from ourdash.utils import b58check_decode, b58check_encode, sha256d

# Independently cross-checked fixed vectors (reference: base58==2.1.1 +
# hashlib sha256d; first letters per Dash Core v23.1.8 chainparams.cpp).
MAINNET_P2PKH_SEQ = "Xags3HEXJ4G4Uuf8va2eSxLCw2KCyEhiJ7"  # hash bytes(range(20))
TESTNET_P2PKH_SEQ = "yLKU4EJxjbv8peagVRM3UykZDJoaUUrXSn"  # hash bytes(range(20))
MAINNET_P2SH_SEQ = "7SQfxmMEhETVQuHwTQ3XMS11AkrcJwJS18"  # script hash bytes(range(20))
TESTNET_P2SH_SEQ = "8eRUv6F6pmr7sCiCXf3UoopN4GdSSt6SgR"  # script hash bytes(range(20))

_HASHES = {
    "zeros": bytes(20),
    "ones": bytes([1]) * 20,
    "seq": bytes(range(20)),
    "ff": bytes([0xFF]) * 20,
}
_P2PKH_VERSION = {"mainnet": 0x4C, "testnet": 0x8C, "regtest": 0x8C, "devnet": 0x8C}
_P2SH_VERSION = {"mainnet": 0x10, "testnet": 0x13, "regtest": 0x13, "devnet": 0x13}


def _reference_b58check(payload: bytes) -> str:
    """Independent Base58Check encoder (base58 package + hashlib)."""
    digest = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58.b58encode(payload + digest).decode("ascii")


def test_version_byte_constants_match_chainparams() -> None:
    """Dash Core v23.1.8 chainparams.cpp base58Prefixes values.

    mainnet: PUBKEY_ADDRESS 76 (0x4c), SCRIPT_ADDRESS 16 (0x10);
    testnet (reused by regtest/devnet): PUBKEY_ADDRESS 140 (0x8c),
    SCRIPT_ADDRESS 19 (0x13).
    """
    assert MAINNET_P2PKH_VERSION == 0x4C == 76
    assert MAINNET_P2SH_VERSION == 0x10 == 16
    assert TESTNET_P2PKH_VERSION == 0x8C == 140
    assert TESTNET_P2SH_VERSION == 0x13 == 19


def test_fixed_vectors_validate_with_network_and_kind() -> None:
    assert validate_address(MAINNET_P2PKH_SEQ) == AddressInfo(
        valid=True, network="mainnet", kind="p2pkh", reason="ok"
    )
    assert validate_address(TESTNET_P2PKH_SEQ) == AddressInfo(
        valid=True, network="testnet", kind="p2pkh", reason="ok"
    )
    assert validate_address(MAINNET_P2SH_SEQ) == AddressInfo(
        valid=True, network="mainnet", kind="p2sh", reason="ok"
    )
    assert validate_address(TESTNET_P2SH_SEQ) == AddressInfo(
        valid=True, network="testnet", kind="p2sh", reason="ok"
    )


def test_fixed_vectors_match_independent_reference() -> None:
    seq = bytes(range(20))
    assert MAINNET_P2PKH_SEQ == _reference_b58check(bytes([0x4C]) + seq)
    assert TESTNET_P2PKH_SEQ == _reference_b58check(bytes([0x8C]) + seq)
    assert MAINNET_P2SH_SEQ == _reference_b58check(bytes([0x10]) + seq)
    assert TESTNET_P2SH_SEQ == _reference_b58check(bytes([0x13]) + seq)


def test_round_trip_every_network_x_kind_cell() -> None:
    for name, digest in _HASHES.items():
        for network, version in _P2PKH_VERSION.items():
            addr = derive_p2pkh(digest, network)
            assert addr == _reference_b58check(bytes([version]) + digest), (name, network)
            info = validate_address(addr)
            assert info.valid and info.kind == "p2pkh", (name, network, addr)
            assert info.network == ("mainnet" if network == "mainnet" else "testnet")
        for network, version in _P2SH_VERSION.items():
            addr = b58check_encode(bytes([version]) + digest)
            assert addr == _reference_b58check(bytes([version]) + digest), (name, network)
            info = validate_address(addr)
            assert info.valid and info.kind == "p2sh", (name, network, addr)
            assert info.network == ("mainnet" if network == "mainnet" else "testnet")


def test_derive_p2pkh_matches_reference_for_all_networks() -> None:
    for network, version in _P2PKH_VERSION.items():
        assert derive_p2pkh(bytes(range(20)), network) == _reference_b58check(
            bytes([version]) + bytes(range(20))
        )


def test_tampered_checksum_rejected() -> None:
    last = MAINNET_P2PKH_SEQ[-1]
    tampered = MAINNET_P2PKH_SEQ[:-1] + ("1" if last != "1" else "2")
    info = validate_address(tampered)
    assert info == AddressInfo(valid=False, network=None, kind=None, reason="bad_checksum")


def test_bad_charset_rejected() -> None:
    bad_inputs = (
        "0agqqFetxiDb9wbartKDrXgnqLah6SqX2S",
        "XagqqFetxiDb9wbartKDrXgnqLah6SqX2O",
        "not an address!",
    )
    for bad in bad_inputs:
        info = validate_address(bad)
        assert info.valid is False and info.reason == "bad_charset", bad


def test_short_and_long_rejected_with_bad_length() -> None:
    assert validate_address("Xa").reason == "bad_length"
    long_payload = b58check_encode(bytes([0x4C]) + bytes(21))  # 22-byte payload, valid checksum
    assert validate_address(long_payload) == AddressInfo(
        valid=False, network=None, kind=None, reason="bad_length"
    )


def test_unknown_prefix_rejected() -> None:
    bitcoin_prefixed = b58check_encode(bytes([0x00]) + bytes(range(20)))
    assert validate_address(bitcoin_prefixed) == AddressInfo(
        valid=False, network=None, kind=None, reason="unknown_prefix"
    )


def test_wrong_network_matrix_both_directions() -> None:
    # Mainnet address presented for testnet-family use.
    for expected in ("testnet", "regtest", "devnet"):
        info = validate_address(MAINNET_P2PKH_SEQ, expected_network=expected)
        assert info.valid is False and info.reason == "wrong_network", expected
        info = validate_address(MAINNET_P2SH_SEQ, expected_network=expected)
        assert info.valid is False and info.reason == "wrong_network", expected
    # Testnet-family address presented for mainnet use.
    for addr in (TESTNET_P2PKH_SEQ, TESTNET_P2SH_SEQ):
        info = validate_address(addr, expected_network="mainnet")
        assert info == AddressInfo(
            valid=False, network="testnet", kind=info.kind, reason="wrong_network"
        )


def test_expected_network_disambiguates_testnet_family() -> None:
    assert validate_address(TESTNET_P2PKH_SEQ).network == "testnet"
    assert validate_address(TESTNET_P2PKH_SEQ, expected_network="testnet").network == "testnet"
    assert validate_address(TESTNET_P2PKH_SEQ, expected_network="regtest") == AddressInfo(
        valid=True, network="regtest", kind="p2pkh", reason="ok"
    )
    assert validate_address(TESTNET_P2PKH_SEQ, expected_network="devnet").network == "devnet"
    assert validate_address(MAINNET_P2PKH_SEQ, expected_network="mainnet").network == "mainnet"


def test_non_string_and_empty_input_raise() -> None:
    for bad in (None, b"Xags3HEXJ4G4Uuf8va2eSxLCw2KCyEhiJ7", 12345, ["X"], ""):
        with pytest.raises(AddressError):
            validate_address(bad)  # type: ignore[arg-type]
    with pytest.raises(AddressError):
        validate_address(MAINNET_P2PKH_SEQ, expected_network="fakenet")
    with pytest.raises(AddressError):
        derive_p2pkh(b"too short", "mainnet")
    with pytest.raises(AddressError):
        derive_p2pkh(bytes(20), "fakenet")


def test_utils_sha256d_and_b58check_round_trip() -> None:
    assert sha256d(b"dash") == hashlib.sha256(hashlib.sha256(b"dash").digest()).digest()
    payload = bytes([0x4C]) + bytes(range(20))
    assert b58check_decode(b58check_encode(payload)) == payload
    with pytest.raises(AddressError):
        b58check_decode("0badcharset")
    with pytest.raises(AddressError):
        b58check_decode("Xa")
    with pytest.raises(AddressError):
        b58check_decode(MAINNET_P2PKH_SEQ[:-1] + ("1" if MAINNET_P2PKH_SEQ[-1] != "1" else "2"))
