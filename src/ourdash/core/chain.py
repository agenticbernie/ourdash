"""Typed Core read facade: chain info, blocks, transactions, balances, addresses.

Dash here is Dash crypto from dash.org — not Plotly Dash.

One typed read surface over the developer's own node. Every function takes a
:class:`ourdash.core.rpc.DashRPC` and returns a pydantic model with a
:meth:`to_dict` plain-object view (stdlib types only) for analysts' own
tooling. Node error objects propagate as the Phase 1 taxonomy
(:class:`ourdash.errors.RpcError` with the node code preserved); malformed
node payloads raise :class:`ourdash.errors.RpcError` chained from the
validation failure. Unknown extras in node responses are ignored; the
documented fields below are required.

Wallet selection: every wallet-aware function (``get_transaction``,
``get_balance``, ``get_new_address``) accepts ``wallet: str | None``. When
set, the call runs against a client bound to that wallet's ``-rpcwallet``
endpoint, built internally from the passed client's config — the caller's
client is never mutated. An unknown wallet surfaces the node's error as
:class:`ourdash.errors.RpcError` with its code preserved.

Method allowlist (Dash Core v23.1.8 ``dash-cli help``, retrieved 2026-09-05):
``getblockchaininfo``, ``getblockhash``, ``getblock``, ``getrawtransaction``,
``gettransaction``, ``getbalances``, ``getbalance``,
``getunconfirmedbalance``, ``getnewaddress``, ``getchaintips``,
``masternode list``, ``getbestchainlock``, ``getblockcount``. No
``dashd``/``dash-cli`` binary exists in this environment, so the allowlist is
pinned from the v23.1.8 sources/docs rather than a live ``dash-cli help``
dump; only the methods above are called, and only the documented fields are
asserted.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from ourdash.core.addresses import validate_address
from ourdash.core.rpc import DashRPC
from ourdash.errors import RpcError
from ourdash.redact import RedactionFilter

logger = logging.getLogger(__name__)
logger.addFilter(RedactionFilter())


def _bound(rpc: DashRPC, wallet: str | None) -> DashRPC:
    """Return ``rpc`` or a copy bound to ``wallet``'s ``-rpcwallet`` endpoint."""
    if wallet is None:
        return rpc
    return DashRPC(replace(rpc.config, wallet=wallet))


