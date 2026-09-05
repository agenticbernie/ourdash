# Phase 2 — Addresses (Validation + Network/Kind)

Date: 04-09-26. Status: ⏳ PLANNED. Umbrella: `ourdash-sdk_PLAN_04-09-26.md`. Depends on: Phase 1 (✅ VERIFIED).

**Date**: 04-09-26
**Status**: ⏳ PLANNED
**Complexity**: COMPLEX (phase 2 of 6 in phase program)
SPEC criteria covered: **7** (validate with network + kind), **8** (wrong-network caught).

TL;DR: Pure-offline address validation against fixed Dash version bytes — valid/invalid plus network plus kind, with wrong-network rejection — no keys, no network calls.

## Overview

Any Dash address input returns, in plain terms: valid or invalid, which network (mainnet / testnet / regtest / devnet), and which kind (P2PKH standard / P2SH multisig-script) — before any funds move. Testnet addresses presented for mainnet use (and vice versa) are rejected.

## Touchpoints

- Write (sole owner): `src/ourdash/core/addresses.py`, `src/ourdash/utils/__init__.py`.
- Create: `tests/test_addresses.py`.
- Read-only: `src/ourdash/errors.py` (`AddressError`), `src/ourdash/redact.py`, locked SPEC constraints (address facts), Dash Core v23.1.8 `chainparams.cpp` (source of version bytes). Context: `process/context/all-context.md`, `process/context/tests/all-tests.md`.
- MUST NOT touch: `pyproject.toml`, `src/ourdash/__init__.py`, `core/rpc.py`, `core/wallet.py`, `core/transactions.py`, `core/network.py`, anything under `platform/`, CI, `README.md`, `docs/`.

## Public Contracts (New — Stable After This Phase)

- Version bytes (fixed, asserted in tests — these are the Dash Core `chainparams.cpp` `base58Prefixes[PUBKEY_ADDRESS]` / `[SCRIPT_ADDRESS]` values): mainnet P2PKH `0x4c` (76), testnet P2PKH `0x8c` (140), mainnet P2SH `0x10` (16), testnet P2SH `0x13` (19). regtest and devnet reuse the testnet prefixes (documented in module docstring; asserted by constructing round-trip vectors, not by memorized addresses).
- Checksum rule: Base58Check with 4-byte double-SHA-256 checksum (SHA-256 of SHA-256, first 4 bytes), 21-byte payload (1 version byte + 20-byte hash).
- `validate_address(addr, expected_network=None)` behavior: returns a pydantic `AddressInfo` model with fields `valid: bool`, `network` (one of `mainnet|testnet|regtest|devnet`; testnet-family prefixes report the specific network only when disambiguated by `expected_network`, otherwise `testnet` family label — exact rule: without `expected_network`, a testnet-prefix address reports `testnet`; with `expected_network="regtest"` or `"devnet"` it validates the prefix against that network and reports it), `kind` (`p2pkh|p2sh`), and `reason` (machine-readable string such as `ok|bad_charset|bad_length|bad_checksum|wrong_network|unknown_prefix` when invalid). When `expected_network` is given and the prefix belongs to a different family, return `valid=False, reason="wrong_network"` (SPEC criterion 8) — never raise for a merely wrong address; raise `AddressError` only for non-string / empty input types.
- `derive_p2pkh(pubkey_hash20, network)` behavior: builds the address for the given 20-byte hash and network using the table above (used by Phase 3 wallet derivation; implemented here so version-byte knowledge lives in exactly one module).
- `utils` helpers (hashing/checksum only, no address semantics): `sha256d(data)`, `b58check_encode(payload)`, `b58check_decode(addr)` raising `AddressError` on charset/length/checksum failure. X11 is explicitly NOT implemented here or anywhere in v0.1 (eleven-hash chain is block-hashing only; transactions/Merkle/addresses use SHA-256/RIPEMD-160 via `hashlib` — record this boundary in the `utils` docstring).

## Blast Radius

Tiny: 2 files written (1 stub filled, 1 stub rewritten), 1 test file created. Pure functions, no I/O, no network. Risk class: low. The load-bearing risk is wrong version bytes — contained by asserting the four constants against Core `chainparams.cpp` values in-test and by round-trip vectors.

