"""DashRPC transport tests vs an in-process fake dashd (loopback only).

No ``dashd`` binary, no external network: every behavior is asserted against
request shapes the fake server records.
"""

from __future__ import annotations

import base64
import json
import logging
import socket
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from ourdash.core.rpc import DashRPC, DashRPCConfig
from ourdash.errors import (
    ConfigError,
    RpcAuthError,
    RpcConnectionError,
    RpcError,
    RpcTimeoutError,
)

Handler = Callable[[Any, Any, str], tuple[int, Any]]


class _State:
    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []
        self.handler: Handler = lambda payload, headers, path: (
            200,
            {"result": None, "error": None, "id": None},
        )


_STATE = _State()


class _FakeDashdHandler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        pass

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            payload = None
        _STATE.received.append({"path": self.path, "headers": dict(self.headers), "body": payload})
        status, body = _STATE.handler(payload, self.headers, self.path)
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def fake_node() -> Any:
    _STATE.received.clear()
    _STATE.handler = lambda payload, headers, path: (
        200,
        {
            "result": None,
            "error": None,
            "id": payload.get("id") if isinstance(payload, dict) else None,
        },
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeDashdHandler)
    server.daemon_threads = True
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def _client(port: int, **overrides: Any) -> DashRPC:
    kwargs: dict[str, Any] = {
        "host": "127.0.0.1",
        "port": port,
        "user": "u",
        "password": "s3cret-pw",
    }
    kwargs.update(overrides)
    return DashRPC(DashRPCConfig(**kwargs))


