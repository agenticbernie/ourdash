"""Network health reads over JSON-RPC: chain tips, masternode-list diffs, ChainLock tip.

Dash here is Dash crypto from dash.org — not Plotly Dash.

REST-vs-ZMQ split (hard v0.1 boundary): Dash Core's read-only HTTP REST
mechanism and its real-time ZMQ push-feed mechanism are two SEPARATE opt-in
mechanisms; both are trusted-network-only features — whether served from the
same port or a separate port (same-port-or-separate-port trusted-network-only
deployments) — and both carry user-visible warnings. v0.1 implements NEITHER
as a transport: there is no REST client and no ZMQ subscriber in this module
(and no new dependencies for either). This module exposes JSON-RPC helpers
only. Any future REST or ZMQ addition requires an explicit opt-in constructor
plus a trusted-network warning; removing this boundary wording breaks
``tests/test_network.py::test_rest_zmq_boundary_docstring``.

This module owns the ONLY global ChainLock-tip reader
(:func:`chainlock_tip_status`). Per-transaction finality
(:func:`ourdash.core.transactions.confirm_status`) is owned by Phase 3 and is
not modified here.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from ourdash.core.rpc import DashRPC
from ourdash.errors import RpcError
from ourdash.redact import RedactionFilter

logger = logging.getLogger(__name__)
logger.addFilter(RedactionFilter())


def _mapping(value: Any, method: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RpcError(f"{method} returned a malformed response")
    return value


class ChainTip(BaseModel):
    """One chain tip: height, hash, branch length, sync status."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    height: int
    hash: str
    branchlen: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class MasternodeDiff(BaseModel):
    """Masternode-list change between two snapshots (proTxHash identifiers)."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    added: list[str]
    removed: list[str]
    changed: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class ChainLockStatus(BaseModel):
    """Global ChainLock tip: locked height/hash plus lag behind the node tip."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    height: int
    blockhash: str
    behind_by: int

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


def get_chain_tips(rpc: DashRPC) -> list[ChainTip]:
    """Read ``getchaintips`` (each tip: height, hash, branch length, status)."""
    raw: Any = rpc.call("getchaintips")
    if not isinstance(raw, list):
        raise RpcError("getchaintips returned a malformed response")
    tips: list[ChainTip] = []
    for entry in raw:
        data = _mapping(entry, "getchaintips")
        try:
            tips.append(
                ChainTip(
                    height=int(data["height"]),
                    hash=data["hash"],
                    branchlen=int(data["branchlen"]),
                    status=data["status"],
                )
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise RpcError(f"getchaintips returned a malformed response: {exc}") from exc
    logger.debug("chain tips read count=%d", len(tips))
    return tips


def get_masternode_list(rpc: DashRPC) -> dict[str, Any]:
    """Read the full ``masternode list json`` snapshot keyed by proTxHash."""
    try:
        raw: Any = rpc.call("masternode", "list", "json")
    except RpcError as first:
        if first.code == -32601:  # pre-0.13 alias for the same snapshot
            raw = rpc.call("masternodelist", "json")
        else:
            raise
    data = _mapping(raw, "masternode list")
    return dict(data)


def diff_masternode_lists(before: Mapping[str, Any], after: Mapping[str, Any]) -> MasternodeDiff:
    """Diff two ``masternode list`` snapshots (e.g. taken at different heights).

    Identifiers are the deterministic proTxHash keys: ``added`` holds keys
    only in ``after``, ``removed`` keys only in ``before``, ``changed`` keys
    in both whose quorum-relevant entry differs. All three lists are sorted.
    """
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        raise RpcError("masternode snapshots must be mappings keyed by proTxHash")
    before_keys = set(before.keys())
    after_keys = set(after.keys())
    added = sorted(str(key) for key in after_keys - before_keys)
    removed = sorted(str(key) for key in before_keys - after_keys)
    changed = sorted(str(key) for key in before_keys & after_keys if before[key] != after[key])
    return MasternodeDiff(added=added, removed=removed, changed=changed)


def masternode_list_diff(
    rpc: DashRPC, base_snapshot: Mapping[str, Any] | None = None
) -> MasternodeDiff:
    """Diff the live masternode list against ``base_snapshot`` (or empty).

    Capture ``base_snapshot`` via :func:`get_masternode_list` at a base
    height, mine/wait, then call again: the result reports which masternodes
    appeared, vanished, or changed entries between the two snapshots.
    """
    current = get_masternode_list(rpc)
    base: Mapping[str, Any] = base_snapshot if base_snapshot is not None else {}
    result = diff_masternode_lists(base, current)
    logger.debug(
        "masternode diff added=%d removed=%d changed=%d",
        len(result.added),
        len(result.removed),
        len(result.changed),
    )
    return result


def chainlock_tip_status(rpc: DashRPC) -> ChainLockStatus:
    """Read the global ChainLock tip (locked height/hash + lag behind tip)."""
    lock = _mapping(rpc.call("getbestchainlock"), "getbestchainlock")
    try:
        node_height_raw: Any = rpc.call("getblockcount")
        if not isinstance(node_height_raw, int) or isinstance(node_height_raw, bool):
            raise RpcError("getblockcount returned a malformed response")
        node_height = int(node_height_raw)
    except RpcError as exc:
        if "malformed" in str(exc):
            raise
        info = _mapping(rpc.call("getblockchaininfo"), "getblockchaininfo")
        try:
            node_height = int(info["blocks"])
        except (KeyError, TypeError, ValueError) as nested:
            raise RpcError(f"getblockchaininfo returned a malformed response: {nested}") from nested
    try:
        status = ChainLockStatus(
            height=int(lock["height"]),
            blockhash=lock["blockhash"],
            behind_by=node_height - int(lock["height"]),
        )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise RpcError(f"getbestchainlock returned a malformed response: {exc}") from exc
    logger.debug("chainlock tip height=%d behind_by=%d", status.height, status.behind_by)
    return status
