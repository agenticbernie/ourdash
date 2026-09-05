"""Dash Core JSON-RPC transport (parity pin: Dash Core v23.1.8).

Default RPC ports: mainnet 9998 / testnet 19998 / regtest 19898 / devnet 19788.
Upstream refs: the docs.dash.org Core RPC family, with ``dash-cli help`` as the
method allowlist oracle.

Transport-only module: stdlib + ``dataclasses`` + ``requests``. No validation
or modelling libraries are imported here (seam rule, enforced by
``tests/test_seam.py``).
"""

from __future__ import annotations

import itertools
import logging
import os
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from ourdash.errors import ConfigError, RpcAuthError, RpcConnectionError, RpcError, RpcTimeoutError
from ourdash.redact import RedactionFilter, redact

logger = logging.getLogger(__name__)
logger.addFilter(RedactionFilter())

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_S = 0.05
_BACKOFF_MAX_S = 1.0
_WARMING_UP_CODE = -28  # node still starting; the one node error worth retrying


@dataclass(frozen=True, repr=False)
class DashRPCConfig:
    """Connection config for dashd JSON-RPC."""

    host: str = "127.0.0.1"
    port: int = 9998  # mainnet RPC; testnet 19998, regtest 19898, devnet 19788
    user: str = ""
    password: str = ""
    timeout_s: float = 30.0
    wallet: str | None = None
    cookie_path: str | None = None
    remote_ok: bool = False

    @classmethod
    def from_env(cls) -> DashRPCConfig:
        """Build config from the ``OURDASH_RPC_*`` env names only.

        ``OURDASH_RPC_URL`` overrides host+port; ``OURDASH_RPC_USER``,
        ``OURDASH_RPC_PASSWORD``, and ``OURDASH_RPC_WALLET`` fill the rest.
        No other env names are read.
        """
        host = "127.0.0.1"
        port = 9998
        url = os.environ.get("OURDASH_RPC_URL", "")
        if url:
            parsed = urlparse(url if "://" in url else f"http://{url}")
            if parsed.hostname:
                host = parsed.hostname
            if parsed.port is not None:
                port = parsed.port
        return cls(
            host=host,
            port=port,
            user=os.environ.get("OURDASH_RPC_USER", ""),
            password=os.environ.get("OURDASH_RPC_PASSWORD", ""),
            wallet=os.environ.get("OURDASH_RPC_WALLET"),
        )

    def __repr__(self) -> str:
        safe = redact(
            {
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "password": self.password,
                "timeout_s": self.timeout_s,
                "wallet": self.wallet,
                "cookie_path": self.cookie_path,
                "remote_ok": self.remote_ok,
            }
        )
        return f"DashRPCConfig({safe})"

    def __str__(self) -> str:
        return repr(self)


