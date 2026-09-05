# Install `ourdash`

Dash here means Dash crypto from dash.org — not Plotly Dash (the dashboard
framework on PyPI as `dash`; never install that expecting crypto).

This guide takes a clean checkout to a green test run. Every session below
was executed verbatim; outputs shown are what you should see (timings and
tip hashes excepted).

## Prerequisites

- Python 3.10 or newer (CI runs 3.10–3.12).
- `pip` and `git`.
- No node, no network, no credentials needed for this guide.

```console
$ .venv/bin/python --version
Python 3.14.6
```

## Install

From the repo root, create a virtualenv and install with all extras
(test + Platform gRPC surface):

```console
$ python -m venv .venv && source .venv/bin/activate
$ pip install -e ".[all]"
```

The `src/` layout requires the editable install — without it, `import
ourdash` fails with `ModuleNotFoundError`. The `[all]` extra pulls
`platform` (`grpcio`, `protobuf`) plus `dev` (`pytest`, `ruff`, `black`,
`mypy`).

Check the import resolves and reports the release version:

```console
$ .venv/bin/python -c "import ourdash; print(ourdash.__version__)"
0.1.0
```

The common surface is re-exported at top level:

```python
from ourdash import DashRPC, DAPIClient, Wallet, validate_address
```

## Verify the install

Run the unit suite (no node needed; live tests are marked `hybrid` /
`agent_probe` and deselected here):

```console
$ .venv/bin/pytest -q -m "not hybrid and not agent_probe"
185 passed, 7 deselected
```

Then the three static gates:

```console
$ .venv/bin/ruff check src tests
All checks passed!
$ .venv/bin/black --check src tests
All done! ✨ 🍰 ✨
32 files would be left unchanged.
$ .venv/bin/mypy src
Success: no issues found in 17 source files
```

All four green means the install is good. Next: `connect.md` (point the
SDK at your own node without ever pasting a secret into code).
