# Phase 1 — Transport + Safety + CI

Date: 04-09-26. Status: ⏳ PLANNED. Umbrella: `ourdash-sdk_PLAN_04-09-26.md`.

**Date**: 04-09-26
**Status**: ⏳ PLANNED
**Complexity**: COMPLEX (phase 1 of 6 in phase program)

SPEC criteria covered: **2** (safe-by-default connection), **15-part** (wrong creds / unreachable / timeout typed errors; rejected-tx type defined here, proven in Phase 3), **17-part** (CI workflow exists + all gates green on current tree).

TL;DR: Build the trusted transport core everything else stands on — typed errors, secret redaction, JSON-RPC client with safe defaults, regtest fixture, seam lint, CI — with zero payload knowledge.

## Overview

A developer can construct `DashRPC`, point it only at safe targets by default, get a distinct typed error for every transport failure with no secrets inside, and every change is gated by CI. No address/wallet/Platform logic in this phase.

## Touchpoints

- Create: `src/ourdash/errors.py`, `src/ourdash/redact.py`, `tests/conftest.py`, `tests/test_errors.py`, `tests/test_rpc_transport.py`, `tests/test_seam.py`, `.github/workflows/ci.yml`.
- Write (sole owner): `pyproject.toml`, `src/ourdash/core/rpc.py`.
- Read-only: locked SPEC, `process/context/all-context.md`, `process/context/tests/all-tests.md`, `tests/test_import.py` (MUST keep passing unchanged).
- MUST NOT touch: `src/ourdash/__init__.py`, `utils/`, `core/addresses.py`, `core/wallet.py`, `core/transactions.py`, `core/network.py`, anything under `platform/` (except reading), `README.md`, `docs/`.

## Public Contracts (New — Stable After This Phase)

- Error taxonomy in `ourdash.errors` (exact class names, all subclassing `OurdashError` → `Exception`): `RpcError` (fields: numeric `code` or `None`, secret-free `message`), `RpcAuthError(RpcError)`, `RpcConnectionError(RpcError)`, `RpcTimeoutError(RpcError)`, `ConfigError` (remote-refused, missing creds, bad wallet selection input), `AddressError`, `WalletError`, `PaymentError` (unsigned/malformed submit refusal — raised first in Phase 3), `DAPIError`, `ProofError`, `ProofUnavailableError`. Later phases import these; this file is never rewritten by them.
- Redaction choke point in `ourdash.redact`: a banned-key set containing at minimum `mnemonic`, `seed`, `xprv`, `xpub` (private material only — note: extended public keys are safe to log but banned keys err conservative; document this), `privkey`, `private_key`, `password`, `passphrase`, `rpcpassword`, `cookie`, `auth`; a `redact()` mapping that replaces values under banned keys (case-insensitive, substring match) with a fixed mask; a logging `Filter` that applies `redact()` to record args. All SDK logging and all `__str__`/`__repr__` of errors and configs pass through it.
- `DashRPCConfig` (frozen dataclass, new fields vs current stub): `host` default `"127.0.0.1"`, `port` default `9998`, `user`, `password`, `timeout_s` default `30.0` (all preserved so `test_import.py` keeps passing), plus `wallet: str | None = None`, `cookie_path: str | None = None`, `remote_ok: bool = False`. `from_env()` classmethod reads ONLY these names: `OURDASH_RPC_URL` (overrides host+port parse), `OURDASH_RPC_USER`, `OURDASH_RPC_PASSWORD`, `OURDASH_RPC_WALLET`. `__repr__`/`__str__` MUST route through `redact()` (no credential or cookie content ever rendered).
- `DashRPC`: constructor validates loopback-only unless `remote_ok=True` (loopback set exactly: `127.0.0.1`, `::1`, `localhost`; anything else without `remote_ok=True` raises `ConfigError` — this is SPEC criterion 2). `call(method, *params)` posts JSON-RPC 1.0 with `Content-Type: text/plain`, HTTP basic auth (user/password or cookie file content when `cookie_path` set; explicit user/password wins), `timeout_s` timeout, at most 3 attempts with bounded backoff on connection-level failures only (never retries auth failures or node error responses). Wallet selection: when `wallet` is set, requests go to the `-rpcwallet` endpoint path for that wallet name. `batch(calls)` sends one array-framed request with incremental string ids and returns results in call order, raising the matching typed error entry on per-call node errors. Node error `-28` (warming up) is retriable; node auth failure maps to `RpcAuthError`; unreachable maps to `RpcConnectionError`; elapsed-timeout maps to `RpcTimeoutError`; every other node error maps to `RpcError` carrying code+message only.
- `pyproject.toml` additions (only writer): runtime deps `ecdsa>=0.18` and `mnemonic>=0.20` (needed by Phase 3; pinned here so later phases never touch the file); pytest marker registration for `hybrid` (needs regtest `dashd` or recorded fixtures) and `agent_probe` (live testnet, never run in CI). If `mypy src` fails on the new third-party imports for missing type hints, add a `[[tool.mypy.overrides]]` stanza for exactly those modules in this same edit — no other config changes.
- CI `.github/workflows/ci.yml`: matrix Python `3.10`, `3.11`, `3.12`; steps: checkout, setup-python, `pip install -e ".[all]"`, `pytest -q -m "not hybrid and not agent_probe"`, `ruff check src tests`, `black --check src tests`, `mypy src`.

## Blast Radius

Small, foundational: 2 files rewritten, 7 created, 0 production callers (no other module exists yet that imports them). Risk class: low. The load-bearing risk is behavioral (auth/timeout/retry semantics), contained by fake-server tests. `test_import.py` MUST stay green unchanged.

