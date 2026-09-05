# Phase 5 — Platform Reads Facade + Proof Port + FakeVerifier

Date: 04-09-26. Status: ⏳ PLANNED. Umbrella: `ourdash-sdk_PLAN_04-09-26.md`. Depends on: Phases 1–4 (✅ VERIFIED).

**Date**: 04-09-26
**Status**: ⏳ PLANNED
**Complexity**: COMPLEX (phase 5 of 6 in phase program)
SPEC criteria covered: **10** (app-data reads + verdict), **11** (explicit fallback), **12** (identity + username), **13** (token rules + transfers).

TL;DR: Seed-discovered DAPI transport (dead default removed, stays pydantic-free) + typed Drive facade where every read returns data plus a CHECKED/UNCHECKED verdict, backed by a verifier contract with FakeVerifier and recorded proof-envelope fixtures.

## Overview

A Platform app developer queries documents/contracts, identities/usernames, and tokens, and ALWAYS gets the data together with a trust verdict — proof-checked when verifiable, explicitly `UNCHECKED` only via keyword-only opt-in — with endpoints discovered per network and no dead placeholder address anywhere in the shipped code.

## Touchpoints

- Write (sole owner): `src/ourdash/platform/dapi.py`, `src/ourdash/platform/drive.py`.
- Create: `src/ourdash/platform/seeds.py`, `src/ourdash/platform/models.py`, `src/ourdash/platform/proofs.py`, `tests/test_dapi.py`, `tests/test_proofs.py`, `tests/fixtures/platform/` (recorded envelopes).
- Read-only: `errors.py` (`DAPIError`, `ProofError`, `ProofUnavailableError`, `ConfigError`), `redact.py`, `tests/test_import.py` (MUST keep passing: `DAPIClient().config.timeout_s == 30.0` preserved). Context: `process/context/all-context.md`, `process/context/tests/all-tests.md`.
- MUST NOT touch: `pyproject.toml` (grpc extras already present; HTTP/JSON surface needs no new dep), `src/ourdash/__init__.py`, anything under `core/` or `utils/` (no imports from them either — seam rule both directions for this phase), CI, `README.md`, `docs/`.

## Public Contracts (New — Stable After This Phase)

