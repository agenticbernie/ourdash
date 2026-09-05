"""Error taxonomy + redaction choke-point tests (no node, no network)."""

from __future__ import annotations

import logging

import pytest

from ourdash.errors import (
    AddressError,
    ConfigError,
    DAPIError,
    OurdashError,
    PaymentError,
    ProofError,
    ProofUnavailableError,
    RpcAuthError,
    RpcConnectionError,
    RpcError,
    RpcTimeoutError,
    WalletError,
)
from ourdash.redact import BANNED_KEYS, MASK, RedactionFilter, redact

ALL_ERRORS = [
    OurdashError,
    RpcError,
    RpcAuthError,
    RpcConnectionError,
    RpcTimeoutError,
    ConfigError,
    AddressError,
    WalletError,
    PaymentError,
    DAPIError,
    ProofError,
    ProofUnavailableError,
]


def test_banned_keys_minimum() -> None:
    for key in (
        "mnemonic",
        "seed",
        "xprv",
        "xpub",
        "privkey",
        "private_key",
        "password",
        "passphrase",
        "rpcpassword",
        "cookie",
        "auth",
    ):
        assert key in BANNED_KEYS


def test_hierarchy() -> None:
    assert issubclass(RpcAuthError, RpcError)
    assert issubclass(RpcConnectionError, RpcError)
    assert issubclass(RpcTimeoutError, RpcError)
    assert issubclass(RpcError, OurdashError)
    assert issubclass(ConfigError, OurdashError)
    assert issubclass(ProofUnavailableError, ProofError)
    assert issubclass(ProofError, OurdashError)
    assert issubclass(OurdashError, Exception)


@pytest.mark.parametrize("cls", ALL_ERRORS)
def test_raisable_and_catchable_through_parent(cls: type[OurdashError]) -> None:
    with pytest.raises(OurdashError):
        raise cls("boom")


@pytest.mark.parametrize("cls", [RpcAuthError, RpcConnectionError, RpcTimeoutError, RpcError])
def test_rpc_branch_catchable_as_rpc_error(cls: type[RpcError]) -> None:
    with pytest.raises(RpcError):
        raise cls("transport boom", -1)


def test_rpc_error_stores_code_and_message() -> None:
    err = RpcError("Block not found", -8)
    assert err.code == -8
    assert err.message == "Block not found"
    assert "-8" in str(err)


def test_rpc_error_code_defaults_to_none() -> None:
    assert RpcError("plain failure").code is None


def test_redact_nested_mappings_and_case_variants() -> None:
    payload = {
        "Mnemonic": "abandon abandon abandon",
        "config": {"RPCPASSWORD": "hunter2", "port": 9998},
        "items": [{"Seed": "deadbeef"}, "plain"],
        "user": "alice",
    }
    out = redact(payload)
    assert out["Mnemonic"] == MASK
    assert out["config"]["RPCPASSWORD"] == MASK
    assert out["config"]["port"] == 9998
    assert out["items"][0] == {"Seed": MASK}
    assert out["items"][1] == "plain"
    assert out["user"] == MASK


def test_redact_key_value_shapes_in_free_text() -> None:
    text = "login failed for rpcuser=admin password=hunter2 on host"
    out = redact(text)
    assert "hunter2" not in out
    assert "admin" not in out
    assert "password=" in out


def test_redact_leaves_safe_values_alone() -> None:
    assert redact({"host": "127.0.0.1", "port": 9998}) == {
        "host": "127.0.0.1",
        "port": 9998,
    }
    assert redact(42) == 42
    assert redact(None) is None


def test_str_of_errors_masks_secrets() -> None:
    err = RpcError("auth failed for user=admin password=hunter2", -1)
    assert "hunter2" not in str(err)
    assert "admin" not in str(err)
    assert err.code == -1


def test_logging_filter_redacts_record_args(caplog: pytest.LogCaptureFixture) -> None:
    test_logger = logging.getLogger("ourdash.test-redact")
    test_logger.addFilter(RedactionFilter())
    try:
        with caplog.at_level(logging.INFO, logger=test_logger.name):
            test_logger.info("connecting with %s", {"rpcpassword": "hunter2", "host": "127.0.0.1"})
    finally:
        test_logger.removeFilter(test_logger.filters[-1])
    assert "hunter2" not in caplog.text
    assert "127.0.0.1" in caplog.text