def _basic(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def _ok(result: Any) -> Handler:
    def handle(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        req_id = payload.get("id") if isinstance(payload, dict) else None
        return 200, {"result": result, "error": None, "id": req_id}

    return handle


def test_jsonrpc_body_shape_and_text_plain(fake_node: int) -> None:
    _STATE.handler = _ok(0)
    assert _client(fake_node).call("getblockcount") == 0
    assert len(_STATE.received) == 1
    seen = _STATE.received[0]
    assert seen["path"] == "/"
    assert seen["body"] == {
        "jsonrpc": "1.0",
        "id": "1",
        "method": "getblockcount",
        "params": [],
    }
    assert seen["headers"]["Content-Type"] == "text/plain"


def test_params_are_forwarded(fake_node: int) -> None:
    _STATE.handler = _ok("hash")
    _client(fake_node).call("getblockhash", 42)
    assert _STATE.received[0]["body"]["params"] == [42]


def test_basic_auth_header_and_no_password_in_logs(
    fake_node: int, caplog: pytest.LogCaptureFixture
) -> None:
    _STATE.handler = _ok(0)
    with caplog.at_level(logging.DEBUG, logger="ourdash.core.rpc"):
        _client(fake_node).call("getblockcount")
    assert _STATE.received[0]["headers"]["Authorization"] == _basic("u", "s3cret-pw")
    assert "s3cret-pw" not in caplog.text


def test_wallet_path_selection(fake_node: int) -> None:
    _STATE.handler = _ok(0)
    _client(fake_node, wallet="mywallet").call("getbalance")
    assert _STATE.received[0]["path"] == "/wallet/mywallet"


def test_bad_wallet_selection_rejected() -> None:
    for bad in ("", "a/b", "../evil"):
        with pytest.raises(ConfigError):
            DashRPC(DashRPCConfig(wallet=bad, user="u", password="p"))


def test_timeout_maps_to_rpc_timeout_error(fake_node: int) -> None:
    def slow(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        time.sleep(0.5)
        return 200, {"result": 0, "error": None, "id": None}

    _STATE.handler = slow
    with pytest.raises(RpcTimeoutError):
        _client(fake_node, timeout_s=0.1).call("getblockcount")


def test_refused_connection_maps_to_rpc_connection_error() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        closed_port = int(sock.getsockname()[1])
    with pytest.raises(RpcConnectionError):
        _client(closed_port, timeout_s=1.0).call("getblockcount")


def test_http_401_maps_to_auth_error_without_retry(fake_node: int) -> None:
    _STATE.handler = lambda payload, headers, path: (401, {})
    with pytest.raises(RpcAuthError):
        _client(fake_node).call("getblockcount")
    assert len(_STATE.received) == 1


def test_node_error_object_preserves_code(fake_node: int) -> None:
    def node_error(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        return 500, {
            "result": None,
            "error": {"code": -8, "message": "Block not found"},
            "id": payload.get("id"),
        }

    _STATE.handler = node_error
    with pytest.raises(RpcError) as exc_info:
        _client(fake_node).call("getblock", "deadbeef")
    assert exc_info.value.code == -8
    assert "Block not found" in str(exc_info.value)


def test_warming_up_retries_then_succeeds(fake_node: int) -> None:
    calls = {"n": 0}

    def flaky(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            return 500, {
                "result": None,
                "error": {"code": -28, "message": "warming up"},
                "id": payload.get("id"),
            }
        return 200, {"result": 42, "error": None, "id": payload.get("id")}

    _STATE.handler = flaky
    assert _client(fake_node).call("getblockcount") == 42
    assert calls["n"] == 2


def test_persistent_warming_up_raises_with_code(fake_node: int) -> None:
    def always_warming(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        return 500, {
            "result": None,
            "error": {"code": -28, "message": "warming up"},
            "id": payload.get("id"),
        }

    _STATE.handler = always_warming
    with pytest.raises(RpcError) as exc_info:
        _client(fake_node).call("getblockcount")
    assert exc_info.value.code == -28
    assert len(_STATE.received) == 3


def test_batch_order_and_incremental_string_ids(fake_node: int) -> None:
    def echo(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        return 200, [
            {"result": f"r-{item['method']}", "error": None, "id": item["id"]} for item in payload
        ]

    _STATE.handler = echo
    out = _client(fake_node).batch([("getblockcount", []), ("getbestblockhash", [])])
    assert out == ["r-getblockcount", "r-getbestblockhash"]
    sent = _STATE.received[0]["body"]
    assert isinstance(sent, list) and len(sent) == 2
    assert [item["id"] for item in sent] == ["1", "2"]
    assert all(isinstance(item["id"], str) for item in sent)


def test_batch_per_call_error_mapping(fake_node: int) -> None:
    def mixed(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        return 200, [
            (
                {
                    "result": None,
                    "error": {"code": -5, "message": "Invalid params"},
                    "id": item["id"],
                }
                if item["method"] == "bad"
                else {"result": "fine", "error": None, "id": item["id"]}
            )
            for item in payload
        ]

    _STATE.handler = mixed
    with pytest.raises(RpcError) as exc_info:
        _client(fake_node).batch([("getblockcount", []), ("bad", [])])
    assert exc_info.value.code == -5


def test_remote_host_refused_without_opt_in() -> None:
    with pytest.raises(ConfigError):
        DashRPC(DashRPCConfig(host="192.0.2.1", user="u", password="p"))


def test_remote_host_allowed_with_explicit_opt_in() -> None:
    rpc = DashRPC(DashRPCConfig(host="192.0.2.1", user="u", password="p", remote_ok=True))
    assert rpc.config.host == "192.0.2.1"


def test_loopback_variants_allowed() -> None:
    for host in ("127.0.0.1", "::1", "localhost"):
        rpc = DashRPC(DashRPCConfig(host=host, user="u", password="p"))
        assert rpc.config.host == host


def test_from_env_honors_only_known_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OURDASH_RPC_URL", "http://127.0.0.1:18332")
    monkeypatch.setenv("OURDASH_RPC_USER", "env-u")
    monkeypatch.setenv("OURDASH_RPC_PASSWORD", "env-p")
    monkeypatch.setenv("OURDASH_RPC_WALLET", "envwallet")
    monkeypatch.setenv("OURDASH_RPC_TIMEOUT_S", "1")
    config = DashRPCConfig.from_env()
    assert (config.host, config.port) == ("127.0.0.1", 18332)
    assert (config.user, config.password, config.wallet) == ("env-u", "env-p", "envwallet")
    assert config.timeout_s == 30.0


def test_missing_credentials_refuses_before_network() -> None:
    with pytest.raises(ConfigError):
        DashRPC().call("getblockcount")


def test_cookie_file_auth(tmp_path: Any, fake_node: int) -> None:
    cookie = tmp_path / "cookie"
    cookie.write_text("cookieuser:cookie-secret", encoding="utf-8")
    _STATE.handler = _ok(0)
    rpc = DashRPC(DashRPCConfig(host="127.0.0.1", port=fake_node, cookie_path=str(cookie)))
    assert rpc.call("getblockcount") == 0
    assert _STATE.received[0]["headers"]["Authorization"] == _basic("cookieuser", "cookie-secret")


def test_explicit_user_password_wins_over_cookie(tmp_path: Any, fake_node: int) -> None:
    cookie = tmp_path / "cookie"
    cookie.write_text("cookieuser:cookie-secret", encoding="utf-8")
    _STATE.handler = _ok(0)
    rpc = _client(fake_node, cookie_path=str(cookie))
    rpc.call("getblockcount")
    assert _STATE.received[0]["headers"]["Authorization"] == _basic("u", "s3cret-pw")


def test_config_repr_never_renders_secrets() -> None:
    config = DashRPCConfig(user="admin", password="s3cret-pw", cookie_path="/tmp/c", wallet="w")
    rendered = repr(config) + str(config)
    assert "s3cret-pw" not in rendered
    assert "admin" not in rendered
    assert "9998" in rendered


def test_transport_errors_carry_no_secrets(fake_node: int) -> None:
    _STATE.handler = lambda payload, headers, path: (401, {})
    with pytest.raises(RpcAuthError) as exc_info:
        _client(fake_node).call("getblockcount")
    assert "s3cret-pw" not in str(exc_info.value)
    assert "s3cret-pw" not in repr(exc_info.value)


@pytest.mark.hybrid
def test_regtest_node_reports_blockcount(dashd_regtest: Any) -> None:
    count = dashd_regtest["rpc"].call("getblockcount")
    assert isinstance(count, int) and count >= 0
