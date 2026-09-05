"""DAPI transport tests vs an in-process fake endpoint (loopback only).

No live network: seed resolution, framing, TLS/timeout/retry behavior, and
the dead-default removal are all asserted locally.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
import requests

from ourdash.errors import DAPIError, RpcAuthError, RpcConnectionError, RpcTimeoutError
from ourdash.platform import seeds as seeds_module
from ourdash.platform.dapi import DAPIClient, DAPIConfig
from ourdash.platform.seeds import NETWORKS, SEEDS, SeedEntry, seeds_for

Handler = Callable[[Any, Any, str], tuple[int, Any]]


class _State:
    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []
        self.handler: Handler = lambda payload, headers, path: (
            200,
            {"jsonrpc": "2.0", "result": None, "id": 1},
        )


_STATE = _State()


class _FakeDAPIHandler(BaseHTTPRequestHandler):
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
def fake_dapi() -> Any:
    _STATE.received.clear()
    _STATE.handler = lambda payload, headers, path: (
        200,
        {
            "jsonrpc": "2.0",
            "result": None,
            "id": payload.get("id") if isinstance(payload, dict) else 1,
        },
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeDAPIHandler)
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


def _client(port: int, **overrides: Any) -> DAPIClient:
    return DAPIClient(DAPIConfig(address=f"http://127.0.0.1:{port}", **overrides))


def _ok(result: Any) -> Handler:
    def handle(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        req_id = payload.get("id") if isinstance(payload, dict) else 1
        return 200, {"jsonrpc": "2.0", "result": result, "id": req_id}

    return handle


def test_dead_placeholder_ships_nowhere() -> None:
    repo = Path(__file__).resolve().parent.parent / "src"
    offenders = [
        str(path.relative_to(repo))
        for path in sorted(repo.rglob("*.py"))
        if "api.dash.org" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_address_defaults_to_none_and_timeout_stays_30() -> None:
    config = DAPIClient().config
    assert config.address is None
    assert config.timeout_s == 30.0


def test_call_without_address_guides_to_from_network(fake_dapi: int) -> None:
    client = DAPIClient()
    with pytest.raises(DAPIError, match="from_network"):
        client.get_best_block_hash()
    assert _STATE.received == []


def test_from_network_resolution() -> None:
    assert (
        DAPIClient.from_network("testnet").config.address
        == "https://seed-1.testnet.networks.dash.org:1443"
    )
    assert (
        DAPIClient.from_network("mainnet").config.address
        == "https://seed-1.mainnet.networks.dash.org:443"
    )
    assert DAPIClient.from_network("regtest").config.address == "http://127.0.0.1:1443"
    assert DAPIClient.from_network("devnet").config.address == "http://127.0.0.1:1443"
    assert DAPIClient.from_network("testnet", timeout_s=5.0).config.timeout_s == 5.0


def test_from_network_unknown_network() -> None:
    with pytest.raises(DAPIError, match="unknown network"):
        DAPIClient.from_network("evonet")


def test_from_network_empty_seed_list_guides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        seeds_module, "SEEDS", {"testnet": [], **{k: v for k, v in SEEDS.items() if k != "testnet"}}
    )
    with pytest.raises(DAPIError, match="no DAPI seed is documented"):
        DAPIClient.from_network("testnet")


def test_seeds_for_unknown_network() -> None:
    with pytest.raises(DAPIError, match="unknown network"):
        seeds_for("evonet")


def test_seed_metadata_and_no_placeholders() -> None:
    assert set(SEEDS) == set(NETWORKS)
    for network, entries in SEEDS.items():
        assert entries, f"{network} must list its (possibly loopback) seeds"
        for entry in entries:
            assert isinstance(entry, SeedEntry)
            assert entry.interface == "json-rpc"
            assert "api.dash.org" not in entry.host
            assert "api.dash.org" not in entry.address
            if entry.host not in ("127.0.0.1", "::1", "localhost"):
                assert entry.source, f"{network}/{entry.host} needs a source"
                assert entry.retrieved, f"{network}/{entry.host} needs a retrieval date"


def test_jsonrpc_body_shape_and_content_type(fake_dapi: int) -> None:
    _STATE.handler = _ok("deadbeef")
    assert _client(fake_dapi).get_best_block_hash() == "deadbeef"
    assert len(_STATE.received) == 1
    seen = _STATE.received[0]
    assert seen["body"] == {
        "method": "getBestBlockHash",
        "id": 1,
        "jsonrpc": "2.0",
        "params": {},
    }
    assert seen["headers"]["Content-Type"] == "application/json"


def test_request_ids_increment(fake_dapi: int) -> None:
    _STATE.handler = _ok("hash")
    client = _client(fake_dapi)
    client.get_best_block_hash()
    client.get_best_block_hash()
    assert [_STATE.received[0]["body"]["id"], _STATE.received[1]["body"]["id"]] == [1, 2]


def test_get_block_hash_params(fake_dapi: int) -> None:
    _STATE.handler = _ok("hash-at-100")
    assert _client(fake_dapi).get_block_hash(100) == "hash-at-100"
    assert _STATE.received[0]["body"]["params"] == {"height": 100}


def test_get_block_hash_rejects_bad_height(fake_dapi: int) -> None:
    client = _client(fake_dapi)
    for bad in (-1, True, "100", 1.5, None):
        with pytest.raises(DAPIError):
            client.get_block_hash(bad)  # type: ignore[arg-type]
    assert _STATE.received == []


def test_get_status_composes_verified_reads(fake_dapi: int) -> None:
    _STATE.handler = _ok("tip-hash")
    assert _client(fake_dapi).get_status() == {"best_block_hash": "tip-hash"}
    assert _STATE.received[0]["body"]["method"] == "getBestBlockHash"


def test_broadcast_refuses_without_network_and_validates_hex(
    fake_dapi: int,
) -> None:
    client = _client(fake_dapi)
    with pytest.raises(DAPIError, match="gRPC"):
        client.broadcast_transaction("deadbeef" * 32)
    for bad in ("", "not-hex!!", 123):
        with pytest.raises(DAPIError):
            client.broadcast_transaction(bad)  # type: ignore[arg-type]
    assert _STATE.received == []


def test_timeout_maps_to_rpc_timeout_error(fake_dapi: int) -> None:
    def slow(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        time.sleep(0.5)
        return 200, {"jsonrpc": "2.0", "result": "late", "id": 1}

    _STATE.handler = slow
    with pytest.raises(RpcTimeoutError):
        _client(fake_dapi, timeout_s=0.1).get_best_block_hash()


def test_timeouts_are_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def always_slow(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        raise requests.Timeout("slow")

    monkeypatch.setattr(requests, "post", always_slow)
    with pytest.raises(RpcTimeoutError):
        DAPIClient(DAPIConfig(address="http://127.0.0.1:1")).get_best_block_hash()
    assert calls["n"] == 1


def test_refused_connection_retries_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def refused(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "post", refused)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    with pytest.raises(RpcConnectionError):
        DAPIClient(DAPIConfig(address="http://127.0.0.1:1")).get_best_block_hash()
    assert calls["n"] == 3


def test_refused_port_maps_to_connection_error() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        closed_port = int(sock.getsockname()[1])
    with pytest.raises(RpcConnectionError):
        _client(closed_port, timeout_s=1.0).get_best_block_hash()


def test_http_401_maps_to_auth_error_without_retry(fake_dapi: int) -> None:
    _STATE.handler = lambda payload, headers, path: (401, {})
    with pytest.raises(RpcAuthError):
        _client(fake_dapi).get_best_block_hash()
    assert len(_STATE.received) == 1


def test_node_error_object_maps_to_dapi_error(fake_dapi: int) -> None:
    def node_error(payload: Any, headers: Any, path: str) -> tuple[int, Any]:
        return 200, {"jsonrpc": "2.0", "error": {"message": "Method not found"}, "id": 1}

    _STATE.handler = node_error
    with pytest.raises(DAPIError, match="Method not found"):
        _client(fake_dapi).get_best_block_hash()


def test_malformed_response_maps_to_dapi_error(fake_dapi: int) -> None:
    _STATE.handler = lambda payload, headers, path: (
        200,
        {"jsonrpc": "2.0", "id": 1},
    )
    with pytest.raises(DAPIError, match="malformed"):
        _client(fake_dapi).get_best_block_hash()


def test_tls_verification_is_always_on(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    class _Response:
        status_code = 200

        def json(self) -> Any:
            return {"jsonrpc": "2.0", "result": "hash", "id": 1}

    def capture(*args: Any, **kwargs: Any) -> Any:
        seen.update(kwargs)
        return _Response()

    monkeypatch.setattr(requests, "post", capture)
    client = DAPIClient(DAPIConfig(address="https://seed-1.testnet.networks.dash.org:1443"))
    assert client.get_best_block_hash() == "hash"
    assert seen.get("verify") is True


def test_from_env_honors_only_known_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OURDASH_DAPI_ADDRESS", "https://dapi.example:1443")
    monkeypatch.setenv("OURDASH_DAPI_TIMEOUT_S", "5")
    config = DAPIConfig.from_env()
    assert config.address == "https://dapi.example:1443"
    assert config.timeout_s == 5.0
    monkeypatch.delenv("OURDASH_DAPI_ADDRESS")
    monkeypatch.delenv("OURDASH_DAPI_TIMEOUT_S")
    assert DAPIConfig.from_env() == DAPIConfig(address=None, timeout_s=30.0)
    monkeypatch.setenv("OURDASH_DAPI_TIMEOUT_S", "not-a-number")
    assert DAPIConfig.from_env().timeout_s == 30.0


def test_config_repr_never_renders_secrets() -> None:
    assert "1443" in repr(DAPIConfig(address="https://dapi.example:1443"))
    rendered = repr(DAPIConfig(address="https://user:s3cret@example:1443"))
    assert "s3cret" not in rendered