## Implementation Checklist

1. Implement `utils` hashing/checksum helpers exactly per Public Contracts (`hashlib`-only; no new dependencies — `pyproject.toml` MUST NOT be touched).
2. Implement `core/addresses.py`: version-byte table, `AddressInfo` pydantic model, `validate_address` with `expected_network` semantics, `derive_p2pkh`. Module docstring cites Dash crypto vs Plotly Dash disambiguation + Core v23.1.8 `chainparams.cpp` as source. No `pydantic` in transport files rule unaffected (facade modules MAY import pydantic; `test_seam.py` still green since `rpc.py`/`dapi.py` untouched).
3. Write `tests/test_addresses.py` (Fully-Automated) covering: the four version-byte constants; round-trip construct-then-validate for every (network × kind) cell; tampered-checksum rejection; bad-charset/short/long rejection; wrong-network matrix (mainnet↔testnet both directions with `expected_network` set → `valid=False, reason="wrong_network"`); `expected_network=None` family-label rule; non-string input → `AddressError`.
4. Cross-check procedure (no invented vectors): generate the round-trip vectors with this implementation, then confirm at least two constructed testnet/mainnet P2PKH addresses against an independent reference (regtest `dashd` `getnewaddress` + `validateaddress`, or the pinned JS toolkit) and record the confirmed addresses as fixed vectors in the test file with the reference named in a comment.
5. Run the full gate set below; fix until green.

## Test Gates (Level-1 — Exact Commands)

- `pytest tests/test_addresses.py -vv` — all pass, offline.
- `pytest -q -m "not hybrid and not agent_probe"` — full unit suite green (no regressions).
- `ruff check src tests`, `black --check src tests`, `mypy src` — all clean.
- New vectors: (network × kind) round-trip vectors + ≥2 independently cross-checked fixed addresses recorded in-test.

## Verification Evidence

| Gate / Scenario | Strategy | Proves SPEC criterion |
|---|---|---|
| address-vector scenario (valid/invalid + network + kind on fixed vectors) | Fully-Automated (`test_addresses.py`) | 7 |
| wrong-network scenario (both directions, pre-use rejection) | Fully-Automated (`test_addresses.py`) | 8 |

## Acceptance Criteria

- The four version-byte constants (`0x4c/0x8c/0x10/0x13`) are asserted in-test against their Core `chainparams.cpp` meaning.
- Round-trip construct-then-validate passes for every (network × kind) cell; tampered checksums and bad charsets are rejected.
- Wrong-network matrix (mainnet↔testnet, both directions, `expected_network` set) returns `valid=False, reason="wrong_network"`.
- ≥2 constructed addresses are cross-checked against an independent reference and recorded as fixed vectors with the reference named.

## Exit Criteria

- All Test Gates green; no file outside the Touchpoints list modified (`git status` shows only the 3 paths).
- `validate_address` observable behaviors match Public Contracts exactly, including the `expected_network=None` family-label rule.
- Status may move to ✅ VERIFIED when gates pass.

## Resume and Execution Handoff

- Next phase: `phase-03-offline-wallet-04-09-26.md` (imports `derive_p2pkh` + `validate_address` + `AddressError`; owns `wallet.py`/`transactions.py`).
- This phase leaves behind: version-byte truth in exactly one module, offline validation facade, hash helpers.
- Known gaps carried forward: first-receiving-address derivation from a mnemonic is proven in Phase 3, not here.

## Test Infra Improvement Notes

(none identified yet)

## Validate Contract

(placeholder — vc-validate-agent writes this section before EXECUTE)

## Phase Completion Rules

Per umbrella: vector suite + wrong-network matrix + all four gates green. No separate user confirmation step is needed for this offline-logic phase; mark ✅ VERIFIED when gates pass.

Execute-anchor note: this file is one of the program's supporting phase files (primary execute anchor above); execute phases strictly in order 1→6.

Next Step: review this phase plan, then say `ENTER EXECUTE MODE` to implement it exactly as specified.
