# Phase 6 — Docs-from-Zero + Secret-Scan + Clean-Gate

Date: 04-09-26. Status: ⏳ PLANNED. Umbrella: `ourdash-sdk_PLAN_04-09-26.md`. Depends on: Phases 1–5 (✅ VERIFIED).

**Date**: 04-09-26
**Status**: ⏳ PLANNED
**Complexity**: COMPLEX (phase 6 of 6 in phase program)
SPEC criteria covered: **16** (secrets never leak — repo-wide scan gate), **17** (clean-gate proof from fresh checkout), **18** (docs work from zero).

TL;DR: Prove the whole program — curated top-level exports, five end-to-end guides verified on testnet by a fresh reader, automated secret-scan, and all four quality gates green from a clean checkout.

## Overview

A new developer with only the shipped guides installs the package from a clean checkout, connects, completes a first test-network payment and a first Platform read, troubleshoots a failure using only the troubleshooting guide — and the repo proves secrets safety and gate-green status automatically.

## Touchpoints

- Write (sole owner): `src/ourdash/__init__.py`, `README.md`, `process/context/all-context.md` (plan-owned corrections ONLY — listed below).
- Create: `docs/install.md`, `docs/connect.md`, `docs/first-payment-testnet.md`, `docs/first-platform-read.md`, `docs/troubleshooting.md`, `tests/test_secrets.py`, `tests/test_docs.py`.
- Read-only: everything under `src/` + all phase test files (to document the true surface). Context: `process/context/all-context.md`, `process/context/tests/all-tests.md`.
- MUST NOT touch: `pyproject.toml`, CI file, any other source module, any other test file, the locked SPEC.

## Public Contracts (New/Fixed — Final)

- Top-level exports (`src/ourdash/__init__.py`, sole writer — exact list, nothing more): `__version__`, `DashRPC`, `DashRPCConfig`, `DAPIClient`, `DAPIConfig`, `AddressInfo`, `validate_address`, `Wallet`, `UnsignedTx`, `SignedTx`, `ConfirmationStatus`, `ProofVerdict`, `ProvenResult`, `OurdashError`, `RpcError`, `RpcAuthError`, `RpcConnectionError`, `RpcTimeoutError`, `ConfigError`, `AddressError`, `WalletError`, `PaymentError`, `DAPIError`, `ProofError`, `ProofUnavailableError`. `__all__` lists exactly these. If any name does not exist after Phases 1–5, EXECUTE STOPS and reports back (missing export = prior phase incomplete; do not invent the object here). `tests/test_import.py` may be extended with an export-list assertion but its two original assertions MUST keep passing.
- Guides (exact files + acceptance bar): `install.md` (venv → `pip install -e ".[all]"` → `pytest -q` green), `connect.md` (env-only creds, loopback default, remote opt-in, wallet selection, each with expected output), `first-payment-testnet.md` (fund → build → review → sign → submit → `confirm_status`, with custody warnings inline), `first-platform-read.md` (seed discovery → documents query → verdict interpretation → explicit fallback), `troubleshooting.md` (one section per typed error: symptom → cause → fix; plus secrets-safety rules). Every guide disambiguates "Dash (dash.org)" vs "Plotly Dash" on first mention (name rule from SPEC constraints; asserted by `test_docs.py`). Every shell session in every guide is executed VERBATIM during the walkthrough — a guide that needs paraphrase to work FAILS criterion 18.
- `README.md` refresh: install, layout, Dash refs, quality gates, link to the five guides; keep package description truthful to v0.1 scope (reads + offline payments + verdicts; no hosted API, no GUI wallet, no infra operation, no full Platform writes).
- `all-context.md` plan-owned corrections (ONLY these hunks; no other context edits): (a) Technology-stack Core line — replace the "ChainLocks + InstantSend (DIP0024 LLMQs)" attribution with the correct wording (ChainLocks active since block 1088640 Jun 2019; InstantSend original + deterministic forms; DIP0024 = quorum-rotation only, never the inventor of either); (b) DAPI default row — replace `https://api.dash.org` default with per-network seed discovery + never-ship rule; (c) Open Questions — mark Core pin (v23.1.8), wallet scope (signing in v0.1, watch-only default), and CI workflow (added Phase 1) resolved. Each correction cites the SPEC constraint it implements.
- Secret-scan (`tests/test_secrets.py`, Fully-Automated): fixed UNIQUE sentinel strings (a fake mnemonic-shaped sentinel, a fake password, a fake cookie) are threaded through wallet build/sign, failing-RPC calls, and error rendering with `caplog`/`capsys` capture; the test FAILS if any sentinel appears in captured logs, exception strings/`repr`s, or any file under `tmp_path` written by the SDK during the run. A second test scans `src/` text for banned literals (`api.dash.org`, `rpcpassword=` with a value, private-key-looking hex literals longer than 32 chars outside test vectors — exact rule coded in-test with an allowlist comment).
- Docs-existence test (`tests/test_docs.py`, Fully-Automated): asserts the five guide files exist, each contains its required sections (checked by heading strings listed in-test), each names Dash-vs-Plotly-Dash disambiguation, and every `ourdash`-import + public name referenced in guides resolves against the final `__init__` exports.

