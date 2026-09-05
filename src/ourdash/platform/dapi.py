"""DAPI client: seed-discovered HTTP/JSON transport for Dash Core (L1) reads.

Dash here is Dash crypto from dash.org — not Plotly Dash.

Endpoint discovery is per network via :mod:`ourdash.platform.seeds` — no
default URL ships (the old placeholder default was deleted, not
deprecated). ``DAPIClient.from_network("testnet")`` dials the first
documented seed; ``DAPIClient(DAPIConfig(address=...))`` stays available for
an explicit user choice and always verifies TLS on ``https`` endpoints.

v0.1 speaks the HTTP/JSON surface ONLY, which upstream DAPI limits to two
commands (verified against ``dashpay/platform`` master
``packages/dapi/lib/rpcServer/commands/`` on 2026-09-05, and live against
testnet the same day):

- ``getBestBlockHash`` (no params) → :meth:`get_best_block_hash`
- ``getBlockHash`` (``{"height": n}``) → :meth:`get_block_hash`

Consequences, stated plainly so nothing silently degrades:

- :meth:`get_status` composes the two verified reads into a status snapshot
  (there is no dedicated JSON-RPC status command upstream).
- :meth:`broadcast_transaction` raises :class:`~ourdash.errors.DAPIError`:
  submit is gRPC-only upstream (see the pinned toolkit's ``CoreMethodsFacade``,
  which routes broadcast through ``GrpcTransport``) and the gRPC transport is
  deferred — the same loud-refusal pattern the SDK uses for P2PKH-only
  signing and verbosity-0 block reads.
- gRPC streaming helpers are deferred (streaming needs the optional
  ``grpcio`` channel surface pinned later).

Transport-only module: stdlib + ``dataclasses`` + ``requests``. No validation
or modelling libraries are imported here (seam rule, enforced by
``tests/test_seam.py``).
"""

from __future__ import annotations

import itertools
import logging
import os
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests

from ourdash.errors import (
    DAPIError,
    RpcAuthError,
    RpcConnectionError,
    RpcTimeoutError,
)
from ourdash.platform.seeds import seeds_for
from ourdash.redact import RedactionFilter, redact

logger = logging.getLogger(__name__)
logger.addFilter(RedactionFilter())

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_S = 0.05
_BACKOFF_MAX_S = 1.0


@dataclass(frozen=True, repr=False)
class DAPIConfig:
    """DAPI connection config.

    ``address`` defaults to ``None``: construct via
    :meth:`DAPIClient.from_network` for seed discovery, or pass an explicit
    address (your own choice — TLS is always verified on ``https``).
    """

    address: str | None = None
    timeout_s: float = 30.0

    @classmethod
    def from_env(cls) -> DAPIConfig:
        """Build config from the ``OURDASH_DAPI_*`` env names only.

        ``OURDASH_DAPI_ADDRESS`` sets the endpoint; ``OURDASH_DAPI_TIMEOUT_S``
        sets the timeout (falling back to ``30.0`` when absent or invalid).
        No other env names are read.
        """
        address = os.environ.get("OURDASH_DAPI_ADDRESS") or None
        timeout_s = 30.0
        raw_timeout = os.environ.get("OURDASH_DAPI_TIMEOUT_S", "")
        if raw_timeout:
            try:
                timeout_s = float(raw_timeout)
            except ValueError:
                timeout_s = 30.0
        return cls(address=address, timeout_s=timeout_s)

    def __repr__(self) -> str:
        safe = redact({"address": self.address, "timeout_s": self.timeout_s})
        return f"DAPIConfig({safe})"

    def __str__(self) -> str:
        return repr(self)