def _mapping(value: Any, method: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RpcError(f"{method} returned a malformed response")
    return value


class BlockchainInfo(BaseModel):
    """Chain state: name, height, sync progress, difficulty."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    chain: str
    blocks: int
    headers: int
    bestblockhash: str
    difficulty: float
    verificationprogress: float

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class BlockInfo(BaseModel):
    """One block: hash, height, time, transaction list/count, ChainLock flag."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    hash: str
    height: int
    time: int
    txids: list[str]
    tx_count: int
    chainlock: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class TransactionInfo(BaseModel):
    """One transaction: confirmations, amounts, InstantSend flag."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    txid: str
    confirmations: int = 0
    amount: float | None = None
    fee: float | None = None
    instantlock: bool = False
    blockhash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class Balance(BaseModel):
    """Wallet balance split: confirmed vs unconfirmed (plus immature mining)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    confirmed: float
    unconfirmed: float = 0.0
    immature: float | None = None
    wallet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


def get_blockchain_info(rpc: DashRPC) -> BlockchainInfo:
    """Read chain state (height, chain name, progress, difficulty)."""
    data = _mapping(rpc.call("getblockchaininfo"), "getblockchaininfo")
    try:
        return BlockchainInfo(
            chain=data["chain"],
            blocks=int(data["blocks"]),
            headers=int(data["headers"]),
            bestblockhash=data["bestblockhash"],
            difficulty=float(data["difficulty"]),
            verificationprogress=float(data["verificationprogress"]),
        )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise RpcError(f"getblockchaininfo returned a malformed response: {exc}") from exc


def get_block(rpc: DashRPC, hash_or_height: str | int, verbosity: int = 1) -> BlockInfo:
    """Read one block by hash (64-hex) or by height (int or decimal string).

    Heights resolve via ``getblockhash`` first. ``verbosity`` 1 returns txids;
    2 returns full tx objects (reduced to their txids here). Verbosity 0
    (raw hex) is refused pre-network — use verbosity 1 or 2.
    """
    if isinstance(hash_or_height, bool):
        raise RpcError("block selector must be a hash string or a height int")
    if verbosity not in (1, 2):
        raise RpcError("get_block needs verbosity 1 or 2 (0 returns raw hex)")
    block_hash: str
    if isinstance(hash_or_height, int):
        resolved: Any = rpc.call("getblockhash", hash_or_height)
        if not isinstance(resolved, str) or not resolved:
            raise RpcError("getblockhash returned a malformed response")
        block_hash = resolved
    elif isinstance(hash_or_height, str) and hash_or_height.isdigit():
        # Decimal-string height (a 64-char all-digit hash is ~impossible).
        resolved = rpc.call("getblockhash", int(hash_or_height))
        if not isinstance(resolved, str) or not resolved:
            raise RpcError("getblockhash returned a malformed response")
        block_hash = resolved
    elif isinstance(hash_or_height, str) and hash_or_height:
        block_hash = hash_or_height
    else:
        raise RpcError("block selector must be a hash string or a height int")
    data = _mapping(rpc.call("getblock", block_hash, verbosity), "getblock")
    raw_tx = data.get("tx", [])
    if not isinstance(raw_tx, list):
        raise RpcError("getblock returned a malformed response")
    txids: list[str] = []
    for entry in raw_tx:
        txid: Any = entry.get("txid", entry.get("hash")) if isinstance(entry, Mapping) else entry
        if not isinstance(txid, str) or not txid:
            raise RpcError("getblock returned a malformed response")
        txids.append(txid)
    raw_count = data.get("nTx")
    tx_count = int(raw_count) if isinstance(raw_count, int) else len(txids)
    lock_raw = data.get("chainlock", data.get("chainLock"))
    chainlock = bool(lock_raw) if lock_raw is not None else None
    try:
        return BlockInfo(
            hash=data["hash"],
            height=int(data["height"]),
            time=int(data["time"]),
            txids=txids,
            tx_count=tx_count,
            chainlock=chainlock,
        )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise RpcError(f"getblock returned a malformed response: {exc}") from exc


def _transaction_from_mapping(txid: str, data: Mapping[str, Any]) -> TransactionInfo:
    """Build a :class:`TransactionInfo` from either verbose shape.

    Accepts the ``getrawtransaction``-verbose shape and the wallet
    ``gettransaction`` shape (``instantlock`` / ``instantlock_internal``).
    """
    raw_confirmations = data.get("confirmations", 0)
    raw_amount = data.get("amount")
    raw_fee = data.get("fee")
    raw_blockhash = data.get("blockhash")
    try:
        return TransactionInfo(
            txid=str(data.get("txid", txid)),
            confirmations=int(raw_confirmations),
            amount=float(raw_amount) if raw_amount is not None else None,
            fee=float(raw_fee) if raw_fee is not None else None,
            instantlock=bool(data.get("instantlock", False))
            or bool(data.get("instantlock_internal", False)),
            blockhash=str(raw_blockhash) if raw_blockhash is not None else None,
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise RpcError(f"transaction payload is malformed: {exc}") from exc


def get_transaction(rpc: DashRPC, txid: str, wallet: str | None = None) -> TransactionInfo:
    """Read one transaction (amounts, fee, confirmations, InstantSend flag).

    With ``wallet`` set, reads the wallet ``gettransaction`` view on that
    wallet's endpoint. Without ``wallet``, tries verbose
    ``getrawtransaction`` (needs txindex for confirmed txs) and falls back to
    the default-wallet ``gettransaction`` view.
    """
    if not isinstance(txid, str) or len(txid) != 64:
        raise RpcError("txid must be 64 hex chars")
    try:
        bytes.fromhex(txid)
    except ValueError:
        raise RpcError("txid must be 64 hex chars") from None
    target = _bound(rpc, wallet)
    if wallet is not None:
        return _transaction_from_mapping(
            txid, _mapping(target.call("gettransaction", txid), "gettransaction")
        )
    try:
        raw: Any = target.call("getrawtransaction", txid, True)
    except RpcError as first:
        try:
            raw = target.call("gettransaction", txid)
        except RpcError:
            raise first from None
    return _transaction_from_mapping(txid, _mapping(raw, "getrawtransaction"))


def get_balance(rpc: DashRPC, wallet: str | None = None) -> Balance:
    """Read a wallet balance split (confirmed / unconfirmed / immature).

    Uses ``getbalances`` when the node offers it; older nodes fall back to
    ``getbalance`` plus ``getunconfirmedbalance``. Unbound (``wallet=None``)
    reads the node's default wallet view.
    """
    target = _bound(rpc, wallet)
    try:
        data = _mapping(target.call("getbalances"), "getbalances")
        mine = _mapping(data.get("mine"), "getbalances")
        try:
            return Balance(
                confirmed=float(mine["trusted"]),
                unconfirmed=float(mine.get("untrusted_pending", 0.0)),
                immature=float(mine["immature"]) if mine.get("immature") is not None else None,
                wallet=wallet,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise RpcError(f"getbalances returned a malformed response: {exc}") from exc
    except RpcError as first:
        if first.message and "malformed" in first.message:
            raise
        try:
            confirmed: Any = target.call("getbalance")
        except RpcError as second:
            raise second from first
        try:
            unconfirmed_raw: Any = target.call("getunconfirmedbalance")
        except RpcError:
            unconfirmed_raw = 0.0
        try:
            return Balance(
                confirmed=float(confirmed),
                unconfirmed=float(unconfirmed_raw),
                wallet=wallet,
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise RpcError(f"getbalance returned a malformed response: {exc}") from exc


def get_new_address(rpc: DashRPC, label: str | None = None, wallet: str | None = None) -> str:
    """Request a fresh receiving address (Phase-2-validated before return)."""
    target = _bound(rpc, wallet)
    result: Any = target.call("getnewaddress", label) if label else target.call("getnewaddress")
    if not isinstance(result, str) or not result:
        raise RpcError("getnewaddress returned a malformed response")
    info = validate_address(result)
    if not info.valid:
        raise RpcError(f"node returned an invalid address (reason={info.reason})")
    logger.debug("new address issued wallet=%s", wallet)
    return result