## Implementation Checklist

1. Write `src/ourdash/errors.py`: exact classes from Public Contracts; each stores only `code`/`message`-style safe fields; `__str__` passes through `redact()`; no attribute may retain a credential, phrase, or key.
2. Write `src/ourdash/redact.py`: banned-key set, `redact()` mapping, logging filter; unit-cover nested dicts/lists and case variants in `test_errors.py`.
3. Rewrite `src/ourdash/core/rpc.py` transport-only: stdlib + `dataclasses` + `requests` ONLY — the literal string `pydantic` MUST NOT appear in this file (enforced by `test_seam.py`); implement `DashRPCConfig` fields, `from_env()`, loopback validation, `call`, `batch`, cookie-file auth, `-rpcwallet` path selection, timeout/retry/error mapping exactly per Public Contracts. Module docstring records Core pin v23.1.8 and default ports mainnet 9998 / testnet 19998 / regtest 19898 / devnet 19788.
4. Write `tests/test_errors.py`: each taxonomy class raisable/catchable through its parent; redaction cases (mnemonic/password/cookie values masked in `str(err)` and log records).
5. Write `tests/test_rpc_transport.py` (Fully-Automated, in-process fake HTTP server — no `dashd`): JSON-RPC 1.0 body shape + `text/plain` header asserted; basic-auth header asserted without logging the password; `-rpcwallet` path asserted when configured; timeout → `RpcTimeoutError`; refused connection → `RpcConnectionError`; HTTP 401 → `RpcAuthError`; node error object → `RpcError` with code preserved; batch order + per-call error mapping; remote host without `remote_ok` → `ConfigError`; with `remote_ok=True` → allowed; `from_env` honors env names only.
6. Write `tests/test_seam.py`: read the source text of `src/ourdash/core/rpc.py` and `src/ourdash/platform/dapi.py` and assert the string `pydantic` appears in neither; walk `src/ourdash/core/*.py` source and assert none contains the string `from ourdash.platform` or `from ..platform`.
7. Write `tests/conftest.py`: `dashd_regtest` fixture (session-scoped) that starts the binary from `OURDASH_DASHD_BIN` (default `dashd`) with regtest on loopback, cookie auth, a private datadir under `tmp_path_factory`; yields a `DashRPC` pointed at it plus a `dash-cli`-equivalent helper for mining (`generatetoaddress`); skips the test (`pytest.skip`) when the binary is absent; always stops the node on teardown. Mark all consumers `hybrid`.
8. Edit `pyproject.toml` exactly per Public Contracts (deps + markers + conditional mypy override only).
9. Create `.github/workflows/ci.yml` exactly per Public Contracts.
10. Run the full gate set below; fix until green.

## Test Gates (Level-1 — Exact Commands)

- `pytest tests/test_errors.py tests/test_rpc_transport.py tests/test_seam.py -vv` — all pass, no network, no node.
- `pytest -q -m "not hybrid and not agent_probe"` — full unit suite green.
- `pytest -q -m hybrid --collect-only` — regtest-marked tests collect (skip, do not fail, without `dashd`).
- `ruff check src tests`, `black --check src tests`, `mypy src` — all clean.
- New vectors/fixtures: fake-server request-shape assertions (in-test); no committed binary fixtures in this phase.

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| remote-refused-by-default + env-only creds | Fully-Automated (`test_rpc_transport.py`) | 2 |
| wrong-creds → `RpcAuthError`; unreachable → `RpcConnectionError`; timeout → `RpcTimeoutError`; secrets absent from all three | Fully-Automated (fake server + redaction asserts) | 15-part |
| CI workflow exists; pytest + ruff + black + mypy green | Fully-Automated | 17-part |
| regtest fixture boots-or-skips; seam lint green | Fully-Automated + Hybrid collect | enabling (no criterion) |

## Acceptance Criteria

- Non-loopback host without `remote_ok=True` raises `ConfigError`; loopback + explicit opt-in connect normally.
- Wrong creds / unreachable / timeout each raise their distinct typed error with zero secret content in message, repr, or logs.
- JSON-RPC 1.0 body shape, `text/plain` header, auth header, `-rpcwallet` path, batch ordering, and retry-only-safe-failures all asserted against the fake server.
- CI workflow exists and runs all four gates on Python 3.10–3.12; `tests/test_import.py` passes unchanged.

## Exit Criteria

- All Test Gates green; `tests/test_import.py` passing unchanged.
- Remote-refusal, auth, connection, timeout, batch, wallet-path, and redaction behaviors observable exactly as specified.
- Handoff note written (next section). Status may move to ✅ VERIFIED only after gates pass.

## Resume and Execution Handoff

- Next phase: `phase-02-addresses-04-09-26.md` (addresses; imports `errors.py`/`redact.py`, uses no transport).
- This phase leaves behind: working `DashRPC` transport, full error taxonomy (including later-phase classes), redaction choke point, regtest fixture, seam lint, CI.
- Known gap carried forward: rejected-transaction error (`PaymentError`) defined but first raised in Phase 3.

## Test Infra Improvement Notes

(none identified yet)

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)

## Phase Completion Rules

Per umbrella: integration (fake server) + error-path coverage + all four gates green. No manual user confirmation required for this phase (no user-visible flow yet); mark ✅ VERIFIED when gates pass.

Execute-anchor note: this file is one of the program's supporting phase files (primary execute anchor above); execute phases strictly in order 1→6.

Next Step: review this phase plan, then say `ENTER EXECUTE MODE` to implement it exactly as specified.
