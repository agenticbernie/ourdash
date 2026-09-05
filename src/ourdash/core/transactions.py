"""Offline P2PKH payment pipeline: build → review → sign → submit, plus finality reads.

Dash here is Dash crypto from dash.org — not Plotly Dash.

Pipeline: :func:`build` assembles an :class:`UnsignedTx` fully offline;
:func:`review` renders a secret-free human-readable summary dict;
:func:`sign` adds local ECDSA signatures with an explicit warned opt-in;
:func:`submit` broadcasts a :class:`SignedTx` through Phase 1 transport
(:meth:`ourdash.core.rpc.DashRPC.call` ``sendrawtransaction``). Unsigned or
malformed payloads are refused with :class:`ourdash.errors.PaymentError`
BEFORE any network call. :func:`confirm_status` reports per-payment finality.

Serialization: v0.1 emits only normal (non-special) transactions — version 2,
type 0 (``CTransaction::CURRENT_VERSION``), no extra payload — so the wire
bytes match the canonical layout: ``int32 version|type`` then inputs, outputs,
``uint32 locktime`` (Dash Core v23.1.8 ``src/primitives/transaction.h``,
retrieved 2026-09-05; no ``dashd``/``dash-cli`` binary exists in this
environment, so the ``dash-cli help`` cross-check is recorded as pending).
Inputs spend P2PKH outputs with ``SIGHASH_ALL`` ECDSA signatures; the txid is
the byte-reversed double-SHA-256 of the signed bytes.

Special-transaction type registry (informational — v0.1 never emits these;
source: Dash Core v23.1.8 ``src/primitives/transaction.h`` ``Transaction
types`` enum, retrieved 2026-09-05): 0 normal, 1 provider-register, 2
provider-update-service, 3 provider-update-registrar, 4 provider-update-revoke,
5 coinbase, 6 quorum-commitment, 7 MNHF-signal, 8 asset-lock, 9 asset-unlock.

Finality wording: InstantSend exists in an original form (Transaction Locking
via masternode votes) and a current deterministic form built on Long-Living
Masternode Quorums (LLMQs). ChainLocks (blocks locked by LLMQs, active on
mainnet since block 1088640, June 2019 — no reorg below a locked block) rest
on the same quorum technology. DIP0024 defines LLMQ quorum rotation only:
DIP0024 quorum rotation did not invent InstantSend, and DIP0024 quorum
rotation did not invent ChainLocks either.
"""

from __future__ import annotations

import hashlib
import logging
import struct
import warnings
from collections.abc import Mapping, Sequence
from typing import Any, Final

from ecdsa import SECP256k1, SigningKey  # type: ignore[import-untyped]
from ecdsa.util import sigencode_der  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from ourdash.core.addresses import validate_address
from ourdash.core.rpc import DashRPC
from ourdash.core.wallet import CUSTODY_WARNING, Wallet
from ourdash.errors import PaymentError, RpcError
from ourdash.redact import RedactionFilter, redact
from ourdash.utils import b58check_decode, sha256d

logger = logging.getLogger(__name__)
logger.addFilter(RedactionFilter())

_NETWORKS: Final[tuple[str, ...]] = ("mainnet", "testnet", "regtest", "devnet")

_TX_VERSION: Final[int] = 2
_TX_TYPE_NORMAL: Final[int] = 0
_SIGHASH_ALL: Final[int] = 1
_SEQUENCE_FINAL: Final[int] = 0xFFFFFFFF
_LOCKTIME: Final[int] = 0
_MAX_VOUT: Final[int] = 0xFFFFFFFF
_MIN_SIGNED_HEX_LEN: Final[int] = 120  # far below any real P2PKH tx; catches garbage
_KEY_SCAN_CAP: Final[int] = 1024  # max receiving indexes scanned when matching inputs
_EST_SIGNED_BYTES_PER_INPUT: Final[int] = 107  # ~72-byte DER sig + 33-byte pubkey + pushes
_CHAINLOCK_FORK_HEIGHT: Final[int] = 1088640  # ChainLocks active on mainnet since here


def _varint(n: int) -> bytes:
    if n < 0xFD:
        return struct.pack("<B", n)
    if n <= 0xFFFF:
        return b"\xfd" + struct.pack("<H", n)
    if n <= 0xFFFFFFFF:
        return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)


