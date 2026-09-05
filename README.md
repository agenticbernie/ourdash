# ourdash — Python SDK for Dash

Dash here means Dash crypto from dash.org — not Plotly Dash (the dashboard
framework on PyPI as `dash`; never install that expecting crypto).

Modern typed Python SDK covering **Dash Core** (RPC, wallet/tx,
P2P/network) + **Dash Platform** (DAPI, Drive, identities, DPNS, tokens).

> Status: `v0.1.0`. Scope is deliberately narrow: typed Core reads,
> offline P2PKH payment pipeline (build → review → sign → submit →
> confirm), address validation, network-health reads, and Platform reads
> with proof verdicts. Explicitly NOT in v0.1: any hosted API, a GUI
> wallet, node infrastructure operation, multisig/script signing, or full
> Platform writes.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
pytest -q -m "not hybrid and not agent_probe"
```

The `src/` layout requires the editable install. See
[`docs/install.md`](docs/install.md) for the full walkthrough.

## Layout

```
src/ourdash/
  __init__.py        -- version + top-level exports (import from here)
  core/              -- Dash Core: rpc, addresses, transactions, wallet, chain, network
  platform/          -- Dash Platform: dapi client, seeds, models, proofs, drive
  utils/             -- shared hashing / base58-check helpers
  errors.py          -- typed exception taxonomy (all subclass OurdashError)
  redact.py          -- secret-redaction choke point
tests/               -- per-phase suites + secret-scan + docs gates
docs/                -- the five end-to-end guides (start below)
```

```python
from ourdash import DashRPC, DAPIClient, Wallet, validate_address
```

## Guides

Start here — each was executed verbatim end to end:

- [`docs/install.md`](docs/install.md) — clean venv → `pip install -e ".[all]"` → green suite
- [`docs/connect.md`](docs/connect.md) — env-only credentials, loopback default, remote opt-in, wallet selection
- [`docs/first-payment-testnet.md`](docs/first-payment-testnet.md) — fund → build → review → sign → submit → `confirm_status` (custody warnings inline)
- [`docs/first-platform-read.md`](docs/first-platform-read.md) — seed discovery → documents query → verdict interpretation → explicit fallback
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — one section per typed error (symptom → cause → fix) plus secrets-safety rules

## Dash references

- Dash.org: https://www.dash.org (Dash crypto — not Plotly Dash)
- Docs: https://docs.dash.org (Core RPC + Platform DAPI/Drive/DPP)
- Core RPC: `dashd` JSON-RPC (`dash-cli help`); parity pin Dash Core v23.1.8
- Platform: DAPI (per-network seed discovery — no default URL ships), Drive, DPP, DPNS

## Quality gates

```bash
.venv/bin/pytest -q -m "not hybrid and not agent_probe"
.venv/bin/ruff check src tests
.venv/bin/black --check src tests
.venv/bin/mypy src
```

All four must be green before every commit. Live tests are marked
`hybrid` (regtest fixture / recorded proof envelopes) and `agent_probe`
(testnet walkthroughs, never in CI). Solo-maintained, strict by default.
See `process/context/tests/all-tests.md`.
