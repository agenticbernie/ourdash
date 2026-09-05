"""Phase 4: typed Core reads (chain info, block, tx, balance, address) + wallets.

Fully-Automated against an in-process fake dashd (response-shape parsing,
wallet-endpoint routing, unknown-wallet code passthrough, to_dict() JSON
round-trips). Hybrid tests prove SPEC 1 (chain info + block + balance on a
live regtest node) and SPEC 3 (second wallet funded separately, per-wallet
balances differ, selection routes correctly). The Agent-Probe testnet
spot-check (SPEC 14 leg) is recorded, never gated: it runs only with
OURDASH_TESTNET_RPC_URL set and the full walkthrough closes in Phase 6.
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

import ourdash.core.chain as chain_module
from ourdash.core.chain import (
    get_balance,
    get_block,
    get_blockchain_info,
    get_new_address,
    get_transaction,
)
from ourdash.core.rpc import DashRPC, DashRPCConfig
from ourdash.core.wallet import from_mnemonic
from ourdash.errors import RpcError

_WALLET = from_mnemonic(
    "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
    passphrase="TREZOR",
)
ADDR0 = _WALLET.receiving_address(0)
ADDR1 = _WALLET.receiving_address(1)
ADDR2 = _WALLET.receiving_address(2)
FAKE_TXID = "0123456789abcdef" * 4
FAKE_HASH = "bb" * 32


def _info_payload() -> dict[str, Any]:
    return {
        "chain": "regtest",
        "blocks": 150,
        "headers": 150,
        "bestblockhash": FAKE_HASH,
        "difficulty": 1.0,
        "verificationprogress": 1.0,
        "unexpected_future_field": {"nested": True},
    }


def _block_payload() -> dict[str, Any]:
    return {
        "hash": FAKE_HASH,
        "confirmations": 3,
        "height": 150,
        "time": 1700000000,
        "nTx": 2,
        "tx": [FAKE_TXID, "ab" * 32],
        "chainlock": True,
        "unexpected_future_field": 1,
    }


def _raw_tx_payload() -> dict[str, Any]:
    return {
        "txid": FAKE_TXID,
        "hash": FAKE_TXID,
        "confirmations": 6,
        "blockhash": FAKE_HASH,
        "time": 1700000001,
        "vout": [],
        "unexpected_future_field": 1,
    }


def _wallet_tx_payload() -> dict[str, Any]:
    return {
        "amount": 1.5,
        "fee": -0.0001,
        "confirmations": 6,
        "instantlock": True,
        "txid": FAKE_TXID,
        "blockhash": FAKE_HASH,
    }


def _balances_payload() -> dict[str, Any]:
    return {
        "mine": {"trusted": 2.5, "untrusted_pending": 0.25, "immature": 0.0},
        "watchonly": None,
    }


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


def _methods() -> list[str]:
    return [entry["body"]["method"] for entry in _STATE.received]


def _assert_stdlib(value: Any) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for item in value:
            _assert_stdlib(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_stdlib(item)
        return
    raise AssertionError(f"non-stdlib value in to_dict(): {value!r}")


# --- Chain info --------------------------------------------------------------


def test_blockchain_info_parsing_ignores_unknown_extras(fake_node: int) -> None:
    _STATE.routes["getblockchaininfo"] = ("ok", _info_payload())
    info = get_blockchain_info(_client(fake_node))
    assert (info.chain, info.blocks, info.headers) == ("regtest", 150, 150)
    assert info.bestblockhash == FAKE_HASH
    assert info.difficulty == 1.0
    assert info.verificationprogress == 1.0


def test_blockchain_info_missing_field_rejected(fake_node: int) -> None:
    payload = _info_payload()
    del payload["blocks"]
    _STATE.routes["getblockchaininfo"] = ("ok", payload)
    with pytest.raises(RpcError, match="malformed"):
        get_blockchain_info(_client(fake_node))


def test_node_error_code_preserved(fake_node: int) -> None:
    _STATE.routes["getblockchaininfo"] = ("err", -28, "warming up")
    with pytest.raises(RpcError) as exc_info:
        get_blockchain_info(_client(fake_node))
    assert exc_info.value.code == -28


# --- Blocks ------------------------------------------------------------------


def test_get_block_by_hash(fake_node: int) -> None:
    _STATE.routes["getblock"] = ("ok", _block_payload())
    block = get_block(_client(fake_node), FAKE_HASH)
    assert (block.hash, block.height, block.time) == (FAKE_HASH, 150, 1700000000)
    assert block.txids == [FAKE_TXID, "ab" * 32]
    assert block.tx_count == 2
    assert block.chainlock is True
    assert _STATE.received[0]["body"]["params"] == [FAKE_HASH, 1]


def test_get_block_by_height_resolves_via_getblockhash(fake_node: int) -> None:
    _STATE.routes["getblockhash"] = ("ok", FAKE_HASH)
    _STATE.routes["getblock"] = ("ok", _block_payload())
    block = get_block(_client(fake_node), 150)
    assert block.height == 150
    assert _methods() == ["getblockhash", "getblock"]
    assert _STATE.received[0]["body"]["params"] == [150]


def test_get_block_verbosity_2_reduces_tx_objects(fake_node: int) -> None:
    payload = _block_payload()
    payload["tx"] = [{"txid": FAKE_TXID}, {"hash": "ab" * 32}]
    del payload["nTx"]
    _STATE.routes["getblock"] = ("ok", payload)
    block = get_block(_client(fake_node), FAKE_HASH, verbosity=2)
    assert block.txids == [FAKE_TXID, "ab" * 32]
    assert block.tx_count == 2  # derived from the list when nTx is absent


def test_get_block_chainlock_absent_is_none(fake_node: int) -> None:
    payload = _block_payload()
    del payload["chainlock"]
    _STATE.routes["getblock"] = ("ok", payload)
    assert get_block(_client(fake_node), FAKE_HASH).chainlock is None


def test_get_block_verbosity_0_refused_pre_network(fake_node: int) -> None:
    with pytest.raises(RpcError, match="verbosity"):
        get_block(_client(fake_node), FAKE_HASH, verbosity=0)
    assert _STATE.received == []


# --- Transactions ------------------------------------------------------------


def test_get_transaction_raw_verbose(fake_node: int) -> None:
    _STATE.routes["getrawtransaction"] = ("ok", _raw_tx_payload())
    tx = get_transaction(_client(fake_node), FAKE_TXID)
    assert tx.txid == FAKE_TXID
    assert tx.confirmations == 6
    assert tx.blockhash == FAKE_HASH
    assert tx.instantlock is False
    assert _STATE.received[0]["body"]["params"] == [FAKE_TXID, True]


def test_get_transaction_falls_back_to_wallet_view(fake_node: int) -> None:
    _STATE.routes["getrawtransaction"] = ("err", -5, "No such mempool or blockchain transaction")
    payload = _wallet_tx_payload()
    payload["instantlock"] = False
    payload["instantlock_internal"] = True
    _STATE.routes["gettransaction"] = ("ok", payload)
    tx = get_transaction(_client(fake_node), FAKE_TXID)
    assert tx.amount == 1.5
    assert tx.fee == -0.0001
    assert tx.instantlock is True  # instantlock_internal counts
    assert _methods() == ["getrawtransaction", "gettransaction"]


def test_get_transaction_wallet_view_direct(fake_node: int) -> None:
    _STATE.routes["gettransaction"] = ("ok", _wallet_tx_payload())
    tx = get_transaction(_client(fake_node), FAKE_TXID, wallet="w1")
    assert tx.amount == 1.5
    assert tx.instantlock is True
    assert _methods() == ["gettransaction"]
    assert _STATE.received[0]["path"] == "/wallet/w1"


def test_get_transaction_bad_txid_refused_pre_network(fake_node: int) -> None:
    for bad in ("", "zz", "ab" * 32 + "x", "ab" * 31):
        with pytest.raises(RpcError, match="64 hex"):
            get_transaction(_client(fake_node), bad)
    assert _STATE.received == []


# --- Balances + addresses + wallet routing -----------------------------------


def test_get_balance_split(fake_node: int) -> None:
    _STATE.routes["getbalances"] = ("ok", _balances_payload())
    balance = get_balance(_client(fake_node))
    assert (balance.confirmed, balance.unconfirmed, balance.immature) == (2.5, 0.25, 0.0)
    assert balance.wallet is None


def test_get_balance_legacy_fallback(fake_node: int) -> None:
    _STATE.routes["getbalances"] = ("err", -32601, "Method not found")
    _STATE.routes["getbalance"] = ("ok", 1.0)
    _STATE.routes["getunconfirmedbalance"] = ("ok", 0.5)
    balance = get_balance(_client(fake_node))
    assert (balance.confirmed, balance.unconfirmed) == (1.0, 0.5)
    assert _methods() == ["getbalances", "getbalance", "getunconfirmedbalance"]


def test_wallet_routing_binds_endpoint_without_mutating_caller(fake_node: int) -> None:
    _STATE.routes["getbalances"] = ("ok", _balances_payload())
    _STATE.routes["getnewaddress"] = ("ok", ADDR0)
    _STATE.routes["gettransaction"] = ("ok", _wallet_tx_payload())
    caller = _client(fake_node)
    assert get_balance(caller, wallet="w2").wallet == "w2"
    assert get_new_address(caller, wallet="w2") == ADDR0
    assert get_transaction(caller, FAKE_TXID, wallet="w2").txid == FAKE_TXID
    assert caller.config.wallet is None  # caller never mutated
    assert [entry["path"] for entry in _STATE.received] == ["/wallet/w2"] * 3
    get_balance(caller)  # unbound call still hits the base endpoint
    assert _STATE.received[-1]["path"] == "/"


def test_unknown_wallet_error_preserves_code(fake_node: int) -> None:
    _STATE.routes["getbalances"] = ("err", -32601, "Method not found")
    _STATE.routes["getbalance"] = ("err", -18, "Requested wallet does not exist or is not loaded")
    with pytest.raises(RpcError) as exc_info:
        get_balance(_client(fake_node), wallet="ghost")
    assert exc_info.value.code == -18


def test_get_new_address_label_forwarded(fake_node: int) -> None:
    _STATE.routes["getnewaddress"] = ("ok", ADDR1)
    assert get_new_address(_client(fake_node), label="savings") == ADDR1
    assert _STATE.received[0]["body"]["params"] == ["savings"]


def test_get_new_address_rejects_node_garbage(fake_node: int) -> None:
    _STATE.routes["getnewaddress"] = ("ok", "not-an-address")
    with pytest.raises(RpcError, match="invalid address"):
        get_new_address(_client(fake_node))


# --- Analyst shape + allowlist -----------------------------------------------


def test_to_dict_json_round_trips_with_stdlib_types(fake_node: int) -> None:
    _STATE.routes["getblock"] = ("ok", _block_payload())
    _STATE.routes["getrawtransaction"] = ("ok", _raw_tx_payload())
    _STATE.routes["getbalances"] = ("ok", _balances_payload())
    client = _client(fake_node)
    models = [
        get_block(client, FAKE_HASH),
        get_transaction(client, FAKE_TXID),
        get_balance(client),
    ]
    for model in models:
        plain = model.to_dict()
        _assert_stdlib(plain)
        assert json.loads(json.dumps(plain)) == plain


def test_method_allowlist_comment() -> None:
    text = Path(chain_module.__file__ or "").read_text(encoding="utf-8")
    assert "v23.1.8" in text
    assert "dash-cli help" in text
    assert "retrieved" in text
    for method in (
        "getblockchaininfo",
        "getblockhash",
        "getblock",
        "getrawtransaction",
        "gettransaction",
        "getbalances",
        "getbalance",
        "getnewaddress",
    ):
        assert method in text, f"allowlist missing {method}"


# --- Hybrid regtest ------------------------------------------------------------


@pytest.mark.hybrid
def test_hybrid_chain_info_block_balance(dashd_regtest: Any) -> None:
    """SPEC 1: chain info + block + balance reads against a live regtest node."""
    base = dashd_regtest["rpc"]
    try:
        base.call("createwallet", "p4main")
    except RpcError:
        pass  # already created earlier in this session
    addr = get_new_address(base, wallet="p4main")
    base.call("generatetoaddress", 2, addr)
    info = get_blockchain_info(base)
    assert info.blocks >= 2
    assert info.bestblockhash and info.verificationprogress > 0
    block = get_block(base, info.blocks)  # height path exercises getblockhash
    assert block.height == info.blocks
    assert block.hash == info.bestblockhash
    assert block.tx_count >= 1 and block.txids
    balance = get_balance(base, wallet="p4main")
    assert isinstance(balance.confirmed, float)
    assert isinstance(balance.unconfirmed, float)
    # Analyst leg: live payloads drop into plain objects.
    for model in (info, block, balance):
        plain = model.to_dict()
        _assert_stdlib(plain)
        assert json.loads(json.dumps(plain)) == plain


@pytest.mark.hybrid
def test_hybrid_multi_wallet_selection(dashd_regtest: Any) -> None:
    """SPEC 3: two wallets funded separately; selection routes correctly."""
    base = dashd_regtest["rpc"]
    for name in ("p4w1", "p4w2"):
        try:
            base.call("createwallet", name)
        except RpcError:
            pass  # already created earlier in this session
    addr1 = get_new_address(base, wallet="p4w1")
    addr2 = get_new_address(base, wallet="p4w2")
    assert addr1 != addr2
    base.call("generatetoaddress", 101, addr1)  # mature a coinbase for p4w1 only
    bal1 = get_balance(base, wallet="p4w1")
    bal2 = get_balance(base, wallet="p4w2")
    assert bal1.confirmed > bal2.confirmed  # funded separately: balances differ
    assert bal1.wallet == "p4w1" and bal2.wallet == "p4w2"
    with pytest.raises(RpcError) as exc_info:  # unknown wallet keeps the node code
        get_balance(base, wallet="no-such-wallet-xyz")
    assert exc_info.value.code is not None


@pytest.mark.agent_probe
def test_agent_probe_testnet_spot_check() -> None:
    """SPEC 14 leg (record, never gate): testnet info + block pull.

    Runs only with OURDASH_TESTNET_RPC_URL (+ USER/PASSWORD) pointed at a
    testnet node; the public-explorer cross-check and full walkthrough close
    in the Phase 6 docs pass.
    """
    url = os.environ.get("OURDASH_TESTNET_RPC_URL", "")
    if not url:
        pytest.skip("no testnet endpoint configured (set OURDASH_TESTNET_RPC_URL)")
    rpc = DashRPC(
        DashRPCConfig(
            host=url,
            port=int(os.environ.get("OURDASH_TESTNET_RPC_PORT", "19998")),
            user=os.environ.get("OURDASH_TESTNET_RPC_USER", ""),
            password=os.environ.get("OURDASH_TESTNET_RPC_PASSWORD", ""),
            remote_ok=True,
        )
    )
    info = get_blockchain_info(rpc)
    assert info.chain == "testnet" and info.blocks > 0
    block = get_block(rpc, info.blocks)
    assert block.height == info.blocks and block.tx_count >= 1
