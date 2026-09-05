# First testnet payment

Dash here means Dash crypto from dash.org — not Plotly Dash.

This guide moves real (valueless) testnet tDASH through the offline
pipeline: fund → build → review → sign → submit → `confirm_status`.
It assumes `install.md` is green. Every session below was executed
verbatim on testnet.

> Custody warning: the wallet defaults to watch-only. Signing spends
> real funds on mainnet — on testnet the coins are valueless, but build
> the review-first habit here. Inspect `review()` output and only sign
> what you verified. Never paste a recovery phrase into a chat, ticket,
> or log.

## Fund a testnet address

Restore the (public, valueless) tutorial wallet on `testnet` and read
its first receiving address. This uses the well-known BIP39 test vector
— use your own phrase for anything that matters:

```python
from ourdash.core.wallet import Wallet

w = Wallet.from_mnemonic(
    "abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon about",
    network="testnet",
)
print("ADDR0:", w.receiving_address(0))
print("ADDR1:", w.receiving_address(1))
print("PATH:", w.derivation_path(0))
print("WATCH:", w.watch_only)
```

Expected output:

```text
ADDR0: yYvm9nJUoaC856FnTQNKePUP8A8vaB5ehS
ADDR1: yMFVoBx7x1SA4kYLcW5y1p58EijmHKo5MN
PATH: m/44'/5'/0'/0/0
WATCH: True
```

Fund ADDR0 from the Dash testnet faucet linked from docs.dash.org
(testnet coins have no value). Wait for one confirmation, then continue.
`WATCH: True` confirms the wallet holds no spendable key until you
explicitly opt into signing.

## Build

Assemble the payment fully offline — no node, no network. Point the
input at your funded UTXO (txid/vout from the faucet payout):

```python
from ourdash.core.transactions import build

unsigned = build(
    [{
        "txid": "0123456789abcdef" * 4,  # replace with your UTXO txid
        "vout": 0,                        # replace with your UTXO vout
        "amount_duffs": 100_000,
        "address": "yYvm9nJUoaC856FnTQNKePUP8A8vaB5ehS",
    }],
    [{"address": "yMFVoBx7x1SA4kYLcW5y1p58EijmHKo5MN", "amount_duffs": 90_000}],
    network="testnet",
)
```

`build` validates both ends before returning: empty inputs, non-P2PKH
addresses (multisig/script are refused with an explicit deferral), and
outputs exceeding inputs all raise `PaymentError` here — never
mid-broadcast.

## Review

> Custody warning: read this summary before signing. If any address or
> amount surprises you, stop — do not sign.

```python
import json
from ourdash.core.transactions import review

print(json.dumps(review(unsigned), indent=2))
```

Expected output (your txid and addresses will differ; the shape will
not):

```json
{
  "kind": "unsigned",
  "network": "testnet",
  "input_count": 1,
  "output_count": 1,
  "inputs": [
    {
      "txid": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "vout": 0,
      "amount_duffs": 100000,
      "address": "yYvm9nJUoaC856FnTQNKePUP8A8vaB5ehS"
    }
  ],
  "destinations": [
    {
      "address": "yMFVoBx7x1SA4kYLcW5y1p58EijmHKo5MN",
      "amount_duffs": 90000
    }
  ],
  "total_in_duffs": 100000,
  "total_out_duffs": 90000,
  "fee_duffs": 10000,
  "fee_rate_duffs_per_vbyte": 52.083333333333336,
  "txid": null
}
```

The summary is secret-free by construction: no phrase, passphrase, or
key bytes — safe to paste into a bug report.

## Sign

> Custody warning: this is the point of no return for custody. The call
> below requires the explicit keyword-only `allow_sign=True` and always
> emits a `UserWarning` — there is no silent signing path.

```python
from ourdash.core.transactions import sign

signed = sign(unsigned, w, allow_sign=True)
print("TXID:", signed.txid)
print("RAWLEN:", len(signed.raw_hex))
```

Expected output (plus one `UserWarning` carrying the custody text):

```text
TXID: 6bec3bafddc331a55ef76fe503239ddf4582691a53aad5e5b058df6600ab8253
RAWLEN: 386
```

Without `allow_sign=True`, `sign` raises `PaymentError` and touches no
key material.

## Submit

Broadcast the signed bytes through your own node (testnet). Unsigned or
malformed payloads are refused with `PaymentError` BEFORE any network
call:

```python
from ourdash.core.rpc import DashRPC, DashRPCConfig
from ourdash.core.transactions import submit

rpc = DashRPC(DashRPCConfig.from_env())  # testnet URL + creds, see connect.md
txid = submit(signed, rpc)
assert txid == signed.txid
print("SUBMITTED:", txid)
```

Expected output once your input UTXO is funded and confirmed:

```text
SUBMITTED: <the TXID printed at sign time>
```

A node rejection (bad UTXO, fee too low) arrives as `PaymentError`
chained from the node error — see `troubleshooting.md`.

## Confirm

Read per-payment finality — confirmations plus InstantSend/ChainLock
state:

```python
from ourdash.core.transactions import confirm_status

status = confirm_status(txid, rpc)
print(status)
```

Expected shape (values move as the chain locks the payment — yours will
show real numbers where `...` stands below):

```text
ConfirmationStatus(confirmations=..., instantlock=..., chainlocked=..., chainlock_height=...)
```

`chainlocked=True` means a quorum-signed ChainLock covers your
payment's block — no reorganization below it. `instantlock=True`
reports a deterministic InstantSend lock.

Next: `first-platform-read.md`, or `troubleshooting.md` when any step
above surprises you.
