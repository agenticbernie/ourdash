"""Phase 3: offline payment pipeline (build → review → sign → submit) + finality reads.

Fully-Automated, no node: every network behavior is asserted against an
in-process fake dashd that counts received requests (bad-submit refusal =
zero hits). One Hybrid test runs the full fund → build → sign → submit →
mine → confirm flow against regtest ``dashd`` (skips cleanly without it).
"""

from __future__ import annotations

import hashlib
import json
import threading
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from ecdsa import SECP256k1, VerifyingKey
from ecdsa.util import sigdecode_der

import ourdash.core.transactions as tx_module
from ourdash.core.addresses import validate_address
from ourdash.core.rpc import DashRPC, DashRPCConfig
from ourdash.core.transactions import (
    ConfirmationStatus,
    SignedTx,
    UnsignedTx,
    build,
    confirm_status,
    review,
    sign,
    submit,
)
from ourdash.core.wallet import from_mnemonic
from ourdash.errors import PaymentError, RpcError
from ourdash.utils import b58check_decode, sha256d

MAINNET_P2SH_SEQ = "7SQfxmMEhETVQuHwTQ3XMS11AkrcJwJS18"  # mainnet P2SH (Phase 2 vector)
FAKE_TXID = "0123456789abcdef" * 4
SENTINEL_PASSPHRASE = "sentinel-pass-9f27c1"


def _wallet(network: str = "mainnet") -> Any:
    return from_mnemonic(
        "abandon abandon abandon abandon abandon abandon "
        "abandon abandon abandon abandon abandon about",
        passphrase="TREZOR",
        network=network,
    )


def _vector_unsigned(network: str = "mainnet") -> UnsignedTx:
    wallet = _wallet(network)
    return build(
        [
            {
                "txid": FAKE_TXID,
                "vout": 0,
                "amount_duffs": 100_000,
                "address": wallet.receiving_address(0),
            }
        ],
        [
            {"address": wallet.receiving_address(1), "amount_duffs": 60_000},
            {"address": wallet.receiving_address(2), "amount_duffs": 39_000},
        ],
        network=network,
    )


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
        _STATE.received.append(payload)
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


# --- Build / review ----------------------------------------------------------


def test_deterministic_build_vector() -> None:
    first = _vector_unsigned()
    second = _vector_unsigned()
    assert first == second
    assert first.unsigned_hex() == second.unsigned_hex()
    # Normal tx: version 2, type 0 → int32 0x00000002 little-endian.
    assert first.unsigned_hex().startswith("02000000")
    assert first.fee_duffs == 1_000
    assert len(first.inputs) == 1 and len(first.outputs) == 2
    assert first.network == "mainnet"


def test_review_content_and_shape() -> None:
    unsigned = _vector_unsigned()
    summary = review(unsigned)
    assert summary["kind"] == "unsigned"
    assert summary["network"] == "mainnet"
    assert summary["input_count"] == 1
    assert summary["output_count"] == 2
    assert summary["total_in_duffs"] == 100_000
    assert summary["total_out_duffs"] == 99_000
    assert summary["fee_duffs"] == 1_000
    assert summary["fee_rate_duffs_per_vbyte"] > 0
    assert len(summary["destinations"]) == 2
    assert summary["txid"] is None


def test_build_accepts_model_objects() -> None:
    wallet = _wallet()
    unsigned = build(
        [
            {
                "txid": FAKE_TXID,
                "vout": 1,
                "amount_duffs": 50_000,
                "address": wallet.receiving_address(0),
            }
        ],
        [{"address": wallet.receiving_address(1), "amount_duffs": 49_000}],
        network="mainnet",
    )
    assert unsigned.fee_duffs == 1_000


def test_build_rejections() -> None:
    wallet = _wallet()
    sender = wallet.receiving_address(0)
    dest = wallet.receiving_address(1)
    good_in = {"txid": FAKE_TXID, "vout": 0, "amount_duffs": 100_000, "address": sender}
    good_out = {"address": dest, "amount_duffs": 99_000}
    with pytest.raises(PaymentError):
        build([], [good_out])
    with pytest.raises(PaymentError):
        build([good_in], [])
    with pytest.raises(PaymentError):  # outputs exceed inputs
        build([good_in], [{"address": dest, "amount_duffs": 100_001}])
    with pytest.raises(PaymentError):  # bad txid
        build([{**good_in, "txid": "zz"}], [good_out])
    with pytest.raises(PaymentError):  # non-positive amount
        build([{**good_in, "amount_duffs": 0}], [good_out])
    with pytest.raises(PaymentError):  # duplicate outpoint
        build([good_in, good_in], [good_out])
    with pytest.raises(PaymentError):  # wrong network
        build(
            [good_in],
            [{"address": _wallet("regtest").receiving_address(0), "amount_duffs": 99_000}],
        )
    with pytest.raises(PaymentError):
        build([good_in], [good_out], network="fakenet")