- Dead-default removal: `DAPIConfig.address` default becomes `None` (the current `"https://api.dash.org"` placeholder is DELETED, not deprecated — a test asserts that exact string appears NOWHERE under `src/`). `timeout_s` default stays `30.0`. New factory `DAPIClient.from_network(network, timeout_s=30.0)` resolving the endpoint through `seeds.py`; direct `DAPIClient(DAPIConfig(address=...))` remains allowed (explicit user choice) and MUST verify TLS on `https` endpoints. Constructing a client with `address=None` and calling any method raises `DAPIError` guiding to `from_network`.
- `seeds.py`: `SEEDS: dict[network, list[seed-entry]]` for `mainnet|testnet|regtest|devnet`, where each entry records host, interface (json-rpc/rest), and source. Seed VALUES are taken from exactly two named sources during EXECUTE (docs.dash.org Platform connectivity page + the pinned proof-capable JS toolkit defaults), each recorded with source URL + retrieval date in a module comment; if a network has no documented seed, its list is EMPTY (never a placeholder URL) and `from_network` for it raises `DAPIError` stating no seed is known. Includes the refresh procedure in the docstring (re-check sources each release; Agent-Probe `getStatus` against every listed seed; drop dead entries). Regtest/devnet default to loopback entries. A test asserts every non-loopback seed entry carries source + date metadata and that no entry contains `api.dash.org`.
- `dapi.py` transport-only (literal `pydantic` MUST NOT appear — `test_seam.py` covers this file): thin methods over HTTP/JSON with `timeout_s` timeout, bounded retries, TLS verification, typed errors (`DAPIError`; auth/timeout/connection subclasses reused from `errors.py`): `get_status`, `get_best_block_hash`, `get_block_hash(height)`, `broadcast_transaction(raw_hex)` (thin L1 submit primitive; broader Platform writes remain out of scope per SPEC). v0.1 uses the HTTP/JSON surface ONLY — gRPC streaming helpers are explicitly deferred (documented in module docstring with reason: streaming needs the optional `grpcio` channel surface pinned later; no streaming stub that silently degrades).
- `models.py` pydantic facade: `ProofVerdict` enum with EXACTLY `CHECKED` and `UNCHECKED`; `ProvenResult` wrapper (`data`, `verdict: ProofVerdict`, `proof_note: str`); `DocumentResult`, `DataContractInfo`, `IdentityInfo` (keys, credit balance, sequence number), `UsernameResolution` (name → identity id, contested flag), `TokenRules`, `TokenTransferPage` (entries + continuation token). All expose `to_dict()` of stdlib types only.
- `proofs.py` verifier contract: `Verifier` protocol with `verify(envelope) -> ProofVerdict`; `FakeVerifier` returning `CHECKED` for well-formed envelopes (proof field present + structurally valid) and raising `ProofError` for malformed ones — used by ALL Fully-Automated Platform tests; bridge boundary `ReferenceBridgeVerifier` implementing `Verifier` by invoking the pinned external reference verifier (package + version resolved in EXECUTE pre-step from the SPEC-pinned proof-capable JS toolkit, recorded in the docstring with pin + invocation schema: input = proof bytes + quorum-info JSON, output = boolean); when the reference binary is absent it raises `ProofUnavailableError` with install instructions. A greenfield pure-Python port is NOT attempted in v0.1 (stated in docstring).
- `drive.py` query facade (every read takes keyword-only `trust_node: bool = False` — positional passing is a `TypeError` by construction; assert in-test): `query_documents(contract, doc_type, filter, trust_node=False)`, `get_data_contract(contract_id, ...)`, `get_identity(identity_id, ...)`, `resolve_dpns(name, ...)`, `get_token_rules(token_id, ...)`, `get_token_transfers(token_id, ...)`. Behavior: `trust_node=False` verifies via the configured `Verifier` and returns `ProvenResult(verdict=CHECKED)`; if no verifiable proof is available it raises `ProofUnavailableError` (never silent trust); `trust_node=True` returns `ProvenResult(verdict=UNCHECKED)` AND emits a `UserWarning` stating the answer is unchecked (criterion 11 — assert warning + label in-test).
- Recorded-envelope vector (Hybrid enabler built HERE): `tests/fixtures/platform/` holds ≥1 real captured `getDocuments`-with-proof response envelope + ≥1 identity response + ≥1 token response, captured via the Agent-Probe testnet step below and committed as JSON with source endpoint + capture date in a `README.md` inside the fixture dir; Fully-Automated tests parse these fixtures through `FakeVerifier` + models (so the suite stays offline while anchored to real shapes).

## Blast Radius

Large-but-isolated: 2 stubs rewritten, 3 modules + 2 test files + fixture dir created; touches the `test_import.py`-covered constructor (defaults preserved). No `core/` contact whatsoever. Risk class: medium (external endpoint reality, proof greenfield) — contained by seed metadata discipline, dead-string test, fixture-anchored tests, and the explicit-unchecked rule.

## Implementation Checklist

