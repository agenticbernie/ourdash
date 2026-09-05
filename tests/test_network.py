"""Phase 4: network health reads (chain tips, masternode diff, ChainLock tip).

Fully-Automated against canned getchaintips / masternode list /
getbestchainlock payloads (tip parsing, three-list diff shape on crafted
before/after snapshots, behind_by arithmetic) plus the REST-vs-ZMQ boundary
docstring scan. Hybrid tests execute all three readers against regtest: shape
+ types only — boolean lock values are NOT asserted true on regtest because a
private regtest node forms no LLMQ quorums, so no ChainLock/quorum state
exists there (the except-RpcError branch below documents exactly this).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

import ourdash.core.network as network_module
from ourdash.core.network import (
    chainlock_tip_status,
    diff_masternode_lists,
    get_chain_tips,
    get_masternode_list,
    masternode_list_diff,
)
from ourdash.core.rpc import DashRPC, DashRPCConfig
from ourdash.errors import RpcError

PROTX_A = "aa" * 32
PROTX_B = "bb" * 32
PROTX_C = "cc" * 32


def _tips_payload() -> list[dict[str, Any]]:
    return [
        {
            "height": 150,
            "hash": "bb" * 32,
            "branchlen": 0,
            "status": "active",
            "unexpected_future_field": True,
        },
        {"height": 148, "hash": "cc" * 32, "branchlen": 2, "status": "valid-fork"},
    ]


def _node_entry(address: str, status: str = "ENABLED") -> dict[str, Any]:
    return {"address": address, "payee": "yX1dummy", "status": status}


# --- In-process fake dashd --------------------------------------------------


class _State:
    def __init__(self) -> None:
        self.received: list[dict[str, Any]] = []
        self.routes: dict[str, tuple[str, Any]] = {}


_STATE = _State()


class _FakeDashdHandler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        pass

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        _STATE.received.append({"path": self.path, "body": payload})
        route = _STATE.routes.get(payload.get("method", ""))
        if route is None:
            body: Any = {
                "result": None,
                "error": {"code": -32601, "message": "Method not found"},
                "id": payload.get("id"),
            }
        elif route[0] == "ok":
            body = {"result": route[1], "error": None, "id": payload.get("id")}
        else:
            _, code, message = route
            body = {
                "result": None,
                "error": {"code": code, "message": message},
                "id": payload.get("id"),
            }
        data = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def fake_node() -> Any:
    _STATE.received.clear()
    _STATE.routes.clear()
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


def _client(port: int) -> DashRPC:
    return DashRPC(DashRPCConfig(host="127.0.0.1", port=port, user="u", password="p"))


# --- Chain tips --------------------------------------------------------------


def test_chain_tips_parsing_ignores_unknown_extras(fake_node: int) -> None:
    _STATE.routes["getchaintips"] = ("ok", _tips_payload())
    tips = get_chain_tips(_client(fake_node))
    assert len(tips) == 2
    assert (tips[0].height, tips[0].branchlen, tips[0].status) == (150, 0, "active")
    assert tips[0].hash == "bb" * 32
    assert (tips[1].height, tips[1].branchlen, tips[1].status) == (148, 2, "valid-fork")


def test_chain_tips_malformed_rejected(fake_node: int) -> None:
    _STATE.routes["getchaintips"] = ("ok", {"height": 1})
    with pytest.raises(RpcError, match="malformed"):
        get_chain_tips(_client(fake_node))
    _STATE.routes["getchaintips"] = ("ok", [{"height": 1}])
    with pytest.raises(RpcError, match="malformed"):
        get_chain_tips(_client(fake_node))


# --- Masternode diff -----------------------------------------------------------


def test_masternode_diff_three_lists() -> None:
    """Diff shape: three sorted lists of deterministic proTxHash identifiers.

    ``before``/``after`` are full ``masternode list json`` snapshots taken at
    two heights (proTxHash -> quorum-relevant entry). ``added`` = keys only in
    ``after`` (new masternodes), ``removed`` = keys only in ``before``
    (departed), ``changed`` = keys in both with a different entry (e.g. a new
    payout address or PoSe status flip).
    """
    before = {
        PROTX_A: _node_entry("10.0.0.1:9999"),
        PROTX_B: _node_entry("10.0.0.2:9999"),
    }
    after = {
        PROTX_B: _node_entry("10.0.0.9:9999"),  # same node, changed address
        PROTX_C: _node_entry("10.0.0.3:9999"),  # brand-new node
    }
    diff = diff_masternode_lists(before, after)
    assert diff.added == [PROTX_C]
    assert diff.removed == [PROTX_A]
    assert diff.changed == [PROTX_B]
    assert diff_masternode_lists(before, dict(before)) == diff_masternode_lists({}, {})
    assert diff.to_dict() == {"added": [PROTX_C], "removed": [PROTX_A], "changed": [PROTX_B]}


def test_masternode_diff_rejects_non_mappings() -> None:
    with pytest.raises(RpcError, match="proTxHash"):
        diff_masternode_lists([], {})  # type: ignore[arg-type]


def test_masternode_list_diff_against_live_snapshot(fake_node: int) -> None:
    live = {PROTX_B: _node_entry("10.0.0.9:9999"), PROTX_C: _node_entry("10.0.0.3:9999")}
    _STATE.routes["masternode"] = ("ok", live)
    base = {PROTX_A: _node_entry("10.0.0.1:9999"), PROTX_B: _node_entry("10.0.0.2:9999")}
    diff = masternode_list_diff(_client(fake_node), base)
    assert (diff.added, diff.removed, diff.changed) == ([PROTX_C], [PROTX_A], [PROTX_B])
    assert _STATE.received[0]["body"] == {
        "jsonrpc": "1.0",
        "id": "1",
        "method": "masternode",
        "params": ["list", "json"],
    }


def test_masternode_list_empty_base_means_all_added(fake_node: int) -> None:
    _STATE.routes["masternode"] = ("ok", {PROTX_A: _node_entry("10.0.0.1:9999")})
    diff = masternode_list_diff(_client(fake_node))
    assert (diff.added, diff.removed, diff.changed) == ([PROTX_A], [], [])


def test_masternode_list_legacy_alias_fallback(fake_node: int) -> None:
    _STATE.routes["masternode"] = ("err", -32601, "Method not found")
    _STATE.routes["masternodelist"] = ("ok", {})
    assert get_masternode_list(_client(fake_node)) == {}
    methods = [entry["body"]["method"] for entry in _STATE.received]
    assert methods == ["masternode", "masternodelist"]


def test_masternode_list_non_mapping_rejected(fake_node: int) -> None:
    _STATE.routes["masternode"] = ("ok", ["not", "a", "mapping"])
    with pytest.raises(RpcError, match="malformed"):
        get_masternode_list(_client(fake_node))


# --- ChainLock tip -------------------------------------------------------------


def test_chainlock_behind_by_arithmetic(fake_node: int) -> None:
    _STATE.routes["getbestchainlock"] = ("ok", {"blockhash": "bb" * 32, "height": 900})
    _STATE.routes["getblockcount"] = ("ok", 905)
    status = chainlock_tip_status(_client(fake_node))
    assert status.height == 900
    assert status.blockhash == "bb" * 32
    assert status.behind_by == 5


def test_chainlock_falls_back_to_blockchaininfo_height(fake_node: int) -> None:
    _STATE.routes["getbestchainlock"] = ("ok", {"blockhash": "bb" * 32, "height": 900})
    _STATE.routes["getblockcount"] = ("err", -32601, "Method not found")
    _STATE.routes["getblockchaininfo"] = ("ok", {"blocks": 901})
    assert chainlock_tip_status(_client(fake_node)).behind_by == 1


def test_chainlock_malformed_rejected(fake_node: int) -> None:
    _STATE.routes["getbestchainlock"] = ("ok", {"height": "nine-hundred"})
    _STATE.routes["getblockcount"] = ("ok", 905)
    with pytest.raises(RpcError, match="malformed"):
        chainlock_tip_status(_client(fake_node))


def test_chainlock_node_error_propagates_with_code(fake_node: int) -> None:
    _STATE.routes["getbestchainlock"] = ("err", -32601, "Method not found")
    with pytest.raises(RpcError) as exc_info:
        chainlock_tip_status(_client(fake_node))
    assert exc_info.value.code == -32601


# --- Boundary guard --------------------------------------------------------------


def test_rest_zmq_boundary_docstring() -> None:
    text = Path(network_module.__file__ or "").read_text(encoding="utf-8")
    for required in (
        "REST",
        "ZMQ",
        "SEPARATE",
        "trusted-network-only",
        "same-port-or-separate-port",
        "NEITHER",
        "JSON-RPC",
        "opt-in",
    ):
        assert required in text, f"boundary wording removed: {required!r}"


# --- Hybrid regtest --------------------------------------------------------------


@pytest.mark.hybrid
def test_hybrid_health_reads(dashd_regtest: Any) -> None:
    """SPEC 9: tips + masternode diff + ChainLock tip execute on regtest."""
    rpc = dashd_regtest["rpc"]
    tips = get_chain_tips(rpc)
    assert tips, "regtest must report at least the active tip"
    assert all(isinstance(tip.height, int) and tip.hash for tip in tips)
    assert any(tip.status == "active" and tip.branchlen == 0 for tip in tips)
    diff = masternode_list_diff(rpc)  # regtest runs no masternodes: three empty lists
    assert (diff.added, diff.removed, diff.changed) == ([], [], [])
    try:
        status = chainlock_tip_status(rpc)
    except RpcError as exc:
        # A private regtest node forms no LLMQ quorums, so there is no
        # ChainLock state to read; the typed error (code preserved) is the
        # correct regtest outcome — lock values are never asserted true here.
        assert exc.code is not None
    else:
        assert isinstance(status.height, int) and status.blockhash
        assert isinstance(status.behind_by, int) and status.behind_by >= 0
