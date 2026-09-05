# Phase 4 — Core Reads + Network Health

Date: 04-09-26. Status: ⏳ PLANNED. Umbrella: `ourdash-sdk_PLAN_04-09-26.md`. Depends on: Phases 1–3 (✅ VERIFIED).

**Date**: 04-09-26
**Status**: ⏳ PLANNED
**Complexity**: COMPLEX (phase 4 of 6 in phase program)
SPEC criteria covered: **1** (local node read), **3** (multi-wallet), **9** (network health), **14** (analyst pulls as plain objects).

TL;DR: One typed read surface over the developer's own node — chain/block/tx/balance, per-wallet selection, chaintips + masternode-list changes + ChainLock tip status — returning plain/pydantic objects usable in analysts' own tools.

## Overview

A developer running their own node reads chain info, blocks, transactions, and balances; selects among multiple wallets per call; and monitors finality-relevant network health (chain tips, masternode-list changes, ChainLock tip status) — all through one client, all as plain Python objects, with REST-vs-ZMQ correctly scoped as trusted-network-only mechanisms that v0.1 does NOT implement as transports.

## Touchpoints

- Create: `src/ourdash/core/chain.py`, `tests/test_chain_reads.py`, `tests/test_network.py`.
- Write (sole owner): `src/ourdash/core/network.py`.
- Read-only: `core/rpc.py` (`DashRPC`, `batch`), `errors.py`, `redact.py`, `tests/conftest.py`, Core v23.1.8 `dash-cli help` (method allowlist source). Context: `process/context/all-context.md`, `process/context/tests/all-tests.md`.
- MUST NOT touch: `pyproject.toml`, `src/ourdash/__init__.py`, `core/rpc.py`, `core/addresses.py`, `core/wallet.py`, `core/transactions.py`, anything under `platform/`, CI, `README.md`, `docs/`.

## Public Contracts (New — Stable After This Phase)