def _push(data: bytes) -> bytes:
    if len(data) >= 76:
        raise PaymentError("push data too long for a standard P2PKH script")
    return struct.pack("<B", len(data)) + data


def _p2pkh_script(address: str) -> bytes:
    """Rebuild the 25-byte P2PKH scriptPubKey for an address (kind pre-checked)."""
    payload = b58check_decode(address)
    return b"\x76\xa9\x14" + payload[1:21] + b"\x88\xac"


class TxInput(BaseModel):
    """One funding outpoint: previous txid (big-endian hex), output index, value, owner."""

    model_config = ConfigDict(frozen=True)

    txid: str
    vout: int
    amount_duffs: int
    address: str


class TxOutput(BaseModel):
    """One payment destination: P2PKH address plus value in duffs."""

    model_config = ConfigDict(frozen=True)

    address: str
    amount_duffs: int


class UnsignedTx(BaseModel):
    """Offline, unsigned payment. Inspect with :func:`review`; sign with :func:`sign`."""

    model_config = ConfigDict(frozen=True)

    inputs: tuple[TxInput, ...]
    outputs: tuple[TxOutput, ...]
    fee_duffs: int
    network: str

    def unsigned_hex(self) -> str:
        """Deterministic serialization with empty scriptSigs (same inputs → same hex)."""
        return _serialize(self.inputs, [b""] * len(self.inputs), self.outputs).hex()

    def __repr__(self) -> str:
        return str(redact(super().__repr__()))

    def __str__(self) -> str:
        return repr(self)


class SignedTx(BaseModel):
    """Signed payment: the reviewed :class:`UnsignedTx` plus broadcast bytes and txid."""

    model_config = ConfigDict(frozen=True)

    unsigned: UnsignedTx
    raw_hex: str
    txid: str

    @property
    def inputs(self) -> tuple[TxInput, ...]:
        return self.unsigned.inputs

    @property
    def outputs(self) -> tuple[TxOutput, ...]:
        return self.unsigned.outputs

    @property
    def fee_duffs(self) -> int:
        return self.unsigned.fee_duffs

    @property
    def network(self) -> str:
        return self.unsigned.network

    def __repr__(self) -> str:
        return str(redact(super().__repr__()))

    def __str__(self) -> str:
        return repr(self)


class ConfirmationStatus(BaseModel):
    """Per-payment finality: confirmations plus InstantSend/ChainLock state."""

    model_config = ConfigDict(frozen=True)

    confirmations: int
    instantlock: bool
    chainlocked: bool
    chainlock_height: int | None

    def __repr__(self) -> str:
        return str(redact(super().__repr__()))

    def __str__(self) -> str:
        return repr(self)


def _checked_address(address: object, network: str, role: str) -> str:
    """Validate one P2PKH address for ``network``; raise :class:`PaymentError` otherwise."""
    if not isinstance(address, str) or not address:
        raise PaymentError(f"{role} address must be a non-empty string")
    info = validate_address(address, expected_network=network)
    if not info.valid:
        if info.reason == "wrong_network":
            raise PaymentError(f"{role} address {address!r} is for {info.network}, not {network!r}")
        raise PaymentError(f"{role} address {address!r} is invalid ({info.reason})")
    if info.kind != "p2pkh":
        raise PaymentError(
            f"P2PKH-only signer (v0.1): {role} uses {info.kind} — "
            "multisig/script support is deferred beyond v0.1"
        )
    return address


def _checked_amount(amount: object, role: str) -> int:
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise PaymentError(f"{role} amount must be a positive int of duffs")
    return amount


