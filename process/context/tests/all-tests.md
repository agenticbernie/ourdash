---
name: context:all-tests
description: "Testing entrypoint — pytest runner, commands, debugging, quality gates"
keywords: test, pytest, verification, coverage, mypy, ruff, black, quality
related: [context:all-planning]
date: 04-09-26
---

# ourdash - All Tests

Last updated: 2026-09-05

Attach this file first when the task involves testing, verification, or test debugging.

This is the fast operator guide for the testing surface:

- which runner to use
- what command to start with
- how to quickly debug common failures
- which deeper file to read next

Do not load the whole `process/context/tests/` folder by default. Start here, then drill down.

---

## How This File Works

This is the `all-tests.md` entrypoint for the `tests/` context group. It follows the `all-*.md` routing convention:

1. Agents read `all-context.md` first and get routed here for testing tasks
2. This file gives quick decision rules and commands
3. For deeper details, agents follow the routing table below to specific docs

As the project grows, add deeper docs to this group (e.g., `e2e-tests.md`, `debugging-and-pitfalls.md`) and add routing entries below. This file stays the fast-start entrypoint.

---

## What This Covers

- test runner selection
- quick commands by package
- fast debugging procedures
- current testing gaps worth remembering

## Read This When

Use this file when you need to:

- run tests after implementation
- decide between test runners
- debug failing tests

## Quick Routing

No deeper test docs yet. Add routing entries here as they are created.

| If you need... | Read next |
|---|---|
| RPC live-integration vs regtest | `tests/conftest.py` (`dashd_regtest` fixture: boots local `dashd` or skips; Hybrid enabler) |
| DAPI integration / proofs | `tests/fixtures/platform/` recorded envelopes + `src/ourdash/platform/proofs.py` (FakeVerifier + bridge boundary) |
| failing-test triage | See Debugging Quick Reference below |

## Quick Decision Guide

### Use `pytest` for everything

- all unit tests run through `pytest`
- `pytest -q` for CI, `pytest -vv` for debugging
- single file: `pytest tests/test_import.py -vv`
- coverage: `pytest --cov=src/ourdash --cov-report=term-missing -q`

### Use `mypy --strict` for type verification

- `mypy src` must pass on every non-trivial change
- modules in `src/ourdash/core/` and `src/ourdash/platform/` are typed; keep them strict

### Use `ruff` + `black` for lint/format

- `ruff check src tests`
- `black --check src tests` (write with `black src tests`)

## Default Verification Order

Unless the task clearly needs a different path:

1. run the narrowest existing automated test (`pytest tests/test_import.py -vv`)
2. run full unit suite (`pytest -q -m "not hybrid and not agent_probe"` — v0.1 final: 185 collected / 7 deselected)
3. run typecheck (`mypy src`) and lint (`ruff check src tests`) + format (`black --check src tests`)
4. use Hybrid tests only when a `dashd` regtest binary is available (`pytest -q -m hybrid`; skips cleanly without it); Agent-Probe (live testnet) is human/agent-run, never CI

## Commands

| Package | Runner | Command | Notes |
|---|---|---|---|
| `ourdash` CI gate | pytest | `pytest -q -m "not hybrid and not agent_probe"` | v0.1 final: 185 collected / 7 deselected; no node needed |
| `ourdash` single file | pytest | `pytest tests/test_import.py -vv` | fastest triage |
| `ourdash` hybrid | pytest | `pytest -q -m hybrid` | needs `dashd` binary or recorded fixtures; skips cleanly without |
| `ourdash` coverage | pytest-cov | `pytest --cov=src/ourdash --cov-report=term-missing -q` | keep new code covered |
| typecheck | mypy | `mypy src` | strict mode per `pyproject.toml` |
| lint | ruff | `ruff check src tests` | line-length 100, py310 |
| format check | black | `black --check src tests` | run `black src tests` to fix |

**Bootstrap (fresh checkout):**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
pytest -q
```

## Debugging Quick Reference

- **import errors:** ensure editable install (`pip install -e ".[all]"`) so `src/` layout resolves; `PYTHONPATH=src pytest` as fallback
- **marker selection errors (`-m` flag fails):** markers `hybrid` + `agent_probe` must be registered in `pyproject.toml` before `-m` selection works (E1 guard: register markers in the same edit that first uses them)
- **marker order:** put `pytestmark` / `-m` deselection notes first in new test files so CI selection (`not hybrid and not agent_probe`) classifies correctly
- **Python version:** requires `>=3.10`; CI uses `3.10–3.12`; local here is `3.14.6`
- **no live node by default:** unit tests must not require `dashd` or network; gate live tests behind env (`OURDASH_RPC_URL`, `OURDASH_DAPI_ADDRESS`) and skip when absent
- **DAPI extras:** `pip install -e ".[platform]"` for `grpcio`/`protobuf`; unit suite passes without them
- **naming collision:** PyPI `dash` is Plotly, not Dash crypto — do not `pip install dash` expecting crypto; package here is `ourdash`

## Current State (v0.1 final — suite 185/7-deselected, all gates green)

- Regtest `dashd` fixture shipped (`tests/conftest.py`): Hybrid enabler, skips cleanly without binary; regtest submit+confirm + health reads proven
- DAPI/Drive proof tests shipped: recorded envelopes in `tests/fixtures/platform/` + `FakeVerifier` + explicit-fallback (`trust_node=True` → `UNCHECKED` + `UserWarning`) + dead-default-absent tests
- Wallet signing vectors shipped: published BIP39 vectors offline (restore → BIP32/44 coin type 5 → P2PKH); P2SH/multisig/script refused via `PaymentError`
- CI workflow `.github/workflows/ci.yml` shipped: pytest (non-hybrid/probe) + ruff + black --check + mypy on Python 3.10–3.12
- Secret-scan gate shipped (`tests/test_secrets.py`): sentinels absent from logs/errors/files; seam lint (`tests/test_seam.py`) enforces transport-dataclass / facade-pydantic split

## Known Residuals (accepted, not CI-gated)

- Analyst pulls + docs walkthrough are Agent-Probe only (human/agent-run on testnet, never CI)
- Recorded proof fixtures prove parsing + verdict plumbing, not live proof cryptography (bridge target pinned in `platform/proofs.py` docstring)
- Local interpreter here is `3.14.6` vs CI matrix `3.10–3.12` (advisory skew, accepted)
