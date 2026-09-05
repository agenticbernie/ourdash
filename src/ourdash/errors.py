"""Typed error taxonomy for the ourdash SDK.

Every public exception subclasses :class:`OurdashError`. Transport, config,
address, wallet, payment, DAPI, and proof failures each get a distinct type so
callers branch on types instead of parsing messages.

``__str__`` on every class routes through :func:`ourdash.redact.redact`, and
error objects store only ``code``/``message``-style safe fields — never
credentials, recovery phrases, or key material.
"""

from __future__ import annotations

from ourdash.redact import redact


class OurdashError(Exception):
    """Base class for every ourdash failure."""

    def __str__(self) -> str:
        return str(redact(super().__str__()))


class RpcError(OurdashError):
    """Dash Core JSON-RPC failure (node error object or HTTP error page)."""

    def __init__(self, message: str = "", code: int | None = None) -> None:
        self.code = code
        self.message = message
        if code is not None:
            super().__init__(f"RPC error {code}: {message}")
        else:
            super().__init__(f"RPC error: {message}")


class RpcAuthError(RpcError):
    """Wrong or missing RPC credentials (HTTP 401/403). Never retried."""


class RpcConnectionError(RpcError):
    """Node unreachable or connection dropped (retried, then raised)."""


class RpcTimeoutError(RpcError):
    """Node did not answer within ``timeout_s``. Never retried."""


class ConfigError(OurdashError):
    """Unsafe or incomplete client configuration.

    Covers remote-host refusal without explicit opt-in, missing credentials,
    and bad wallet-selection input.
    """


class AddressError(OurdashError):
    """Address validation failure (first raised in Phase 2)."""


class WalletError(OurdashError):
    """Wallet restore/derivation failure (first raised in Phase 3)."""


class PaymentError(OurdashError):
    """Unsigned/malformed submit refusal (first raised in Phase 3)."""


class DAPIError(OurdashError):
    """Dash Platform DAPI transport failure (first raised in Phase 5)."""


class ProofError(OurdashError):
    """Proof verification failure (first raised in Phase 5)."""


class ProofUnavailableError(ProofError):
    """Proof material unavailable for the requested read (first raised in Phase 5)."""