def build(
    inputs: Sequence[TxInput | Mapping[str, Any]],
    outputs: Sequence[TxOutput | Mapping[str, Any]],
    network: str = "mainnet",
) -> UnsignedTx:
    """Assemble an :class:`UnsignedTx` fully offline (no network use).

    Raises :class:`ourdash.errors.PaymentError` for empty/duplicate inputs,
    non-positive amounts, invalid or non-P2PKH addresses, network mismatches,
    or outputs exceeding inputs.
    """
    if network not in _NETWORKS:
        raise PaymentError(f"unknown network {network!r}")
    if not inputs:
        raise PaymentError("cannot build a transaction with no inputs")
    if not outputs:
        raise PaymentError("cannot build a transaction with no outputs")
    checked_inputs = tuple(
        TxInput.model_validate(item) if not isinstance(item, TxInput) else item for item in inputs
    )
    checked_outputs = tuple(
        TxOutput.model_validate(item) if not isinstance(item, TxOutput) else item
        for item in outputs
    )
    seen: set[tuple[str, int]] = set()
    total_in = 0
    for position, item in enumerate(checked_inputs):
        role = f"input #{position}"
        if not isinstance(item.txid, str) or len(item.txid) != 64:
            raise PaymentError(f"{role} txid must be 64 hex chars")
        try:
            bytes.fromhex(item.txid)
        except ValueError:
            raise PaymentError(f"{role} txid must be 64 hex chars") from None
        if not isinstance(item.vout, int) or not 0 <= item.vout <= _MAX_VOUT:
            raise PaymentError(f"{role} vout out of range")
        _checked_amount(item.amount_duffs, role)
        _checked_address(item.address, network, role)
        key = (item.txid.lower(), item.vout)
        if key in seen:
            raise PaymentError(f"{role} spends a duplicate outpoint")
        seen.add(key)
        total_in += item.amount_duffs
    total_out = 0
    for position, out_item in enumerate(checked_outputs):
        role = f"output #{position}"
        _checked_amount(out_item.amount_duffs, role)
        _checked_address(out_item.address, network, role)
        total_out += out_item.amount_duffs
    fee = total_in - total_out
    if fee < 0:
        raise PaymentError(
            f"outputs exceed inputs by {-fee} duffs (in={total_in}, out={total_out})"
        )
    logger.debug(
        "built unsigned tx network=%s inputs=%d outputs=%d fee=%d",
        network,
        len(checked_inputs),
        len(checked_outputs),
        fee,
    )
    return UnsignedTx(
        inputs=checked_inputs, outputs=checked_outputs, fee_duffs=fee, network=network
    )


def _serialize(
    inputs: Sequence[TxInput], scripts: Sequence[bytes], outputs: Sequence[TxOutput]
) -> bytes:
    """Serialize a normal (version 2, type 0) tx with one script per input."""
    out = struct.pack("<i", (_TX_VERSION | (_TX_TYPE_NORMAL << 16)))
    out += _varint(len(inputs))
    for item, script in zip(inputs, scripts, strict=True):
        out += bytes.fromhex(item.txid)[::-1]
        out += struct.pack("<I", item.vout)
        out += _varint(len(script)) + script
        out += struct.pack("<I", _SEQUENCE_FINAL)
    out += _varint(len(outputs))
    for out_item in outputs:
        out += struct.pack("<q", out_item.amount_duffs)
        script = _p2pkh_script(out_item.address)
        out += _varint(len(script)) + script
    out += struct.pack("<I", _LOCKTIME)
    return out


def _sighash(unsigned_tx: UnsignedTx, input_index: int) -> bytes:
    """Double-SHA-256 digest to sign for one input (SIGHASH_ALL, P2PKH scriptCode)."""
    scripts = [
        _p2pkh_script(item.address) if pos == input_index else b""
        for pos, item in enumerate(unsigned_tx.inputs)
    ]
    preimage = _serialize(unsigned_tx.inputs, scripts, unsigned_tx.outputs)
    preimage += struct.pack("<I", _SIGHASH_ALL)
    return sha256d(preimage)


