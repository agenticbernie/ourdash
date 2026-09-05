# Platform proof fixtures (recorded envelopes)

Hybrid enabler for Phase 5: Fully-Automated tests parse these fixtures
through `FakeVerifier` + models, so the suite stays offline while anchored
to real response shapes.

## Capture provenance

- Source endpoint: `https://seed-1.testnet.networks.dash.org:1443`
  (testnet seed-1 — the seed named by BOTH plan sources: the docs.dash.org
  Platform "Connect to a network" tutorial and `@dashevo/dapi-client@4.1.1`
  `lib/networkConfigs.js`).
- Capture date: 2026-09-05. Method: live testnet gRPC (`Platform` service,
  `platform.proto` from `dashpay/platform` master) with `prove=True` for the
  proof envelopes and `prove=False` for the data blobs.
- Chain anchor at capture: `height=558061`, `core_chain_locked_height=1547601`,
  `epoch=18671`, `chain_id=dash-testnet-51` (in each file's `metadata`).

## Files

| File | Endpoint | Kind |
|---|---|---|
| `getdocuments_dpns_testnet.json` | `getDocuments` (DPNS `domain`, limit 2) | REAL — 2 domain docs (`mvp-mmlv0l8o.dash`, `test-invite-21.dash`) + real GroveDB proof |
| `getdatacontract_dpns_testnet.json` | `getDataContract` (DPNS `GWRSAVFMjXx8HpQFaNJMqBV7MBgMK4br5UESsB4S31Ec`) | REAL — contract descriptor + real proof |
| `getidentity_quantumexplorer_testnet.json` | `getIdentity` (`BNnn19SAJZuvsUu787dMzPDXASwuCrm4yQ864tEpQFvo`, owner of `quantumexplorer.dash` per the docs tutorial) | REAL — identity descriptor + real proof |
| `gettoken_synthetic_pending_recapture.json` | `getTokenContractInfo` + `getIdentitiesTokenBalances` | SYNTHETIC (`"synthetic": "synthetic-pending-recapture"`) — no testnet token contract is publicly documented (token tutorials register per-user contracts); shape mirrors the proto fields, ids are sha256-derived, proof bytes are placeholders. Recapture from testnet in the Phase 6 walkthrough. |

## Binary transcription notes (real fixtures)

DPP serializes descriptors as version-prefixed binary, not JSON. The `data`
sections were transcribed at these verified offsets:

- Documents: `[prefix:2][0x00 0x00][id:32][owner:32][3× u64-BE ms timestamps][0x00 separator][len-prefixed label, normalized label, parent, normalized parent][0x00][0x21 0x01][records identity:32]`. Labels are
  byte-verified against the raw blobs (tests assert this); `$id`/`owner_id`/
  `records_identity_id` are offset-derived base58 transcriptions.
- Data contract: `[ver:1][id:32][version u32le][owner:32]` — the id slice was
  byte-match-verified against the requested contract id; `document_types`
  (`domain`, `preorder`) read as ASCII from the blob (tests assert presence).
- Identity: `[ver:1][id:32][balance u64le][revision:1 byte][4 × (0x21 + 33-byte
  compressed key + 9 metadata bytes)]` — id byte-match-verified; balance 4,
  revision 0.

## Known gaps

- `contested` is absent from the transcribed name fields: contest state needs
  a `getContestedResources` read, which v0.1 does not perform. `resolve_dpns`
  reports `contested=False` unless the envelope carries the flag.
- Token fixture is synthetic (see above) — recapture is a Phase 6
  walkthrough item.
- Proofs are REAL GroveDB proofs but v0.1 checks them structurally
  (`FakeVerifier`); cryptographic verification is the `ReferenceBridgeVerifier`
  boundary (`proofs.py`).
