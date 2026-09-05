"""Smoke: package imports + version + stub clients construct."""

from ourdash import __version__
from ourdash.core.rpc import DashRPC
from ourdash.platform.dapi import DAPIClient


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_clients_construct() -> None:
    assert DashRPC().config.host == "127.0.0.1"
    assert DAPIClient().config.timeout_s == 30.0


def test_top_level_export_surface() -> None:
    """Phase 6: __all__ matches the exact curated export list, nothing more."""
    import ourdash

    assert ourdash.__all__ == [
        "__version__",
        "DashRPC",
        "DashRPCConfig",
        "DAPIClient",
        "DAPIConfig",
        "AddressInfo",
        "validate_address",
        "Wallet",
        "UnsignedTx",
        "SignedTx",
        "ConfirmationStatus",
        "ProofVerdict",
        "ProvenResult",
        "OurdashError",
        "RpcError",
        "RpcAuthError",
        "RpcConnectionError",
        "RpcTimeoutError",
        "ConfigError",
        "AddressError",
        "WalletError",
        "PaymentError",
        "DAPIError",
        "ProofError",
        "ProofUnavailableError",
    ]
    for name in ourdash.__all__:
        assert getattr(ourdash, name) is not None, f"missing export: {name}"