def review(tx: UnsignedTx | SignedTx) -> dict[str, Any]:
    """Return a secret-free human-readable summary of an unsigned or signed payment."""
    if isinstance(tx, SignedTx):
        unsigned, kind, txid = tx.unsigned, "signed", tx.txid
    elif isinstance(tx, UnsignedTx):
        unsigned, kind, txid = tx, "unsigned", None
    else:
        raise PaymentError(f"review() needs an UnsignedTx or SignedTx, got {type(tx).__name__}")
    total_in = sum(item.amount_duffs for item in unsigned.inputs)
    total_out = sum(item.amount_duffs for item in unsigned.outputs)
    est_signed_vbytes = len(bytes.fromhex(unsigned.unsigned_hex())) + (
        _EST_SIGNED_BYTES_PER_INPUT * len(unsigned.inputs)
    )
    summary: dict[str, Any] = {
        "kind": kind,
        "network": unsigned.network,
        "input_count": len(unsigned.inputs),
        "output_count": len(unsigned.outputs),
        "inputs": [
            {
                "txid": item.txid,
                "vout": item.vout,
                "amount_duffs": item.amount_duffs,
                "address": item.address,
            }
            for item in unsigned.inputs
        ],
        "destinations": [
            {"address": item.address, "amount_duffs": item.amount_duffs}
            for item in unsigned.outputs
        ],
        "total_in_duffs": total_in,
        "total_out_duffs": total_out,
        "fee_duffs": unsigned.fee_duffs,
        "fee_rate_duffs_per_vbyte": unsigned.fee_duffs / est_signed_vbytes,
        "txid": txid,
    }
    redacted: dict[str, Any] = redact(summary)
    return redacted


def _find_key_index(unsigned_tx: UnsignedTx, wallet: Wallet) -> dict[int, int]:
    """Map each input position to the wallet receiving index holding its address."""
    known: dict[str, int] = {}
    unknown = list(range(len(unsigned_tx.inputs)))
    mapping: dict[int, int] = {}
    for index in range(_KEY_SCAN_CAP):
        if not unknown:
            break
        address = wallet.receiving_address(index)
        if address in known:
            continue
        known[address] = index
        for position in list(unknown):
            if unsigned_tx.inputs[position].address == address:
                mapping[position] = index
                unknown.remove(position)
    if unknown:
        missing = ", ".join(f"input #{pos}" for pos in unknown)
        raise PaymentError(
            f"wallet holds no receiving key for {missing} (scanned {_KEY_SCAN_CAP} indexes)"
        )
    return mapping


def sign(unsigned_tx: UnsignedTx, wallet: Wallet, *, allow_sign: bool = False) -> SignedTx:
    """Locally sign every input of ``unsigned_tx`` with ``wallet`` (explicit opt-in only).

    Requires ``allow_sign=True`` and always emits the custody ``UserWarning``.
    Only P2PKH inputs owned by ``wallet`` on the same network are signable;
    anything else raises :class:`ourdash.errors.PaymentError`.
    """
    if isinstance(unsigned_tx, SignedTx) or not isinstance(unsigned_tx, UnsignedTx):
        raise PaymentError("sign() needs an UnsignedTx — this payment is already signed")
    if allow_sign is not True:
        raise PaymentError(
            "refusing to sign without explicit allow_sign=True "
            "(wallet is watch-only by default — review first)"
        )
    if wallet.network != unsigned_tx.network:
        raise PaymentError(
            f"wallet network {wallet.network!r} does not match "
            f"transaction network {unsigned_tx.network!r}"
        )
    for position, item in enumerate(unsigned_tx.inputs):
        _checked_address(item.address, unsigned_tx.network, f"input #{position}")
    warnings.warn(CUSTODY_WARNING, UserWarning, stacklevel=2)
    key_index = _find_key_index(unsigned_tx, wallet)
    scripts: list[bytes] = []
    # private_key_bytes() warns on every call; sign() already warned once above,
    # so the per-input warnings are suppressed here to keep one warning per signing.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        key_material = [
            (
                wallet.private_key_bytes(key_index[position], allow_sign=True),
                wallet.public_key_bytes(key_index[position]),
            )
            for position in range(len(unsigned_tx.inputs))
        ]
    for position, (priv, pub) in enumerate(key_material):
        digest = _sighash(unsigned_tx, position)
        signature = SigningKey.from_secret_exponent(
            int.from_bytes(priv, "big"), curve=SECP256k1
        ).sign_digest_deterministic(digest, hashfunc=hashlib.sha256, sigencode=sigencode_der)
        scripts.append(_push(signature + b"\x01") + _push(pub))
    raw = _serialize(unsigned_tx.inputs, scripts, unsigned_tx.outputs)
    txid = sha256d(raw)[::-1].hex()
    logger.debug("signed tx network=%s inputs=%d txid=%s", unsigned_tx.network, len(scripts), txid)
    return SignedTx(unsigned=unsigned_tx, raw_hex=raw.hex(), txid=txid)


