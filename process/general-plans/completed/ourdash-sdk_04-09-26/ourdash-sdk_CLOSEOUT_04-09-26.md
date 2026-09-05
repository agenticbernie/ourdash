# ourdash SDK v0.1 — Program Closeout

Date: 05-09-26. Status: DONE (archived). Branch `master`: `0bbf7ca` harness + `61699da` feat phases 1–6.

Full flow with no BLOCKED anywhere: vc-setup (fresh) → RESEARCH (DONE_WITH_CONCERNS) → findings-validation
CONDITIONAL → SPEC (18 criteria, DONE) → INNOVATE (Approach C trust-ladder hybrid, DONE) →
PLAN (umbrella + 6 phases, DONE_WITH_CONCERNS) → VALIDATE (CONDITIONAL, V5-accepted, outer-pvl contract) →
EXECUTE Phases 1–6 (all DONE) → git-manager (2 commits) → UPDATE PROCESS (this note).

Final gates: suite 185 collected / 7 deselected (`-m "not hybrid and not agent_probe"`), `ruff` / `black --check` /
`mypy src` clean, fresh-checkout proof green, live testnet reads recorded. AP-only residuals (accepted):
SPEC 14 analyst pulls, SPEC 18 docs walkthrough.

## Durable learnings (kept — everything else lives in the plans below)

1. **DIP numbering:** never cite DIP0024 for ChainLocks/InstantSend — DIP0024 defines quorum rotation only.
   ChainLocks active since block 1088640 (Jun 2019); InstantSend has an original Transaction-Locking form plus the
   current deterministic LLMQ form.
2. **Dead-default rule:** `https://api.dash.org` never resolved — removed as DAPI default; `DAPIConfig.address`
   defaults to `None`, resolved per network via `platform/seeds.py` (`DAPIClient.from_network()`). Rule: an
   endpoint entry needs source URL + retrieval date, else empty-list-with-reason — never an invented hostname.
3. **Proofs-greenfield port pattern:** do NOT attempt a greenfield pure-Python proof port in a v0.1;
   ship verifier contract + `FakeVerifier` (tests) + pinned reference-bridge boundary (`platform/proofs.py`),
   prove parsing + verdict plumbing over recorded envelopes (`tests/fixtures/platform/`).
4. **P2PKH-only fence:** offline wallet ships P2PKH-only; P2SH/multisig/script paths raise `PaymentError`
   (explicit deferral, tested) — never silently unsupported.
5. **Seam rule:** transport files (`core/rpc.py`, `platform/dapi.py`) use stdlib + dataclasses only, NO pydantic;
   user-facing typed models live in the facade (pydantic allowed). Enforced by `tests/test_seam.py`; Phase 5 adds
   no `core/` AND no `utils/` imports (shares via `errors.py`/`redact.py` only).
6. **E1 marker-ordering guard:** land `hybrid` + `agent_probe` marker registration in `pyproject.toml` in the SAME
   edit that first uses `-m` selection — pre-registration `-m` runs error, and without `strict-markers` they
   warn-but-pass. New test files declare their marker first.
7. **Src-layout precondition:** `.venv` + editable install (`pip install -e ".[all]"`) is REQUIRED before any
   gate — the `src/` layout does not collect without it (`ModuleNotFoundError: ourdash`).

## Archived artifacts (this folder)

Umbrella `ourdash-sdk_PLAN_04-09-26.md` (CONDITIONAL outer-pvl contract inline) + locked
`ourdash-sdk_SPEC_04-09-26.md` (18 criteria) + `phase-01` … `phase-06` plans. No BLOCKED, no scope smuggled
(gRPC streaming, multisig, X11-in-Python = pause + replan, never EXECUTE expansion).