class DashRPC:
    """Thin requests-based JSON-RPC 1.0 client for Dash Core."""

    def __init__(self, config: DashRPCConfig | None = None) -> None:
        self.config = config or DashRPCConfig()
        if self.config.host not in _LOOPBACK_HOSTS and not self.config.remote_ok:
            raise ConfigError(
                f"refusing non-loopback RPC host {self.config.host!r}; "
                "pass remote_ok=True to opt in explicitly"
            )
        if self.config.wallet is not None and (
            not self.config.wallet or "/" in self.config.wallet or ".." in self.config.wallet
        ):
            raise ConfigError(f"invalid wallet selection {self.config.wallet!r}")
        self._ids: Iterator[int] = itertools.count(1)

    @property
    def _url(self) -> str:
        host = self.config.host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        base = f"http://{host}:{self.config.port}"
        if self.config.wallet:
            return f"{base}/wallet/{self.config.wallet}"
        return base + "/"

    def _auth(self) -> tuple[str, str] | None:
        if self.config.user:
            return (self.config.user, self.config.password)
        if self.config.cookie_path is None:
            return None
        try:
            content = Path(self.config.cookie_path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ConfigError(f"cannot read RPC cookie file {self.config.cookie_path!r}") from exc
        name, sep, secret = content.partition(":")
        if not sep or not name.strip() or not secret.strip():
            raise ConfigError(f"malformed RPC cookie file {self.config.cookie_path!r}")
        return (name.strip(), secret.strip())

    def _require_auth(self) -> tuple[str, str]:
        auth = self._auth()
        if auth is None:
            raise ConfigError("missing RPC credentials: set user/password or cookie_path")
        return auth

    @staticmethod
    def _backoff(attempt: int) -> None:
        time.sleep(min(_BACKOFF_BASE_S * (2**attempt), _BACKOFF_MAX_S))

    def _post(self, payload: Any, auth: tuple[str, str]) -> Any:
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = requests.post(
                    self._url,
                    json=payload,
                    auth=auth,
                    timeout=self.config.timeout_s,
                    headers={"Content-Type": "text/plain"},
                )
            except requests.Timeout as exc:
                raise RpcTimeoutError(f"RPC call timed out after {self.config.timeout_s}s") from exc
            except requests.ConnectionError as exc:
                if attempt < _MAX_ATTEMPTS - 1:
                    self._backoff(attempt)
                    continue
                raise RpcConnectionError("RPC call could not reach the node") from exc
            except requests.RequestException as exc:
                raise RpcConnectionError(f"RPC call failed: {redact(str(exc))}") from exc
            if response.status_code in (401, 403):
                raise RpcAuthError(
                    f"RPC call rejected: bad credentials (HTTP {response.status_code})"
                )
            try:
                return response.json()
            except ValueError as exc:
                raise RpcError(
                    f"RPC call returned non-JSON body (HTTP {response.status_code})"
                ) from exc
        raise RpcError("RPC call exhausted retries")

    @staticmethod
    def _result_or_raise(body: Any, method: str) -> Any:
        if isinstance(body, dict) and body.get("error"):
            error = body["error"]
            if isinstance(error, dict):
                code = error.get("code")
                raise RpcError(
                    str(error.get("message", "")),
                    code if isinstance(code, int) else None,
                )
            raise RpcError(str(error))
        if isinstance(body, dict) and "result" in body:
            return body["result"]
        raise RpcError(f"RPC call {method!r} returned a malformed response")

    def call(self, method: str, *params: Any) -> Any:
        """Send one JSON-RPC 1.0 request; return ``result`` or raise typed error."""
        auth = self._require_auth()
        logger.debug("RPC call %s", method)
        payload: dict[str, Any] = {
            "jsonrpc": "1.0",
            "id": str(next(self._ids)),
            "method": method,
            "params": list(params),
        }
        for attempt in range(_MAX_ATTEMPTS):
            body = self._post(payload, auth)
            error = body.get("error") if isinstance(body, dict) else None
            if (
                isinstance(error, dict)
                and error.get("code") == _WARMING_UP_CODE
                and attempt < _MAX_ATTEMPTS - 1
            ):
                self._backoff(attempt)
                continue
            return self._result_or_raise(body, method)
        raise RpcError("RPC call exhausted retries")

    def batch(self, calls: Sequence[tuple[str, Sequence[Any]]]) -> list[Any]:
        """Send one array-framed batch; return results in call order.

        Raises the matching typed error for the first per-call node error.
        """
        auth = self._require_auth()
        if not calls:
            return []
        logger.debug("RPC batch of %d calls", len(calls))
        payload = [
            {"jsonrpc": "1.0", "id": str(index + 1), "method": name, "params": list(args)}
            for index, (name, args) in enumerate(calls)
        ]
        body = self._post(payload, auth)
        if not isinstance(body, list) or len(body) != len(payload):
            raise RpcError("RPC batch call returned a malformed response")
        by_id = {str(entry.get("id")): entry for entry in body if isinstance(entry, dict)}
        results: list[Any] = []
        pending_error: dict[str, Any] | None = None
        for request in payload:
            entry = by_id.get(str(request["id"]))
            if not isinstance(entry, dict):
                raise RpcError("RPC batch call returned a malformed response")
            error = entry.get("error")
            if error:
                if pending_error is None:
                    pending_error = (
                        error if isinstance(error, dict) else {"code": None, "message": str(error)}
                    )
                results.append(None)
            else:
                results.append(entry.get("result"))
        if pending_error is not None:
            code = pending_error.get("code")
            raise RpcError(
                str(pending_error.get("message", "")),
                code if isinstance(code, int) else None,
            )
        return results