def _assert_submittable(tx: SignedTx) -> None:
    """Offline pre-network refusal checks. Raises :class:`PaymentError` before any RPC."""
    if isinstance(tx, UnsignedTx) or not isinstance(tx, SignedTx):
        raise PaymentError(
            "refusing to submit an unsigned transaction: "
            "build → review → sign first, then submit the SignedTx"
        )
    if (
        not isinstance(tx.raw_hex, str)
        or not tx.raw_hex
        or len(tx.raw_hex) < _MIN_SIGNED_HEX_LEN
        or len(tx.raw_hex) % 2 != 0
    ):
        raise PaymentError(
            "refusing to submit malformed raw transaction "
            "(must be non-empty even-length hex of a plausible length)"
        )
    try:
        bytes.fromhex(tx.raw_hex)
    except ValueError:
        raise PaymentError("refusing to submit malformed raw transaction (not valid hex)") from None
    for position, item in enumerate(tx.unsigned.inputs):
        _checked_address(item.address, tx.network, f"input #{position}")
    for position, out_item in enumerate(tx.unsigned.outputs):
        _checked_address(out_item.address, tx.network, f"output #{position}")


def submit(tx: SignedTx, rpc: DashRPC) -> str:
    """Broadcast a :class:`SignedTx` via ``sendrawtransaction``; return the node txid.

    Unsigned/malformed/network-mismatched payloads raise
    :class:`ourdash.errors.PaymentError` BEFORE any network call. A node
    rejection is mapped to :class:`ourdash.errors.PaymentError` chained from
    the :class:`ourdash.errors.RpcError`.
    """
    _assert_submittable(tx)
    try:
        result = rpc.call("sendrawtransaction", tx.raw_hex)
    except RpcError as exc:
        raise PaymentError(f"node rejected the transaction: {exc}") from exc
    if not isinstance(result, str) or result != tx.txid:
        raise PaymentError("node returned an unexpected txid for the submitted transaction")
    return result


def confirm_status(txid: str, rpc: DashRPC) -> ConfirmationStatus:
    """Report per-payment finality for ``txid`` (confirmations + IS/ChainLock state).

    Reads ``gettransaction`` (``confirmations``, ``instantlock`` /
    ``instantlock_internal``) and ``getbestchainlock`` (best locked height; a
    confirmed payment at or below that height is chainlocked). A node that
    predates ChainLocks — or has no lock yet — yields ``chainlocked=False`` /
    ``chainlock_height=None`` instead of an error (pre-ChainLock-era semantics).
    """
    if not isinstance(txid, str) or len(txid) != 64:
        raise PaymentError("txid must be 64 hex chars")
    try:
        bytes.fromhex(txid)
    except ValueError:
        raise PaymentError("txid must be 64 hex chars") from None
    node_tx = rpc.call("gettransaction", txid)
    if not isinstance(node_tx, Mapping):
        raise RpcError("gettransaction returned a malformed response")
    confirmations = int(node_tx.get("confirmations", 0))
    instantlock = bool(node_tx.get("instantlock", False)) or bool(
        node_tx.get("instantlock_internal", False)
    )
    try:
        best_lock = rpc.call("getbestchainlock")
    except RpcError:
        return ConfirmationStatus(
            confirmations=confirmations,
            instantlock=instantlock,
            chainlocked=False,
            chainlock_height=None,
        )
    lock_height = best_lock.get("height") if isinstance(best_lock, Mapping) else None
    if not isinstance(lock_height, int) or lock_height < 0:
        return ConfirmationStatus(
            confirmations=confirmations,
            instantlock=instantlock,
            chainlocked=False,
            chainlock_height=None,
        )
    chainlocked = False
    blockhash = node_tx.get("blockhash")
    if confirmations > 0 and isinstance(blockhash, str) and blockhash:
        try:
            header = rpc.call("getblockheader", blockhash)
        except RpcError:
            header = None
        tx_height = header.get("height") if isinstance(header, Mapping) else None
        chainlocked = isinstance(tx_height, int) and 0 <= tx_height <= lock_height
    return ConfirmationStatus(
        confirmations=confirmations,
        instantlock=instantlock,
        chainlocked=chainlocked,
        chainlock_height=lock_height,
    )
