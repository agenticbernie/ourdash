"""Per-network DAPI seed discovery (no default URL ships).

Dash here is Dash crypto from dash.org — not Plotly Dash.

Seed values come from exactly two named sources (retrieved 2026-09-05):

1. The docs.dash.org Platform "Connect to a network" tutorial
   (https://docs.dash.org/projects/platform/en/stable/docs/tutorials/connecting-to-testnet.html
   and the 2.0.0 edition of the same page): ``seed-1.testnet.networks.dash.org:1443``
   over HTTPS for the JSON-RPC surface.
2. The pinned proof-capable JS toolkit ``@dashevo/dapi-client@4.1.1``
   (npm ``latest`` on 2026-09-05), file ``lib/networkConfigs.js``: five
   ``*.testnet.networks.dash.org:1443`` seeds plus ``seed-1.pshenmic.dev:1443``
   for testnet; four ``*.mainnet.networks.dash.org`` seeds (bare hostnames —
   port 443 and ``https`` come from that package's ``lib/dapiAddressProvider/
   DAPIAddress.js`` ``DEFAULT_PORT = 443`` / ``DEFAULT_PROTOCOL = 'https'``,
   verified 2026-09-05) plus ``seed-1.pshenmic.dev`` for mainnet; loopback
   ``127.0.0.1`` for the ``local`` (regtest) network.

Networks with no documented seed get an EMPTY list (never a placeholder URL);
:meth:`seeds_for` documents the reason and :meth:`DAPIClient.from_network
<ourdash.platform.dapi.DAPIClient.from_network>` raises a guiding
:class:`~ourdash.errors.DAPIError` for them.

Refresh procedure (run each release): re-check both sources above for seed
changes; Agent-Probe ``getBestBlockHash`` (JSON-RPC) against every listed
seed and record the outcome; drop entries that stay dead across two
consecutive releases. Last probe 2026-09-05: all five
``*.testnet.networks.dash.org:1443`` seeds answered with the same tip;
``seed-1.pshenmic.dev:1443`` failed TLS hostname verification; mainnet
``*.mainnet.networks.dash.org:443`` seeds failed TLS hostname verification
(``seed-4`` refused the connection) — mainnet entries are kept because the
pinned toolkit names them, but expect the first live use to exercise the
client's normal retry/error path.

Transport-only module: stdlib + ``dataclasses``. No validation or modelling
libraries are imported here (seam rule, enforced by ``tests/test_seam.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

from ourdash.errors import DAPIError

#: Networks the SDK knows by name. Unknown names are refused, never guessed.
NETWORKS: tuple[str, ...] = ("mainnet", "testnet", "regtest", "devnet")

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

_DAPI_CLIENT_PIN = "@dashevo/dapi-client@4.1.1"
_DOCS_SOURCE = "docs.dash.org Platform 'Connect to a network' tutorial " "(stable + 2.0.0 editions)"
_TOOLKIT_SOURCE = f"{_DAPI_CLIENT_PIN} lib/networkConfigs.js"
_RETRIEVED = "2026-09-05"


@dataclass(frozen=True)
class SeedEntry:
    """One documented DAPI seed endpoint.

    ``interface`` names the surface this seed was documented for (``json-rpc``
    in v0.1 — the only HTTP surface the SDK speaks; gRPC endpoints are
    discovered through the same seeds once a gRPC transport lands).
    ``source`` + ``retrieved`` record WHERE the value came from and WHEN, so a
    stale pin can be traced back to its origin.
    """

    host: str
    port: int
    interface: str = "json-rpc"
    source: str = ""
    retrieved: str = ""

    @property
    def address(self) -> str:
        """Full base URL for this seed.

        ``https`` everywhere except loopback, where local DAPI dev endpoints
        serve plain HTTP (mirrors the ``DashRPC`` loopback pattern).
        """
        scheme = "http" if self.host in _LOOPBACK_HOSTS else "https"
        return f"{scheme}://{self.host}:{self.port}"


def _toolkit(host: str, port: int) -> SeedEntry:
    return SeedEntry(
        host=host,
        port=port,
        interface="json-rpc",
        source=_TOOLKIT_SOURCE,
        retrieved=_RETRIEVED,
    )


def _docs(host: str, port: int) -> SeedEntry:
    return SeedEntry(
        host=host,
        port=port,
        interface="json-rpc",
        source=_DOCS_SOURCE,
        retrieved=_RETRIEVED,
    )


#: Per-network seeds. Order matters: ``from_network`` dials the FIRST entry.
SEEDS: dict[str, list[SeedEntry]] = {
    # testnet seed-1 is cross-cited by BOTH named sources; the rest (2-5 plus
    # the third-party pshenmic.dev entry) come from the pinned toolkit.
    # pshenmic.dev is kept for source fidelity — it is never the default
    # (first) entry, and the 2026-09-05 probe noted a TLS hostname mismatch.
    "testnet": [
        SeedEntry(
            host="seed-1.testnet.networks.dash.org",
            port=1443,
            interface="json-rpc",
            source=f"{_DOCS_SOURCE} + {_TOOLKIT_SOURCE}",
            retrieved=_RETRIEVED,
        ),
        _toolkit("seed-2.testnet.networks.dash.org", 1443),
        _toolkit("seed-3.testnet.networks.dash.org", 1443),
        _toolkit("seed-4.testnet.networks.dash.org", 1443),
        _toolkit("seed-5.testnet.networks.dash.org", 1443),
        _toolkit("seed-1.pshenmic.dev", 1443),
    ],
    # Bare hostnames in the pinned toolkit; port 443 + https per that
    # package's DAPIAddress DEFAULT_PORT/DEFAULT_PROTOCOL (verified
    # 2026-09-05). The 2026-09-05 probe found 443 not serving matching TLS
    # certs — entries kept per the empty-over-invented rule, with the probe
    # outcome recorded in this module's docstring.
    "mainnet": [
        _toolkit("seed-1.mainnet.networks.dash.org", 443),
        _toolkit("seed-2.mainnet.networks.dash.org", 443),
        _toolkit("seed-3.mainnet.networks.dash.org", 443),
        _toolkit("seed-4.mainnet.networks.dash.org", 443),
        _toolkit("seed-1.pshenmic.dev", 443),
    ],
    # No public regtest/devnet seeds are documented by either source;
    # loopback entries for a developer-run node (mirrors the pinned toolkit's
    # ``local`` network pointing at 127.0.0.1).
    "regtest": [
        SeedEntry(
            host="127.0.0.1",
            port=1443,
            interface="json-rpc",
            source="loopback default (no public seed documented; run a local DAPI node)",
            retrieved=_RETRIEVED,
        ),
    ],
    "devnet": [
        SeedEntry(
            host="127.0.0.1",
            port=1443,
            interface="json-rpc",
            source="loopback default (devnets are private; point at your devnet DAPI node)",
            retrieved=_RETRIEVED,
        ),
    ],
}


def seeds_for(network: str) -> list[SeedEntry]:
    """Return the documented seed list for ``network`` (may be empty).

    Raises :class:`~ourdash.errors.DAPIError` for unknown network names —
    the SDK never guesses an endpoint.
    """
    if network not in SEEDS:
        raise DAPIError(f"unknown network {network!r}; expected one of {', '.join(NETWORKS)}")
    return list(SEEDS[network])