def test_build_refuses_script_inputs_with_deferral() -> None:
    wallet = _wallet()
    with pytest.raises(PaymentError, match="deferred beyond v0.1"):
        build(
            [
                {
                    "txid": FAKE_TXID,
                    "vout": 0,
                    "amount_duffs": 100_000,
                    "address": MAINNET_P2SH_SEQ,
                }
            ],
            [{"address": wallet.receiving_address(1), "amount_duffs": 99_000}],
        )


# --- Sign --------------------------------------------------------------------


def test_sign_round_trip_verifies_on_curve() -> None:
    wallet = _wallet()
    unsigned = _vector_unsigned()
    with pytest.warns(UserWarning, match="watch-only"):
        signed = sign(unsigned, wallet, allow_sign=True)
    assert isinstance(signed, SignedTx)
    assert signed.network == "mainnet"
    assert signed.txid == sha256d(bytes.fromhex(signed.raw_hex))[::-1].hex()
    assert len(signed.raw_hex) > len(unsigned.unsigned_hex())
    # White-box: the scriptSig carries a valid DER signature for its sighash.
    raw = bytes.fromhex(signed.raw_hex)
    assert raw[:4] == b"\x02\x00\x00\x00"
    pos = 4
    assert raw[pos] == 1  # one input
    pos += 1 + 36  # vin count + prevout
    script_len = raw[pos]
    pos += 1
    sig_len = raw[pos]  # push opcode = signature length
    pos += 1
    sig_plus_hashtype = raw[pos : pos + sig_len]
    pos += sig_len
    assert script_len == 2 + sig_len + 33  # two pushes: sig+hashtype, pubkey
    assert sig_plus_hashtype[-1:] == b"\x01"  # SIGHASH_ALL
    pub_len = raw[pos]
    pos += 1
    assert pub_len == 33
    pub = raw[pos : pos + pub_len]
    assert pub == wallet.public_key_bytes(0)
    vk = VerifyingKey.from_string(pub, curve=SECP256k1, hashfunc=hashlib.sha256)
    assert vk.verify_digest(
        sig_plus_hashtype[:-1],
        tx_module._sighash(unsigned, 0),
        sigdecode=sigdecode_der,
    )
    summary = review(signed)
    assert summary["kind"] == "signed"
    assert summary["txid"] == signed.txid


def test_sign_without_opt_in_refused() -> None:
    wallet = _wallet()
    unsigned = _vector_unsigned()
    with pytest.raises(PaymentError, match="allow_sign=True"):
        sign(unsigned, wallet)
    with pytest.raises(PaymentError, match="allow_sign=True"):
        sign(unsigned, wallet, allow_sign=False)


