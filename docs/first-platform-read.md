# First Platform read

Dash here means Dash crypto from dash.org — not Plotly Dash.

This guide reads Dash Platform data with proof verdicts: discover a seed,
run Layer-1 reads live on testnet, query documents with a `CHECKED`
verdict, and learn the explicit trusted-node fallback. It assumes
`install.md` is green. Every session below was executed verbatim (live
outputs recorded 2026-09-05; your tip hash will be newer — the shape is
what matters).

## Discover a seed

The SDK ships NO default Platform URL (a dead placeholder must never
ship). Endpoints resolve per network from documented seeds in
`ourdash.platform.seeds`:

```python
from ourdash.platform.dapi import DAPIClient
from ourdash.platform.seeds import seeds_for

client = DAPIClient.from_network("testnet")
print("ADDRESS:", client.config.address)
for seed in seeds_for("testnet")[:2]:
    print(seed.address, "|", seed.interface)
```

Expected output:

```text
ADDRESS: https://seed-1.testnet.networks.dash.org:1443
https://seed-1.testnet.networks.dash.org:1443 | json-rpc
https://seed-2.testnet.networks.dash.org:1443 | json-rpc
```

`from_network` dials the FIRST documented seed. Networks with no
documented seed raise `DAPIError` with guidance instead of guessing —
pass `DAPIConfig(address=...)` explicitly in that case. Prefer
constructing with no address at all over inventing one: bare
`DAPIClient()` refuses every call with `DAPIError` until you choose.

## First Layer-1 reads

v0.1 speaks the HTTP/JSON surface: best block hash, block hash by
height, and a composed status snapshot (broadcast is gRPC-only upstream
and raises a loud `DAPIError` instead of silently degrading):

```python
tip = client.get_best_block_hash()
print("TIP:", tip)
print("STATUS:", client.get_status())
print("H0:", client.get_block_hash(0))
```

Expected output (recorded 2026-09-05):

```text
TIP: 48d6060f74d5e66a9406bd23a45e46465d95a9038b1789557bf69b7e1f010000
STATUS: {'best_block_hash': '48d6060f74d5e66a9406bd23a45e46465d95a9038b1789557bf69b7e1f010000'}
H0: 00000bafbc94add76cb75e2ec92894837288a481e5c005f6563d91623bf8bc2c
```

H0 is the testnet genesis hash — a stable anchor you can assert in
your own smoke tests.

## Documents query with a verdict

Application-data reads go through the `Drive` facade. v0.1 ships no
Platform query transport (DAPI queries are gRPC-only upstream, deferred),
so live use injects a `fetcher` callable `(endpoint, request) ->
envelope`; the suite ships recorded testnet envelopes under
`tests/fixtures/platform/` so this whole session replays offline:

```python
import json
from ourdash.platform.drive import Drive, DPNS_TESTNET_CONTRACT_ID
from ourdash.platform.proofs import FakeVerifier

envelope = json.load(open("tests/fixtures/platform/getdocuments_dpns_testnet.json"))
drive = Drive(client, verifier=FakeVerifier(), fetcher=lambda endpoint, request: envelope)
result = drive.query_documents(DPNS_TESTNET_CONTRACT_ID, "domain", limit=10)
print("VERDICT:", result.verdict)
print("NOTE:", result.proof_note)
print("NDOCS:", len(result.data))
print("DOC0:", result.data[0].to_dict())
```

Expected output:

```text
VERDICT: ProofVerdict.CHECKED
NOTE: verifier FakeVerifier accepted the proof
NDOCS: 2
DOC0: {'doc_id': 'cVnj3JkCiQegDzUMpDMgHFhen5kP6RkoXbNQqb8NdFm', 'contract_id': 'GWRSAVFMjXx8HpQFaNJMqBV7MBgMK4br5UESsB4S31Ec', 'doc_type': 'domain', 'fields': {'label': 'mvp-mmlv0l8o', 'normalized_label': 'mvp-mm1v0180', 'parent_domain_name': 'dash', 'normalized_parent_domain_name': 'dash', 'owner_id': 'E3hcnTxGaB6KnaaQ9cyho89TtH32RUzZc8bu3fLese6r', 'records_identity_id': 'Bfe6EDSywjtXx2HPu4kTTEkWDcVECXcGb4aTw43FL2dx', 'created_at_ms': 1773222732845, 'updated_at_ms': 1773222732845}}
```

`FakeVerifier` checks proof PLUMBING (well-formed envelope proof →
`CHECKED`), never proof cryptography. `Drive` defaults to
`ReferenceBridgeVerifier` (fail-closed: raises `ProofUnavailableError`
when the bridge binary is absent, never default `CHECKED`); the
`FakeVerifier` below is passed explicitly for offline replay. Swap in
`ReferenceBridgeVerifier` (bridge to the pinned `@dashevo/dapi-client`
reference) for real checks — see `platform/proofs.py` for the pin and
invocation schema.

## Verdict interpretation

Every `Drive` read returns a `ProvenResult` pairing data with its
trust verdict:

| Verdict | Meaning | When you see it |
|---|---|---|
| `CHECKED` | a verifier accepted the response proof | default path (`trust_node=False`) with proof material present |
| `UNCHECKED` | proof NOT verified — treat as untrusted gossip | ONLY via explicit `trust_node=True` (always warns) |

With no proof material and no opt-in, reads raise
`ProofUnavailableError` — never silent trust, never fabricated data.
`ProvenResult.to_dict()` gives a plain-object view (stdlib types only)
for your own tooling.

## Explicit trusted-node fallback

When you consciously accept an unverified answer (dev loop, known-good
local node), say so out loud — keyword-only, never positional:

```python
import warnings
from ourdash.platform.drive import Drive

drive = Drive(client, fetcher=lambda endpoint, request: {"data": {"documents": []}})
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    result = drive.query_documents("c", "domain", trust_node=True)
    print("UNCHECKED:", result.verdict, "| WARN:", str(caught[0].message)[:100])
```

Expected output:

```text
UNCHECKED: ProofVerdict.UNCHECKED | WARN: Drive.query_documents: trust_node=True: this answer is UNCHECKED (proof not verified); use the defau
```

Passing the flag positionally (`query_documents("c", "domain", True)`)
raises `TypeError` by construction — it would bind to `filter`, not to
the keyword-only flag, so the SDK refuses the ambiguity outright.

Same-verdict reads exist for contracts (`get_data_contract`),
identities (`get_identity`), DPNS names (`resolve_dpns`), and tokens
(`get_token_rules`, `get_token_transfers`). When anything here fails,
see `troubleshooting.md`.
