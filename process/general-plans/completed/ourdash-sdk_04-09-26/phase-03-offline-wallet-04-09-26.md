# Phase 3 — Offline Wallet Slice + ChainLock/InstantSend Reads

Date: 04-09-26. Status: ⏳ PLANNED. Umbrella: `ourdash-sdk_PLAN_04-09-26.md`. Depends on: Phases 1–2 (✅ VERIFIED).

**Date**: 04-09-26
**Status**: ⏳ PLANNED
**Complexity**: COMPLEX (phase 3 of 6 in phase program)
SPEC criteria covered: **4** (phrase → wallet + address), **5** (inspectable pipeline + bad-submit refusal), **6** (submit + confirm incl. InstantSend/ChainLock), **15-part** (rejected-tx typed error), **16-part** (wallet-side secret safety; full scan gate in Phase 6).

TL;DR: Mnemonic restore → BIP44 (coin type 5) → P2PKH-only offline build/review/sign, with unsigned/malformed submits refused pre-network and per-payment ChainLock/InstantSend finality readable.

## Overview

A developer restores a wallet from a standard recovery phrase, derives a valid receiving address, and moves a payment through separately inspectable build → review → sign → submit steps — with signing explicit and warned, watch-only by default, secrets never logged, and only P2PKH supported (everything script-based is refused with a clear deferral, not silently mishandled).

## Touchpoints

- Write (sole owner): `src/ourdash/core/wallet.py`, `src/ourdash/core/transactions.py`.
- Create: `tests/test_wallet.py`, `tests/test_transactions.py`.
- Read-only: `core/rpc.py` (`DashRPC`), `core/addresses.py` (`derive_p2pkh`, `validate_address`), `errors.py` (`WalletError`, `PaymentError`, `RpcError`), `redact.py`, `tests/conftest.py` (regtest fixture), `mnemonic` + `ecdsa` deps (added in Phase 1 — DO NOT touch `pyproject.toml`). Context: `process/context/all-context.md`, `process/context/tests/all-tests.md`.
- MUST NOT touch: `pyproject.toml`, `src/ourdash/__init__.py`, `core/rpc.py`, `core/addresses.py`, `core/chain.py` (does not exist yet — Phase 4), `core/network.py`, anything under `platform/`, CI, `README.md`, `docs/`.

## Public Contracts (New — Stable After This Phase)