- `core/chain.py` typed read facade (each function takes a `DashRPC` and returns a pydantic model; node errors propagate as the Phase 1 taxonomy): `get_blockchain_info` (height, chain name, verification progress, difficulty), `get_block(hash_or_height, verbosity)` (hash, height, time, tx list/count, chainlock flag when present), `get_transaction(txid, wallet_aware)` (amount detail, fee when available, confirmations, `instantlock` flag passthrough), `get_balance(wallet=None)` (mine-confirmed/unconfirmed split where the node reports it), `get_new_address(label=None, wallet=None)` (returns a Phase-2-validated address string). Wallet selection: every wallet-aware function accepts `wallet: str | None`; when set, the call is executed against a `DashRPC` bound to that wallet's `-rpcwallet` endpoint (construct the bound client internally from the passed client's config — never mutate the caller's client). Unknown wallet → node's error surfaced as `RpcError` with code preserved (criterion 3 failure path).
- `core/network.py` health surface (owns the ONLY global ChainLock-tip reader — distinct from Phase 3's per-tx `confirm_status`, which this phase MUST NOT modify): `get_chain_tips` (each tip: height, hash, branch length, status), `masternode_list_diff(base_height)` (added/removed/changed quorum-relevant entries between two `masternode list` snapshots — exact diff shape: three lists of deterministic identifiers, documented in-test), `chainlock_tip_status` (locked height + locked hash from `getbestchainlock`, plus `behind_by` = node height minus locked height). All three are JSON-RPC-only.
- REST-vs-ZMQ split (hard v0.1 boundary, recorded in `network.py` module docstring AND asserted by a test scanning that docstring): Dash Core's read-only HTTP mechanism and its real-time push-feed mechanism are two SEPARATE opt-in mechanisms; both are same-port-or-separate-port trusted-network-only features with user-visible warnings; v0.1 implements NEITHER as a transport — this module exposes JSON-RPC helpers only. Any future addition requires explicit opt-in constructor + trusted-network warning; the test fails if the docstring boundary wording is removed.
- Analyst shape (criterion 14, Core leg): every model above exposes `to_dict()` returning only stdlib types (str/int/float/bool/None/lists/dicts) so blocks/transactions/address activity drop directly into analysts' own tooling; a test asserts `json.dumps(model.to_dict())` round-trips for block, transaction, and balance models. (Full criterion 14 proof closes with the Agent-Probe testnet pull recorded here and finished in Phase 6 walkthrough.)

## Blast Radius

Medium: 2 source files (1 new, 1 stub filled), 2 test files. All reads are non-mutating RPC; no signing, no Platform. Risk class: low-medium (RPC shape drift vs Core versions — contained by pinning expectations to v23.1.8 `dash-cli help` and asserting only specified fields, ignoring unknown extras).

## Implementation Checklist

1. Implement `core/chain.py` exactly per Public Contracts (pydantic response models with `to_dict()`; wallet binding via copied config; unknown-extras ignored, specified fields required).
2. Implement `core/network.py` exactly per Public Contracts (three health readers + the REST-vs-ZMQ boundary docstring; no REST client, no ZMQ subscriber, no new dependencies).
3. Write `tests/test_chain_reads.py`: Fully-Automated part against the in-process fake server (response-shape parsing, wallet-endpoint path per `wallet=` argument, unknown-wallet `RpcError` code passthrough, `to_dict()` JSON round-trips); Hybrid part (`hybrid` mark) against the regtest fixture proving criterion 1 (chain info + block + balance on a live node), criterion 3 (create second wallet, fund separately, assert per-wallet balances differ and selection routes correctly), and address-activity pull shape.
4. Write `tests/test_network.py`: Fully-Automated part with canned `getchaintips`/`masternode list`/`getbestchainlock` payloads (tip parsing, diff three-list shape on crafted before/after snapshots, `behind_by` arithmetic); docstring-boundary scan test; Hybrid part asserting all three readers execute against regtest (shape + types; boolean lock values NOT asserted true on regtest — document why in-test).
5. Record the `dash-cli help` (Core v23.1.8) method allowlist exercised by this phase in a `chain.py` module comment with retrieval date.
6. Run the full gate set below; fix until green.

## Test Gates (Level-1 — Exact Commands)

- `pytest tests/test_chain_reads.py tests/test_network.py -vv -m "not hybrid"` — all pass, fake server + canned payloads only.
- `pytest tests/test_chain_reads.py tests/test_network.py -vv -m hybrid` — passes with regtest `dashd`; cleanly skips without it.
- `pytest -q -m "not hybrid and not agent_probe"`, `ruff check src tests`, `black --check src tests`, `mypy src` — all clean.
- `git status --porcelain` — shows ONLY `core/chain.py`, `core/network.py`, `tests/test_chain_reads.py`, `tests/test_network.py`.
- Agent-Probe (record, do not gate): testnet `get_blockchain_info` + one block pull cross-checked against a public explorer count (criterion 14 leg; recorded output committed as a note in the phase report, full walkthrough in Phase 6).

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| local-node read (chain info, block, balance on regtest) | Hybrid (`test_chain_reads.py`) | 1 |
| multi-wallet selection (separate balances, routed calls, unknown-wallet error) | Hybrid + Fully-Automated | 3 |
| network-health reads (tips, masternode diff, ChainLock tip) | Hybrid (shape on regtest) + Fully-Automated (canned parsing) | 9 |
| analyst pulls as plain objects (`to_dict()` JSON round-trip) + testnet spot-check | Fully-Automated + Agent-Probe | 14 |

## Acceptance Criteria

- Regtest reads return typed chain info, block, and balance through the facade; per-wallet balances differ and route correctly; unknown wallet surfaces the node code.
- Chaintips, masternode-list diff (three-list shape), and ChainLock-tip `behind_by` parse from canned payloads and execute on regtest.
- Every response model `to_dict()` JSON round-trips using stdlib types only; testnet spot-check recorded.
- `network.py` docstring carries the REST-vs-ZMQ trusted-network-only boundary wording, enforced by test.

## Exit Criteria

- All Test Gates green; wallet routing, health shapes, `to_dict()` round-trips, and the REST-vs-ZMQ boundary all observable in tests.
- Phase 3 files byte-identical (`git diff --stat` shows none of them). Status may move to ✅ VERIFIED when gates pass.

## Resume and Execution Handoff

- Next phase: `phase-05-platform-proofs-04-09-26.md` (Platform side; MUST NOT import from `core/` — seam rule; may mirror facade patterns only).
- This phase leaves behind: complete typed Core read surface + health readers + analyst-ready objects.
- Known gaps carried forward: Platform reads + proof verdicts (Phase 5); docs + final gates (Phase 6); criterion 14 testnet walkthrough leg (Phase 6).

## Test Infra Improvement Notes

(none identified yet)

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)

## Phase Completion Rules

Per umbrella: fake-server parsing + Hybrid regtest reads + Agent-Probe spot-check recorded + all four gates green. No separate user confirmation is needed beyond the filed probe note; mark ✅ VERIFIED when gates pass and the probe note is filed.

Execute-anchor note: this file is one of the program's supporting phase files (primary execute anchor above); execute phases strictly in order 1→6.

Next Step: review this phase plan, then say `ENTER EXECUTE MODE` to implement it exactly as specified.
