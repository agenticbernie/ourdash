"""Phase 3: offline HD wallet (BIP39 restore → BIP32/44 P2PKH derive).

Fully-Automated, no node, no network — plus one Hybrid regtest cross-check
(validates our derived address with the node's own ``validateaddress``).

Published vectors:
- BIP39/BIP32 vector 1: phrase ``abandon`` x11 + ``about``, passphrase
  ``TREZOR`` → seed + master ``xprv`` from the official
  ``trezor/python-mnemonic`` ``vectors.json`` (retrieved 2026-09-05).
- Dash BIP44 vectors: "zoomonic" (``zoo`` x11 + ``wrong`` / ``TREZOR``) and
  "catmonic" (``cat swing flag ... train`` / empty secret) first-address
  fixtures from the independent ``dashhd`` JS implementation
  (``dashhive/dashhd-cli.js`` ``FIXTURES.md``, retrieved 2026-09-05).
"""

from __future__ import annotations

import hashlib
import hmac
import warnings
from pathlib import Path

import pytest
from ecdsa import SECP256k1, SigningKey
from mnemonic import Mnemonic

from ourdash.core.addresses import validate_address
from ourdash.core.wallet import CUSTODY_WARNING, from_mnemonic
from ourdash.errors import WalletError
from ourdash.utils import b58check_decode, b58check_encode

ABANDON_PHRASE = (
    "abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon about"
)
TREZOR_PASSPHRASE = "TREZOR"
# Official trezor/python-mnemonic vectors.json, english vector 1 (entropy 128x0).
OFFICIAL_SEED_HEX = (
    "c55257c360c07c72029aebc1b53c05ed0362ada38ead3e3e9efa3708e53495531f09a6"
    "987599d18264c1e1c92f2cf141630c7a3c4ab7c81b2f001698e7463b04"
)
OFFICIAL_MASTER_XPRV = (
    "xprv9s21ZrQH143K3h3fDYiay8mocZ3afhfULfb5GX8kCBdno77K4HiA15Tg23wpbeF1pLfs1c5S"
    "PmYHrEpTuuRhxMwvKDwqdKiGJS9XFKzUsAF"
)
# Independent dashhd (JS) Dash BIP44 fixtures, m/44'/5'/0'/0/{index}.
ZOOMONIC_PHRASE = "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong"
ZOOMONIC_ADDR0 = "XrZJJfEKRNobcuwWKTD3bDu8ou7XSWPbc9"
ZOOMONIC_ADDR1 = "Xi1KPmjEEoKcg946H9bamEHjBXsdZ56Waf"
CATMONIC_PHRASE = "cat swing flag economy stadium alone churn speed unique patch report train"
CATMONIC_ADDR0 = "XyqBhjoHFToC9nCk15t6eZ5L3TiARZW5Wm"
# Implementation-pinned: abandon+TREZOR at m/44'/5'/0'/0/0 (cross-validated by
# the master-xprv check plus the two dashhd vectors above).
ABANDON_TREZOR_ADDR0 = "Xn9KtWHuvMBuSbpzPFTzYG2bC9Wp2ZZJJG"

SENTINEL_PASSPHRASE = "sentinel-pass-9f27c1"


def test_bip39_vector_restores_official_seed() -> None:
    wallet = from_mnemonic(ABANDON_PHRASE, passphrase=TREZOR_PASSPHRASE)
    assert wallet._seed.hex() == OFFICIAL_SEED_HEX
    assert len(wallet._seed) == 64


def test_bip32_master_key_matches_official_xprv() -> None:
    seed = Mnemonic("english").to_seed(ABANDON_PHRASE, passphrase=TREZOR_PASSPHRASE)
    master = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    payload = (
        bytes.fromhex("0488ade4")
        + b"\x00"
        + bytes(4)
        + bytes(4)
        + master[32:]
        + b"\x00"
        + master[:32]
    )
    assert b58check_encode(payload) == OFFICIAL_MASTER_XPRV


def test_first_address_matches_independent_dash_vectors() -> None:
    zoomonic = from_mnemonic(ZOOMONIC_PHRASE, passphrase=TREZOR_PASSPHRASE)
    assert zoomonic.receiving_address(0) == ZOOMONIC_ADDR0
    assert zoomonic.receiving_address(1) == ZOOMONIC_ADDR1
    catmonic = from_mnemonic(CATMONIC_PHRASE)
    assert catmonic.receiving_address(0) == CATMONIC_ADDR0
    vector = from_mnemonic(ABANDON_PHRASE, passphrase=TREZOR_PASSPHRASE)
    assert vector.receiving_address(0) == ABANDON_TREZOR_ADDR0


def test_derived_addresses_validate_for_their_network() -> None:
    wallet = from_mnemonic(ABANDON_PHRASE, passphrase=TREZOR_PASSPHRASE)
    info = validate_address(wallet.receiving_address(0), expected_network="mainnet")
    assert info.valid and info.network == "mainnet" and info.kind == "p2pkh"
    regtest_wallet = from_mnemonic(ABANDON_PHRASE, network="regtest")
    regtest_addr = regtest_wallet.receiving_address(0)
    assert regtest_addr.startswith("y")
    info = validate_address(regtest_addr, expected_network="regtest")
    assert info.valid and info.network == "regtest" and info.kind == "p2pkh"
    # testnet/regtest/devnet share prefixes, so the same key renders identically.
    assert regtest_addr == from_mnemonic(ABANDON_PHRASE, network="testnet").receiving_address(0)
    assert wallet.derivation_path(0) == "m/44'/5'/0'/0/0"
    assert wallet.derivation_path(7) == "m/44'/5'/0'/0/7"


