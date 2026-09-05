# Connect `ourdash` to your node

Dash here means Dash crypto from dash.org — not Plotly Dash.

This guide connects `DashRPC` to a Dash Core node (`dashd`) using
environment variables only — secrets never appear in code, logs, or error
text. It assumes `install.md` is green. Every session below was executed
verbatim.

## Loopback default

A default client points at your own machine and refuses anything else.
No credentials are needed to construct it:

```python
from ourdash.core.rpc import DashRPC

print(DashRPC().config)
```

Expected output (user/password are masked even when empty):

```text
DashRPCConfig({'host': '127.0.0.1', 'port': 9998, 'user': '[REDACTED]', 'password': '[REDACTED]', 'timeout_s': 30.0, 'wallet': None, 'cookie_path': '[REDACTED]', 'remote_ok': False})
```

Port `9998` is mainnet RPC (`19998` testnet, `19898` regtest, `19788`
devnet). Calls still need credentials — construction alone sends nothing.

## Credentials from the environment

The SDK reads exactly four names (and nothing else): `OURDASH_RPC_URL`,
`OURDASH_RPC_USER`, `OURDASH_RPC_PASSWORD`, `OURDASH_RPC_WALLET`.
Export them in your shell, then build the config:

```console
$ export OURDASH_RPC_URL=http://127.0.0.1:19998
$ export OURDASH_RPC_USER=alice
$ export OURDASH_RPC_PASSWORD=s3cret
$ export OURDASH_RPC_WALLET=testwallet
$ .venv/bin/python -c "
from ourdash.core.rpc import DashRPCConfig
print(DashRPCConfig.from_env())
"
DashRPCConfig({'host': '127.0.0.1', 'port': 19998, 'user': '[REDACTED]', 'password': '[REDACTED]', 'timeout_s': 30.0, 'wallet': 'testwallet', 'cookie_path': '[REDACTED]', 'remote_ok': False})
```

Note the password renders as `[REDACTED]` — that is the `redact.py`
choke point working, not a missing value. Alternatively, point
`cookie_path` at your node's live cookie file instead of user/password.

## Remote hosts need opt-in

A non-loopback host without explicit consent is refused before any
network use:

```python
from ourdash.core.rpc import DashRPC, DashRPCConfig
from ourdash.errors import ConfigError

try:
    DashRPC(DashRPCConfig(host="192.0.2.10"))
except ConfigError as exc:
    print("REMOTE:", exc)
```

Expected output:

```text
REMOTE: refusing non-loopback RPC host '192.0.2.10'; pass remote_ok=True to opt in explicitly
```

To deliberately dial a remote node, pass `remote_ok=True` yourself —
the SDK never guesses:

```python
remote = DashRPC(DashRPCConfig(host="192.0.2.10", remote_ok=True))
```

## Wallet selection

Multi-wallet nodes (Core 18+) are selected per client via `wallet`,
which routes calls to that wallet's `-rpcwallet` endpoint. The caller's
client is never mutated:

```python
from ourdash.core.rpc import DashRPC, DashRPCConfig

cfg = DashRPCConfig(host="127.0.0.1", port=19998, user="alice",
                    password="s3cret", wallet="testwallet")
print("WALLET-URL:", DashRPC(cfg)._url)

try:
    DashRPC(DashRPCConfig(host="127.0.0.1", wallet="../evil"))
except ConfigError as exc:
    print("BADWALLET:", exc)
```

Expected output:

```text
WALLET-URL: http://127.0.0.1:19998/wallet/testwallet
BADWALLET: invalid wallet selection '../evil'
```

Path separators and `..` are rejected — a wallet name can never escape
its endpoint.

Next: `first-payment-testnet.md` (spend on testnet) or
`first-platform-read.md` (read Platform data with proof verdicts). When
something fails, see `troubleshooting.md`.