## Blast Radius

Docs + export surface + 2 test files: zero behavioral change to SDK logic (any logic bug found during walkthrough is fixed in the OWNING phase's files via an explicit plan amendment, not smuggled into this phase). Risk class: low code risk; the load-bearing risk is guide accuracy — contained by verbatim walkthrough + import-resolution test. `all-context.md` edits are the only context changes in the program.

## Implementation Checklist

1. Write the final `src/ourdash/__init__.py` export list exactly per Public Contracts (stop-and-report rule on missing names); extend `test_import.py` with the export assertion only.
2. Write the five guides exactly per Public Contracts (verbatim-executable sessions, custody warnings, disambiguation line, troubleshooting per typed error).
3. Refresh `README.md` per Public Contracts (scope-honest, links to guides).
4. Apply the three `all-context.md` correction hunks exactly per Public Contracts (nothing else in that file).
5. Write `tests/test_secrets.py` + `tests/test_docs.py` exactly per Public Contracts.
6. Secret-scan run: `pytest tests/test_secrets.py -vv` green.
7. Fresh-checkout clean-gate (exact procedure, Agent-Probe-adjacent but machine-run): fresh `python -m venv`, `pip install -e ".[all]"`, then `pytest -q -m "not hybrid and not agent_probe"`, `ruff check src tests`, `black --check src tests`, `mypy src` — all green, output recorded.
8. Docs walkthrough (Agent-Probe, human/agent on testnet, following ONLY the shipped guides): install → connect → first payment → first Platform read → one induced failure fixed via troubleshooting guide. Record deviations verbatim; any guide fix re-runs the affected guide from its first step. If Phase 5 left `synthetic-pending-recapture` fixtures, recapture from testnet here and re-run `test_proofs.py`.
9. Run the full gate set below; fix until green.

## Test Gates (Level-1 — Exact Commands)

- `pytest tests/test_secrets.py tests/test_docs.py -vv` — green.
- Fresh-checkout procedure (step 7) — all four gates green, output recorded in the phase report.
- `pytest -q -m "not hybrid and not agent_probe"`, `ruff check src tests`, `black --check src tests`, `mypy src` — green in the working tree.
- `git status --porcelain` — shows ONLY `__init__.py`, `README.md`, `all-context.md`, `docs/*`, `tests/test_secrets.py`, `tests/test_docs.py`, `tests/test_import.py`.
- Walkthrough (step 8) — all five guides completed verbatim; deviations log empty or fully resolved with re-runs.

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| secret-scan over captured outputs + source-literal scan | Fully-Automated (`test_secrets.py`) | 16 |
| clean-gate: fresh checkout → install → pytest + ruff + black + mypy green; CI workflow present | Fully-Automated | 17 |
| docs walkthrough end to end on testnet (verbatim sessions) | Agent-Probe | 18 |
| guide import-resolution + disambiguation asserts | Fully-Automated (`test_docs.py`) | 18-part |

## Acceptance Criteria

- Top-level `__all__` matches the exact export list; every guide-referenced name resolves; `test_import.py` original assertions intact.
- All five guides execute verbatim end to end on testnet (deviations log resolved with re-runs); troubleshooting fixes the induced failure.
- `test_secrets.py` green: sentinels absent from logs, exception text, and written files; source-literal scan clean.
- Fresh-checkout venv install + all four gates green with recorded output; the three `all-context.md` hunks applied and cited.

## Exit Criteria

- All Test Gates green; walkthrough deviations log resolved; `test_import.py` original assertions intact; program-level success criteria (umbrella) met.
- Whole program may move to ✅ VERIFIED only after this phase's gates + walkthrough pass. Closeout: archive plan set per update-process; report which SPEC criteria rest on Hybrid vs Agent-Probe evidence for the maintainer's release notes.

## Resume and Execution Handoff

- Next step after this phase: `ENTER UPDATE PROCESS MODE` (archive umbrella + 6 phase plans; capture learnings; record Hybrid/Agent-Probe evidence ledger for v0.1 release notes).
- This phase leaves behind: shippable v0.1 (code + fixtures + CI + guides + scan gates).
- Known residual risks for release notes: proof verification rests on bridge + FakeVerifier (no pure-Python port); gRPC streaming deferred; multisig/script signing deferred; X11 not implemented (block-hashing only, correctly out of scope).

## Test Infra Improvement Notes

(none identified yet)

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)

## Phase Completion Rules

Per umbrella: secret-scan + fresh-checkout gates + verbatim walkthrough + all four gates green + user confirmation of the walkthrough result. Mark ✅ VERIFIED only when the walkthrough is confirmed working.

Execute-anchor note: this file is one of the program's supporting phase files (primary execute anchor above); execute phases strictly in order 1→6.

Next Step: review this phase plan, then say `ENTER EXECUTE MODE` to implement it exactly as specified.