def test_sign_rejects_resign_and_foreign_inputs() -> None:
    wallet = _wallet()
    unsigned = _vector_unsigned()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        signed = sign(unsigned, wallet, allow_sign=True)
    with pytest.raises(PaymentError):
        sign(signed, wallet, allow_sign=True)  # type: ignore[arg-type]
    foreign = build(
        [
            {
                "txid": FAKE_TXID,
                "vout": 0,
                "amount_duffs": 100_000,
                "address": _wallet().receiving_address(9),
            }
        ],
        [{"address": wallet.receiving_address(1), "amount_duffs": 99_000}],
    )
    other = from_mnemonic("zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong", passphrase="TREZOR")
    with pytest.raises(PaymentError, match="holds no receiving key"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            sign(foreign, other, allow_sign=True)


def test_sign_rejects_network_mismatch() -> None:
    wallet = _wallet(network="regtest")
    unsigned = _vector_unsigned(network="mainnet")
    with pytest.raises(PaymentError, match="does not match"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            sign(unsigned, wallet, allow_sign=True)


def test_p2sh_sign_fence_with_deferral() -> None:
    wallet = _wallet()
    unsigned = UnsignedTx(
        inputs=(
            {
                "txid": FAKE_TXID,
                "vout": 0,
                "amount_duffs": 100_000,
                "address": MAINNET_P2SH_SEQ,
            },  # type: ignore[dict-item]
        ),
        outputs=(
            {
                "address": wallet.receiving_address(1),
                "amount_duffs": 99_000,
            },  # type: ignore[dict-item]
        ),
        fee_duffs=1_000,
        network="mainnet",
    )
    with pytest.raises(PaymentError, match="deferred beyond v0.1"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            sign(unsigned, wallet, allow_sign=True)


# --- Submit ------------------------------------------------------------------


def test_submit_refuses_unsigned_with_zero_hits(fake_node: int) -> None:
    unsigned = _vector_unsigned()
    with pytest.raises(PaymentError, match="unsigned"):
        submit(unsigned, _client(fake_node))  # type: ignore[arg-type]
    assert _STATE.received == []


def test_submit_refuses_malformed_with_zero_hits(fake_node: int) -> None:
    unsigned = _vector_unsigned()
    for bad_hex in ("", "abc", "zz" * 100, "00" * 10):
        broken = SignedTx(unsigned=unsigned, raw_hex=bad_hex, txid="00" * 32)
        with pytest.raises(PaymentError, match="malformed|unsigned"):
            submit(broken, _client(fake_node))
    assert _STATE.received == []


def test_submit_refuses_network_mismatch_with_zero_hits(fake_node: int) -> None:
    regtest_wallet = _wallet(network="regtest")
    regtest_unsigned = _vector_unsigned(network="regtest")
    assert regtest_wallet.receiving_address(0) == regtest_unsigned.inputs[0].address
    mismatched = SignedTx(
        unsigned=regtest_unsigned.model_copy(update={"network": "mainnet"}),
        raw_hex="ab" * 200,
        txid="ab" * 32,
    )
    with pytest.raises(PaymentError, match="is for"):
        submit(mismatched, _client(fake_node))
    assert _STATE.received == []


def test_submit_success_returns_node_txid(fake_node: int) -> None:
    wallet = _wallet()
    unsigned = _vector_unsigned()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        signed = sign(unsigned, wallet, allow_sign=True)
    _STATE.routes["sendrawtransaction"] = ("ok", signed.txid)
    assert submit(signed, _client(fake_node)) == signed.txid
    assert len(_STATE.received) == 1
    seen = _STATE.received[0]
    assert seen["method"] == "sendrawtransaction"
    assert seen["params"] == [signed.raw_hex]


def test_node_rejection_maps_to_payment_error_chained(fake_node: int) -> None:
    wallet = _wallet()
    unsigned = _vector_unsigned()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        signed = sign(unsigned, wallet, allow_sign=True)
    _STATE.routes["sendrawtransaction"] = ("err", -26, "66: min relay fee not met")
    with pytest.raises(PaymentError, match="rejected") as exc_info:
        submit(signed, _client(fake_node))
    assert isinstance(exc_info.value.__cause__, RpcError)
    assert exc_info.value.__cause__.code == -26  # type: ignore[union-attr]


# --- Confirm status ------------------------------------------------------------


def _route_finality(tx_result: Any, lock: tuple[str, Any] | None, header: Any = None) -> None:
    _STATE.routes["gettransaction"] = ("ok", tx_result)
    if lock is None:
        _STATE.routes["getbestchainlock"] = ("err", -32601, "Method not found")
    else:
        _STATE.routes["getbestchainlock"] = lock
    if header is None:
        _STATE.routes["getblockheader"] = ("err", -5, "Block not found")
    else:
        _STATE.routes["getblockheader"] = ("ok", header)


def test_confirm_status_locked_payment(fake_node: int) -> None:
    _route_finality(
        {
            "confirmations": 6,
            "instantlock": True,
            "blockhash": "aa" * 32,
            "txid": FAKE_TXID,
        },
        ("ok", {"height": 900, "blockhash": "bb" * 32}),
        {"height": 895, "hash": "aa" * 32},
    )
    status = confirm_status(FAKE_TXID, _client(fake_node))
    assert status == ConfirmationStatus(
        confirmations=6, instantlock=True, chainlocked=True, chainlock_height=900
    )


def test_confirm_status_unconfirmed_reports_tip_lock(fake_node: int) -> None:
    _route_finality({"confirmations": 0}, ("ok", {"height": 900}))
    status = confirm_status(FAKE_TXID, _client(fake_node))
    assert (status.confirmations, status.instantlock) == (0, False)
    assert (status.chainlocked, status.chainlock_height) == (False, 900)


def test_confirm_status_pre_chainlock_era(fake_node: int) -> None:
    _route_finality({"confirmations": 2, "blockhash": "aa" * 32}, None)
    status = confirm_status(FAKE_TXID, _client(fake_node))
    assert status.chainlocked is False
    assert status.chainlock_height is None
    assert status.confirmations == 2


def test_confirm_status_instantlock_internal_counts(fake_node: int) -> None:
    _route_finality({"confirmations": 1, "instantlock_internal": True}, None)
    assert confirm_status(FAKE_TXID, _client(fake_node)).instantlock is True


def test_confirm_status_tx_above_lock_not_chainlocked(fake_node: int) -> None:
    _route_finality(
        {"confirmations": 1, "blockhash": "aa" * 32},
        ("ok", {"height": 900}),
        {"height": 905},
    )
    status = confirm_status(FAKE_TXID, _client(fake_node))
    assert status.chainlocked is False
    assert status.chainlock_height == 900


def test_confirm_status_bad_txid_refused_pre_network(fake_node: int) -> None:
    for bad in ("", "zz", "ab" * 32 + "x"):
        with pytest.raises(PaymentError):
            confirm_status(bad, _client(fake_node))
    assert _STATE.received == []


# --- Wording guard + redaction -------------------------------------------------


def test_module_wording_guard() -> None:
    text = Path(tx_module.__file__ or "").read_text(encoding="utf-8")
    dip_lines = [line for line in text.splitlines() if "DIP0024" in line]
    assert dip_lines, "DIP0024 scope must be documented"
    for line in dip_lines:  # DIP0024 is quorum rotation — never the inventor of finality
        assert "rotation" in line, f"banned attribution risk: {line!r}"
    assert "1088640" in text  # ChainLock activation height recorded
    assert "v23.1.8" in text  # pinned source recorded


def test_review_and_errors_carry_no_secrets(tmp_path: Path) -> None:
    wallet = from_mnemonic(
        "abandon abandon abandon abandon abandon abandon "
        "abandon abandon abandon abandon abandon about",
        passphrase=SENTINEL_PASSPHRASE,
    )
    unsigned = build(
        [
            {
                "txid": FAKE_TXID,
                "vout": 0,
                "amount_duffs": 100_000,
                "address": wallet.receiving_address(0),
            }
        ],
        [{"address": wallet.receiving_address(1), "amount_duffs": 99_000}],
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        signed = sign(unsigned, wallet, allow_sign=True)
        priv_hex = wallet.private_key_bytes(0, allow_sign=True).hex()
    try:
        submit(unsigned, None)  # type: ignore[arg-type]
    except PaymentError as exc:
        refusal = str(exc)
    probe = tmp_path / "review.txt"
    probe.write_text(
        json.dumps(review(unsigned)) + json.dumps(review(signed)) + refusal, encoding="utf-8"
    )
    haystack = probe.read_text(encoding="utf-8") + repr(unsigned) + repr(signed) + str(signed)
    assert SENTINEL_PASSPHRASE not in haystack
    assert priv_hex not in haystack
    assert wallet._seed.hex() not in haystack
    assert validate_address(wallet.receiving_address(0)).valid


# --- Hybrid regtest --------------------------------------------------------------


@pytest.mark.hybrid
def test_regtest_fund_sign_submit_confirm(dashd_regtest: Any) -> None:
    from decimal import Decimal

    rpc = dashd_regtest["rpc"]
    mine = dashd_regtest["mine"]
    try:
        rpc.call("createwallet", "phase3")
    except RpcError:
        pass  # already created earlier in this session
    node_addr = rpc.call("getnewaddress")
    mine(101)  # mature at least one coinbase (100-confirmation maturity)
    assert rpc.call("getbalance") > 0
    candidates = [
        entry
        for entry in rpc.call("listunspent", 1, 9999999, [node_addr])
        if entry.get("spendable", True)
    ]
    assert candidates, "regtest funding produced no spendable UTXO"
    utxo = max(candidates, key=lambda entry: float(entry["amount"]))
    amount_duffs = int(Decimal(str(utxo["amount"])) * 100_000_000)
    fee = 5_000
    assert amount_duffs > fee
    wallet = from_mnemonic(
        "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong",
        passphrase="TREZOR",
        network="regtest",
    )
    dest = wallet.receiving_address(0)
    assert rpc.call("validateaddress", dest)["isvalid"] is True
    unsigned = build(
        [
            {
                "txid": utxo["txid"],
                "vout": utxo["vout"],
                "amount_duffs": amount_duffs,
                "address": node_addr,
            }
        ],
        [{"address": dest, "amount_duffs": amount_duffs - fee}],
        network="regtest",
    )
    assert review(unsigned)["fee_duffs"] == fee
    with pytest.warns(UserWarning, match="watch-only"):
        signed = sign(unsigned, wallet, allow_sign=True)
    decoded = rpc.call("decoderawtransaction", signed.raw_hex)
    assert decoded["version"] == 2
    expected_script = "76a914" + b58check_decode(dest)[1:].hex() + "88ac"
    assert decoded["vout"][0]["scriptPubKey"]["hex"] == expected_script
    assert submit(signed, rpc) == signed.txid
    mine(1)
    status = confirm_status(signed.txid, rpc)
    assert status.confirmations >= 1
    assert isinstance(status.instantlock, bool)
    assert isinstance(status.chainlocked, bool)
    assert status.chainlock_height is None or isinstance(status.chainlock_height, int)