class DAPIClient:
    """Thin requests-based DAPI HTTP/JSON client (L1 reads)."""

    def __init__(self, config: DAPIConfig | None = None) -> None:
        self.config = config or DAPIConfig()
        self._ids: Iterator[int] = itertools.count(1)

    @classmethod
    def from_network(cls, network: str, timeout_s: float = 30.0) -> DAPIClient:
        """Resolve the endpoint through :mod:`ourdash.platform.seeds`.

        Dials the FIRST documented seed for ``network``. Networks with no
        documented seed raise a guiding :class:`~ourdash.errors.DAPIError`
        (empty-list-with-reason over invented hostnames).
        """
        seeds = seeds_for(network)
        if not seeds:
            raise DAPIError(
                f"no DAPI seed is documented for network {network!r}; "
                "pass DAPIConfig(address=...) explicitly"
            )
        return cls(DAPIConfig(address=seeds[0].address, timeout_s=timeout_s))

    def _require_address(self) -> str:
        address = self.config.address
        if not address:
            raise DAPIError(
                "DAPI client has no address (no default ships); "
                "use DAPIClient.from_network(network) or pass "
                "DAPIConfig(address=...) explicitly"
            )
        parsed = urlparse(address if "://" in address else f"https://{address}")
        if parsed.scheme not in ("http", "https"):
            raise DAPIError(f"DAPI address must be http(s), got {address!r}")
        return address

    @staticmethod
    def _backoff(attempt: int) -> None:
        time.sleep(min(_BACKOFF_BASE_S * (2**attempt), _BACKOFF_MAX_S))

    def _post(self, payload: Mapping[str, Any]) -> Any:
        address = self._require_address()
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = requests.post(
                    address,
                    json=dict(payload),
                    timeout=self.config.timeout_s,
                    headers={"Content-Type": "application/json"},
                    verify=True,
                )
            except requests.Timeout as exc:
                raise RpcTimeoutError(
                    f"DAPI call timed out after {self.config.timeout_s}s"
                ) from exc
            except requests.ConnectionError as exc:
                if attempt < _MAX_ATTEMPTS - 1:
                    self._backoff(attempt)
                    continue
                raise RpcConnectionError("DAPI call could not reach the endpoint") from exc
            except requests.RequestException as exc:
                raise RpcConnectionError(f"DAPI call failed: {redact(str(exc))}") from exc
            if response.status_code in (401, 403):
                raise RpcAuthError(
                    "DAPI call rejected: bad credentials " f"(HTTP {response.status_code})"
                )
            try:
                return response.json()
            except ValueError as exc:
                raise DAPIError(
                    f"DAPI call returned non-JSON body (HTTP {response.status_code})"
                ) from exc
        raise DAPIError("DAPI call exhausted retries")

    def _call(self, method: str, params: Mapping[str, Any] | None = None) -> Any:
        logger.debug("DAPI call %s", method)
        body = self._post(
            {
                "method": method,
                "id": next(self._ids),
                "jsonrpc": "2.0",
                "params": dict(params) if params else {},
            }
        )
        if not isinstance(body, dict):
            raise DAPIError(f"DAPI call {method!r} returned a malformed response")
        error = body.get("error")
        if error:
            if isinstance(error, dict):
                raise DAPIError(str(error.get("message", error)))
            raise DAPIError(str(error))
        if "result" not in body:
            raise DAPIError(f"DAPI call {method!r} returned a malformed response")
        return body["result"]

    def get_best_block_hash(self) -> str:
        """Return the chaintip block hash (JSON-RPC ``getBestBlockHash``)."""
        result = self._call("getBestBlockHash")
        if not isinstance(result, str) or not result:
            raise DAPIError("getBestBlockHash returned a malformed response")
        return result

    def get_block_hash(self, height: int) -> str:
        """Return the block hash at ``height`` (JSON-RPC ``getBlockHash``)."""
        if isinstance(height, bool) or not isinstance(height, int) or height < 0:
            raise DAPIError("block height must be a non-negative int")
        result = self._call("getBlockHash", {"height": height})
        if not isinstance(result, str) or not result:
            raise DAPIError("getBlockHash returned a malformed response")
        return result

    def get_status(self) -> dict[str, Any]:
        """Return an L1 status snapshot composed from the verified reads.

        Upstream DAPI exposes no dedicated JSON-RPC status command, so v0.1
        reports ``{"best_block_hash": ...}`` from :meth:`get_best_block_hash`.
        """
        return {"best_block_hash": self.get_best_block_hash()}

    def broadcast_transaction(self, raw_hex: str) -> str:
        """Refuse: submit is gRPC-only upstream (deferred in v0.1).

        Raises :class:`~ourdash.errors.DAPIError` without touching the
        network — a loud refusal, never a silent downgrade. Validates the hex
        shape first so malformed input is reported as such.
        """
        if not isinstance(raw_hex, str) or not raw_hex:
            raise DAPIError("raw transaction must be a non-empty hex string")
        try:
            raw = bytes.fromhex(raw_hex)
        except ValueError:
            raise DAPIError("raw transaction must be a non-empty hex string") from None
        if not raw:
            raise DAPIError("raw transaction must be a non-empty hex string")
        raise DAPIError(
            "broadcast_transaction needs the gRPC transport (upstream DAPI serves "
            "submit over gRPC only; see @dashevo/dapi-client CoreMethodsFacade), "
            "which is deferred in v0.1 — no bytes were sent"
        )