- Wallet restore/derive (`core/wallet.py`): `from_mnemonic(phrase, passphrase="", network="mainnet")` validates the phrase per BIP39 (checksum; invalid → `WalletError`) using the `mnemonic` package wordlist, derives seed via PBKDF2-HMAC-SHA512 (2048 rounds, `mnemonic`+`passphrase` salt), derives the account key per BIP32 and the first receiving address at exactly `m/44'/5'/0'/0/0` (Dash coin type 5), and returns a pydantic `Wallet` object with `watch_only=True` by default. The object exposes `receiving_address(index)` (P2PKH only, via Phase 2 `derive_p2pkh`) and NEVER exposes or logs the phrase/seed/private key through any attribute named in the Phase 1 banned-key set; private material lives only in explicitly-named, redacted accessors. Any signing call emits a `UserWarning` carrying custody wording (not your keys flow — review before signing; default watch-only) and requires an explicit `allow_sign=True`-style opt-in parameter (exact name fixed in EXECUTE, recorded in module docstring; behavior fixed here: no silent signing path exists).
- Signing scope fence: only P2PKH inputs are signable. Any P2SH/multisig/segwit/script input (detected via address kind from Phase 2 or script prefix) raises `PaymentError` with a message stating multisig/script support is deferred beyond v0.1. This fence is asserted by a dedicated test.
- Payment pipeline (`core/transactions.py`): pydantic models `UnsignedTx` (inputs, outputs, fee, network; constructible fully offline), `SignedTx` (adds signatures + txid). `build(inputs, outputs, network)` is pure offline; `review(unsigned_or_signed)` returns a human-readable summary dict (destinations, amounts, fee, fee rate, input count, network — and NEVER any secret); `sign(unsigned_tx, wallet)` requires the wallet's explicit signing opt-in and produces `SignedTx`; `submit(signed_tx, rpc)` refuses `UnsignedTx` input, refuses malformed hex (odd length / non-hex / empty), and refuses network-mismatched payloads with `PaymentError` BEFORE any network call (SPEC criterion 5 bad-submit refusal — assert refusal with the fake server counting zero received requests). Only `SignedTx` reaches `rpc.call("sendrawtransaction", hex)`, and node rejection maps to `PaymentError` chained from `RpcError` (SPEC criterion 15 rejected-tx case).
- Per-payment finality (`core/transactions.py`, owned HERE — distinct from Phase 4's global tip status): `confirm_status(txid, rpc)` returns a pydantic `ConfirmationStatus` with fields `confirmations: int`, `instantlock: bool` (from `gettransaction` `instantlock`/`instantlock_internal` fields), `chainlocked: bool` + `chainlock_height: int | None` (from `getbestchainlock` comparison — ChainLocks active since block 1088640, Jun 2019; no reorg below a locked block), using DIP wording exactly: InstantSend exists in original + current deterministic forms and DIP0024 (quorum rotation) MUST NEVER be cited as inventing either; ChainLocks MUST NEVER be attributed to DIP0024. Special-tx type table (types 0–9) is taken from the canonical registry in the Dash Core v23.1.8 source tree (verified against `dash-cli help` output in EXECUTE and recorded in a module comment with the source named) — NOT from memory.
- Custody/redaction: every wallet/tx `__str__`/`__repr__`, every `review()` output, and every raised error passes through the Phase 1 `redact()` choke point; tests assert the fixed test phrase/password sentinels appear NOWHERE in captured logs, exception strings, or `tmp_path` files written during these scenarios (16-part behavior; the repo-wide scan gate itself lands in Phase 6).

## Blast Radius

Medium: 2 stubs filled, 2 test files created; first use of third-party crypto deps and first Hybrid (regtest) execution. Risk class: medium (key handling). Contained by: offline-first design, P2PKH fence, redaction asserts in every wallet test, disallowed-file list (`git status` check in gates).

## Implementation Checklist

1. Implement `core/wallet.py` exactly per Public Contracts (BIP39 validate → seed → BIP32 → `m/44'/5'/0'/0/0` → Phase 2 `derive_p2pkh`; watch-only default; warned explicit signing opt-in; redacted reprs).
2. Implement `core/transactions.py` exactly per Public Contracts (`UnsignedTx`/`SignedTx`/`ConfirmationStatus` pydantic models; offline `build`; secret-free `review`; P2PKH-only `sign`; pre-network refusal in `submit`; `confirm_status` with correct DIP wording).
3. Write `tests/test_wallet.py` (Fully-Automated): published BIP39 vector restores to the expected seed prefix and derives the recorded first address; wrong checksum phrase → `WalletError`; watch-only default asserted; signing without opt-in refused; signing emits custody `UserWarning`; multisig/P2SH sign attempt → `PaymentError` deferral; sentinel secret strings absent from `caplog`/`capsys`/exception text.
4. Write `tests/test_transactions.py` (Fully-Automated part): deterministic build vector (same inputs → same unsigned hex); `review()` content asserts + secret-absence asserts; submit-unsigned → `PaymentError` with zero fake-server hits; submit-malformed → `PaymentError`; node-rejects-raw-tx (fake server error) → `PaymentError` chaining code; `confirm_status` parsing against canned `gettransaction`/`getbestchainlock` payloads incl. pre-ChainLock-era semantics.
5. Hybrid part (same files, `hybrid` mark, regtest fixture from Phase 1): fund a regtest address, build → sign → `submit` a real signed tx, mine a block, assert `confirm_status` shows confirmations ≥1; assert ChainLock/InstantSend fields parse (values may be false on regtest — assert shape + types, not truthiness; document why in-test).
6. Record the special-tx 0–9 registry + `dash-cli help` allowlist source (Core v23.1.8) in a `transactions.py` module comment with retrieval date; DIP0024-never-for-ChainLocks/InstantSend wording asserted by a test scanning the module docstring/comments for the banned attribution (simple, explicit, prevents the exact known documentation error).
7. Run the full gate set below; fix until green.

## Test Gates (Level-1 — Exact Commands)

- `pytest tests/test_wallet.py tests/test_transactions.py -vv -m "not hybrid"` — all pass, offline.
- `pytest tests/test_wallet.py tests/test_transactions.py -vv -m hybrid` — passes with regtest `dashd` present; cleanly skips without it (never fails for missing binary).
- `pytest -q -m "not hybrid and not agent_probe"`, `ruff check src tests`, `black --check src tests`, `mypy src` — all clean.
- `git status --porcelain` — shows ONLY `core/wallet.py`, `core/transactions.py`, `tests/test_wallet.py`, `tests/test_transactions.py`.
- New vectors: BIP39 published vector (phrase → seed → `m/44'/5'/0'/0/0` address, recorded in-test with source named); deterministic build vector; canned finality payloads.

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| recovery-phrase vector → valid receiving address | Fully-Automated (`test_wallet.py`) | 4 |
| offline build-and-sign + bad-submit refusal (zero network hits) | Fully-Automated (`test_transactions.py`) | 5 |
| signed regtest payment submits + ChainLock/InstantSend status readable | Hybrid (regtest fixture) | 6 |
| node-rejected tx → distinct `PaymentError` (no secrets) | Fully-Automated (fake server) | 15-part |
| sentinel secrets absent from all captured outputs | Fully-Automated (redaction asserts) | 16-part |

## Acceptance Criteria

- Published BIP39 vector restores to the expected seed and derives the recorded first address at `m/44'/5'/0'/0/0`; bad-checksum phrases raise `WalletError`.
- Build → review → sign are separately observable; `review()` output is secret-free; wallet defaults to watch-only and signing requires explicit warned opt-in.
- Unsigned/malformed submits raise `PaymentError` with zero fake-server hits; node rejection chains the node code; P2SH/multisig sign attempts raise the deferral `PaymentError`.
- Hybrid regtest submit confirms with readable ChainLock/InstantSend status; module DIP wording passes the banned-attribution scan.

## Exit Criteria

- All Test Gates green; P2PKH-only fence, watch-only default, warned signing, and DIP-wording guard all observable in tests.
- Handoff note written. Status may move to ✅ VERIFIED when gates pass (Hybrid green where `dashd` exists, clean skip otherwise).

## Resume and Execution Handoff

- Next phase: `phase-04-core-reads-04-09-26.md` (general Core reads + health; consumes `DashRPC` + regtest fixture patterns from this phase; MUST NOT edit `wallet.py`/`transactions.py`).
- This phase leaves behind: offline wallet slice, payment pipeline, per-tx finality reader, secret-safe behavior baseline.
- Known gaps carried forward: global ChainLock-tip + masternode health surface (Phase 4); repo-wide secret-scan gate (Phase 6).

## Test Infra Improvement Notes

(none identified yet)

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)

## Phase Completion Rules

Per umbrella: offline vectors + refusal proofs + Hybrid submit/confirm + all four gates green. Agent-Probe testnet submit is deferred to the Phase 6 docs walkthrough (criterion 6 testnet leg), recorded as pending in the handoff. No separate user confirmation is needed to mark this phase ✅ VERIFIED once gates pass; user confirmation of the end-to-end payment happens in the Phase 6 walkthrough.

Execute-anchor note: this file is one of the program's supporting phase files (primary execute anchor above); execute phases strictly in order 1→6.

Next Step: review this phase plan, then say `ENTER EXECUTE MODE` to implement it exactly as specified.
