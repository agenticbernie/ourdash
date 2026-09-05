# Troubleshooting

Dash here means Dash crypto from dash.org — not Plotly Dash.

One section per typed error: symptom → cause → fix, each with the exact
session that produces it. All sessions below were executed verbatim.
Every `ourdash` error subclasses `OurdashError`, so `except
OurdashError` catches the whole family when you want one handler.

## ConfigError

Symptom:

```text
REMOTE: refusing non-loopback RPC host '192.0.2.10'; pass remote_ok=True to opt in explicitly
```

Cause: you pointed `DashRPC` at a non-loopback host without opting in.
The SDK refuses remote endpoints by default so a typo'd host never
sprays credentials at a stranger.

Fix: stay on loopback (127.0.0.1, ::1, localhost), or pass
`remote_ok=True` explicitly when you mean it:

```python
from ourdash.core.rpc import DashRPC, DashRPCConfig

remote = DashRPC(DashRPCConfig(host="192.0.2.10", remote_ok=True))
```

Related: `BADWALLET: invalid wallet selection '../evil'` — wallet names
containing `/` or `..` are rejected before any call. Rename the wallet
to a plain label.

## RpcAuthError

Symptom:

```text
AUTH: RpcAuthError | RPC error: RPC call rejected: bad credentials (HTTP 401)
```

Cause: the node answered HTTP 401/403 — wrong rpcuser/rpcpassword
(or stale cookie). Never retried: retrying bad credentials only locks
accounts.

Fix: re-export the right `OURDASH_RPC_USER` / `OURDASH_RPC_PASSWORD`
(see `connect.md`), or point `cookie_path` at the node's live cookie
file. Confirm with `dash-cli -rpcwallet=... getblockcount` outside the
SDK first.

## RpcConnectionError

Symptom:

```text
CONN: RpcConnectionError | RPC error: RPC call could not reach the node
```

Cause: nothing listening at host:port (node down, wrong port, firewall).
Retried with backoff, then raised.

Fix: check the node is up and the port matches the network (`9998`
mainnet, `19998` testnet, `19898` regtest, `19788` devnet). `telnet
127.0.0.1 19998` failing the same way proves it is not the SDK.

## RpcTimeoutError

Symptom:

```text
TIMEOUT: RpcTimeoutError | RPC error: RPC call timed out after 0.2s
```

Cause: the node accepted the connection but did not answer within
`timeout_s`. Never retried — a slow node may still execute the call.

Fix: raise `timeout_s` for heavy calls (masternode list, rescans), and
treat wallet-state calls as possibly-executed before retrying by hand.

## WalletError

Symptom:

```text
WALLET: WalletError | invalid recovery phrase (wordlist or checksum failure)
```

Cause: the phrase is not a checksum-valid BIP39 mnemonic (typo, wrong
word order, non-English wordlist without opting in).

Fix: re-enter the phrase carefully — note the SDK never echoes your
input back, so a "did I mistype?" check means retyping, not reading an
error. Related refusal: `private_key_bytes` / `sign` without the exact
keyword-only `allow_sign=True` raises `WalletError` by design — the
wallet is watch-only until you explicitly opt out of safety.

## PaymentError

Symptom:

```text
SUBMIT: PaymentError | refusing to submit an unsigned transaction: build → review → sign first, then submit the SignedTx
```

Cause: `submit` received an `UnsignedTx` (or malformed hex). The
pre-network refusal fires BEFORE any RPC so a half-built payment can
never half-broadcast.

Fix: complete the pipeline in order — `build` → `review` → `sign` →
`submit` (see `first-payment-testnet.md`). Other `PaymentError`
triggers and their fixes: outputs exceeding inputs (rebalance amounts),
non-P2PKH address (v0.1 signs P2PKH only — multisig/script are an
explicit deferral, not a bug), node rejection of a signed tx (read the
chained node message: usually a spent UTXO or too-low fee).

## AddressError

Symptom: `validate_address` returns `valid=False` instead of raising
(wrong-network is data, not an exception):

```python
from ourdash.core.addresses import validate_address

addr = "XoJA8qE3N2Y3jMLEtZ3vcN42qseZ8LvFf5"
print("WRONGNET:", validate_address(addr, expected_network="testnet"))
print("OK:", validate_address(addr))
```

Expected output:

```text
WRONGNET: valid=False network='mainnet' kind='p2pkh' reason='wrong_network'
OK: valid=True network='mainnet' kind='p2pkh' reason='ok'
```

Cause: a mainnet (`X...`) address on a testnet path, or vice versa
(`y...`). Only non-string/empty input raises AddressError.

Fix: match the address family to the network (`0x4c` mainnet P2PKH vs
`0x8c` testnet P2PKH). Branch on the reason field, not on exception type.

## DAPIError

Symptom:

```text
DAPI: DAPIError | DAPI client has no address (no default ships); use DAPIClient.from_network(network) or pass DAPIConfig(address=...) explicitly
```

Cause: bare `DAPIClient()` with no seed resolution. No default URL
ships — the old api.dash.org placeholder never resolved and must
never be configured.

Fix: `DAPIClient.from_network("testnet")` for discovery (see
`first-platform-read.md`), or `DAPIConfig(address=...)` with your own
endpoint. Same error class covers malformed envelopes and the loud
`broadcast_transaction` refusal (submit is gRPC-only upstream —
deferred in v0.1, never silently downgraded).

## ProofError and ProofUnavailableError

Symptom:

```text
PROOF: ProofUnavailableError | no verifiable proof is available for 'getDocuments': v0.1 ships no Platform query transport (DAPI queries are gRPC-only ...
```

Cause: a `Drive` read with no `fetcher` and no proof material. The SDK
refuses silent trust — this error IS the safety feature working.

Fix: pass a `fetcher` (recorded fixtures under
`tests/fixtures/platform/` replay offline; a gRPC-backed fetcher lands
with the transport), or consciously accept `trust_node=True` and handle
the `UNCHECKED` verdict as gossip. `ProofError` (sibling) means a
verifier actively REJECTED the proof — do not retry that read against
the same source; investigate the source.

## Secrets-safety rules

These are enforced by `tests/test_secrets.py` — the secret-scan gate.
If you touch wallet, transport, or error paths, keep all five true:

1. Recovery phrases, passphrases, passwords, cookie secrets, and key
   bytes never reach logs, `str(exc)`, `repr(obj)`, or files the SDK
   writes. All rendering passes through the `redact.py` choke point.
2. Wallets are watch-only by default. Key material leaves ONLY via
   `private_key_bytes(..., allow_sign=True)` / `sign(..., allow_sign=True)`,
   each emitting a `UserWarning` with custody wording.
3. Config `repr`s mask credential fields (`[REDACTED]`) — a pasted
   traceback still leaks nothing.
4. Cookie files stay yours: mode `0600`, never committed, never pasted.
   The SDK reads them; it never writes them anywhere.
5. New hex-looking test vectors belong in `tests/`, never in `src/` —
   the source-literal scan fails on 33+ hex-char literals, valued
   `rpcpassword=`, and the dead api.dash.org placeholder.