1. Pre-step (research, no code): read the docs.dash.org Platform connectivity page + pinned JS toolkit defaults; record chosen seeds with source URLs + date for `seeds.py`; record the reference-verifier package + version pin for `proofs.py`. If a fact is unavailable, leave the list EMPTY with reason — never invent a hostname.
2. Implement `seeds.py` exactly per Public Contracts (tables + metadata + refresh procedure + loopback regtest/devnet).
3. Rewrite `dapi.py` transport-only per Public Contracts (dead default deleted; `from_network`; four thin L1 methods; TLS verify; pydantic-free; `timeout_s` default `30.0`).
4. Implement `models.py` (`ProofVerdict`, `ProvenResult`, six domain models, all `to_dict()`).
5. Implement `proofs.py` (`Verifier`, `FakeVerifier`, `ReferenceBridgeVerifier` boundary with absent-binary `ProofUnavailableError`).
6. Implement `drive.py` (six facade reads, keyword-only `trust_node=False`, CHECKED/UNCHECKED semantics + warning).
7. Capture fixtures: Agent-Probe testnet `getDocuments`-with-proof + identity + token responses into `tests/fixtures/platform/` with source + date notes (if testnet is unreachable at EXECUTE time, record the attempt and use structurally-faithful hand-built envelopes MARKED `synthetic-pending-recapture` — tests must still pass; recapture becomes a Phase 6 walkthrough item).
8. Write `tests/test_dapi.py` (Fully-Automated): dead-string absence; `address=None` → guiding `DAPIError`; `from_network` resolution incl. empty-seed-network error; TLS/timeout/retry behavior on fake server; seed metadata test.
9. Write `tests/test_proofs.py` (Fully-Automated + fixture-backed): `FakeVerifier` well-formed → CHECKED / malformed → `ProofError`; every `drive.py` read returns `ProvenResult` with verdict; `trust_node=True` → UNCHECKED + `UserWarning` asserted; positional `trust_node` → `TypeError`; proof-absent + `trust_node=False` → `ProofUnavailableError`; fixture envelopes parse through models with `to_dict()` round-trip.
10. Run the full gate set below; fix until green.

## Test Gates (Level-1 — Exact Commands)

- `pytest tests/test_dapi.py tests/test_proofs.py -vv` — all pass, offline (fixtures on disk).
- `pytest -q -m "not hybrid and not agent_probe"`, `ruff check src tests`, `black --check src tests`, `mypy src` — all clean.
- `git status --porcelain` — shows ONLY `platform/*`, `tests/test_dapi.py`, `tests/test_proofs.py`, `tests/fixtures/platform/`.
- `grep -rn "api.dash.org" src/` — empty output (dead default gone).
- Agent-Probe (record): `getStatus` against every listed seed + fixture capture provenance noted.

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| Platform read + trust verdict on recorded envelopes | Hybrid (recorded proof fixtures) | 10 |
| explicit-fallback (kw-only flag, UNCHECKED label + warning; silent-trust impossible) | Fully-Automated (`test_proofs.py`) | 11 |
| identity lookup + username resolution | Hybrid (recorded fixtures) + Agent-Probe spot-check | 12 |
| token rules + transfer page | Hybrid (recorded fixtures) | 13 |

## Acceptance Criteria

- Every Platform read returns `ProvenResult` (data + `CHECKED`/`UNCHECKED` verdict); proof-absent + `trust_node=False` raises `ProofUnavailableError`.
- `trust_node` is keyword-only (positional use is a `TypeError`); `True` returns `UNCHECKED` plus an asserted `UserWarning`.
- `grep -rn "api.dash.org" src/` is empty; seed entries carry source + date metadata; empty-seed networks raise guiding `DAPIError`.
- Recorded envelopes parse through `FakeVerifier` + models offline; seed pins + bridge pin recorded with sources and dates; no `core/` imports.

## Exit Criteria

- All Test Gates green; every Platform read observably returns data + verdict; `grep` for the dead host empty; `test_import.py` unchanged-green.
- Status may move to ✅ VERIFIED when gates pass and seed/bridge pins are recorded with sources + dates.

## Resume and Execution Handoff

- Next phase: `phase-06-docs-gate-04-09-26.md` (docs over the now-complete surface; top-level exports; secret-scan; clean-gate).
- This phase leaves behind: complete Platform read facade, verifier contract + FakeVerifier, recorded fixtures, seed discovery with refresh procedure.
- Known gaps carried forward: pure-Python proof port (deferred by design, bridge boundary defined); gRPC streaming (deferred, documented); synthetic fixtures if testnet capture failed (recapture in Phase 6 walkthrough).

## Test Infra Improvement Notes

(none identified yet)

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)

## Phase Completion Rules

Per umbrella: fixture-backed verdict tests + fallback explicitness + dead-string absence + all four gates green + probe provenance filed. No separate user confirmation is needed to mark this phase ✅ VERIFIED once gates pass and pins are recorded.

Execute-anchor note: this file is one of the program's supporting phase files (primary execute anchor above); execute phases strictly in order 1→6.

Next Step: review this phase plan, then say `ENTER EXECUTE MODE` to implement it exactly as specified.