def test_bad_checksum_phrase_raises_without_echo() -> None:
    bad_checksum = ABANDON_PHRASE.rsplit(" ", 1)[0] + " abandon"  # valid words, bad checksum
    for bad in (bad_checksum, "not a real recovery phrase at all", "", "   ", None, 123):
        with pytest.raises(WalletError) as exc_info:
            from_mnemonic(bad)  # type: ignore[arg-type]
        assert ABANDON_PHRASE not in str(exc_info.value)
    with pytest.raises(WalletError):
        from_mnemonic(ABANDON_PHRASE, network="fakenet")


def test_unknown_network_rejected() -> None:
    with pytest.raises(WalletError):
        from_mnemonic(ABANDON_PHRASE, network="bitcoin")


def test_watch_only_default() -> None:
    assert from_mnemonic(ABANDON_PHRASE).watch_only is True


def test_private_key_requires_explicit_opt_in() -> None:
    wallet = from_mnemonic(ABANDON_PHRASE)
    with pytest.raises(WalletError):
        wallet.private_key_bytes(0)
    with pytest.raises(WalletError):
        wallet.private_key_bytes(0, allow_sign=False)
    with pytest.raises(WalletError):  # truthy-but-not-True is not explicit enough
        wallet.private_key_bytes(0, allow_sign=1)  # type: ignore[arg-type]


def test_private_key_opt_in_warns_with_custody_wording() -> None:
    wallet = from_mnemonic(ABANDON_PHRASE)
    with pytest.warns(UserWarning, match="watch-only") as record:
        key = wallet.private_key_bytes(0, allow_sign=True)
    assert len(key) == 32
    assert "review" in str(record[0].message)
    assert "not your keys flow" in CUSTODY_WARNING


def test_pubkey_matches_privkey_and_address() -> None:
    wallet = from_mnemonic(ABANDON_PHRASE)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        priv = wallet.private_key_bytes(3, allow_sign=True)
    pub = wallet.public_key_bytes(3)
    expected = SigningKey.from_secret_exponent(
        int.from_bytes(priv, "big"), curve=SECP256k1
    ).verifying_key.to_string()
    assert pub == (b"\x02" if expected[63] % 2 == 0 else b"\x03") + expected[:32]
    assert wallet.receiving_address(3) != wallet.receiving_address(4)


def test_receiving_index_bounds() -> None:
    wallet = from_mnemonic(ABANDON_PHRASE)
    for bad in (-1, 0x80000000, 2**32, True):
        with pytest.raises(WalletError):
            wallet.receiving_address(bad)  # type: ignore[arg-type]
        with pytest.raises(WalletError):
            wallet.public_key_bytes(bad)  # type: ignore[arg-type]


def test_repr_and_str_never_leak_secrets() -> None:
    wallet = from_mnemonic(ABANDON_PHRASE, passphrase=SENTINEL_PASSPHRASE)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        priv_hex = wallet.private_key_bytes(0, allow_sign=True).hex()
    rendered = repr(wallet) + str(wallet)
    assert ABANDON_PHRASE not in rendered
    assert SENTINEL_PASSPHRASE not in rendered
    assert priv_hex not in rendered
    assert wallet._seed.hex() not in rendered
    assert "watch_only=True" in rendered


def test_sentinel_secrets_absent_from_captured_outputs(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    with caplog.at_level("DEBUG", logger="ourdash.core.wallet"):
        wallet = from_mnemonic(ABANDON_PHRASE, passphrase=SENTINEL_PASSPHRASE)
        wallet.receiving_address(0)
        try:
            wallet.private_key_bytes(0)
        except WalletError as exc:
            refusal = str(exc)
    _ = capsys.readouterr()
    probe = tmp_path / "captured.txt"
    probe.write_text(repr(wallet) + refusal + wallet.account_fingerprint, encoding="utf-8")
    captured = caplog.text + capsys.readouterr().out + probe.read_text(encoding="utf-8")
    assert ABANDON_PHRASE not in captured
    assert SENTINEL_PASSPHRASE not in captured
    assert wallet._seed.hex() not in captured


def test_module_documents_allow_sign_opt_in() -> None:
    import ourdash.core.wallet as wallet_module

    assert "allow_sign" in (wallet_module.__doc__ or "")
    assert "watch_only" in (wallet_module.__doc__ or "").lower()


def test_address_payload_is_21_bytes() -> None:
    wallet = from_mnemonic(ABANDON_PHRASE)
    assert len(b58check_decode(wallet.receiving_address(0))) == 21


@pytest.mark.hybrid
def test_regtest_address_accepted_by_node(dashd_regtest: object) -> None:
    assert isinstance(dashd_regtest, dict)
    rpc = dashd_regtest["rpc"]
    wallet = from_mnemonic(ZOOMONIC_PHRASE, passphrase=TREZOR_PASSPHRASE, network="regtest")
    addr = wallet.receiving_address(0)
    assert validate_address(addr, expected_network="regtest").valid
    node = rpc.call("validateaddress", addr)
    assert node["isvalid"] is True
    assert node["scriptPubKey"] == "76a914" + b58check_decode(addr)[1:].hex() + "88ac"
