"""Phase 6: docs work from zero (SPEC 18, automated part). Fully-Automated.

Asserts the five guides exist, carry their required sections, disambiguate
Dash crypto from Plotly Dash, and reference only resolvable API: every
``from ourdash... import ...`` line imports cleanly, and every backticked
API-looking name resolves to a real ``ourdash`` attribute (or enum member).

The live verbatim walkthrough itself is Agent-Probe (never in CI); this
file is its machine-checkable shadow.
"""

from __future__ import annotations

import builtins
import importlib
import re
from enum import Enum
from pathlib import Path

import ourdash

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

GUIDES = (
    "install.md",
    "connect.md",
    "first-payment-testnet.md",
    "first-platform-read.md",
    "troubleshooting.md",
)

# Required sections per guide (heading strings; keep in sync with docs/).
REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "install.md": ("## Prerequisites", "## Install", "## Verify the install"),
    "connect.md": (
        "## Loopback default",
        "## Credentials from the environment",
        "## Remote hosts need opt-in",
        "## Wallet selection",
    ),
    "first-payment-testnet.md": (
        "## Fund a testnet address",
        "## Build",
        "## Review",
        "## Sign",
        "## Submit",
        "## Confirm",
    ),
    "first-platform-read.md": (
        "## Discover a seed",
        "## First Layer-1 reads",
        "## Documents query with a verdict",
        "## Verdict interpretation",
        "## Explicit trusted-node fallback",
    ),
    "troubleshooting.md": (
        "## ConfigError",
        "## RpcAuthError",
        "## RpcConnectionError",
        "## RpcTimeoutError",
        "## WalletError",
        "## PaymentError",
        "## AddressError",
        "## DAPIError",
        "## ProofError and ProofUnavailableError",
        "## Secrets-safety rules",
    ),
}

# Backticked words that are NOT SDK API. Guides reserve backticks for code;
# these three documented sets cover the rest:
# - env names (the ONLY config surface; values never appear in repo),
# - dataclass/param names (attributes of configs, not module members),
# - tooling words (test runner, linters, extras, markers, networks).
NON_API_WORDS: frozenset[str] = frozenset(
    {
        # env names
        "OURDASH_RPC_URL",
        "OURDASH_RPC_USER",
        "OURDASH_RPC_PASSWORD",
        "OURDASH_RPC_WALLET",
        "OURDASH_DAPI_ADDRESS",
        "OURDASH_DAPI_TIMEOUT_S",
        "OURDASH_NETWORK",
        # config fields / call params
        "remote_ok",
        "wallet",
        "cookie_path",
        "trust_node",
        "allow_sign",
        "timeout_s",
        "host",
        "port",
        "user",
        "password",
        "filter",
        "limit",
        "network",
        "fetcher",
        # tooling / packaging / networks
        "pytest",
        "ruff",
        "black",
        "mypy",
        "pip",
        "venv",
        "python",
        "grpcio",
        "protobuf",
        "dev",
        "platform",
        "all",
        "hybrid",
        "agent_probe",
        "src",
        "dash",
        "dashd",
        "git",
        "ourdash",
        "testnet",
        "mainnet",
        "regtest",
        "devnet",
    }
)

_SUBMODULES = (
    "core.rpc",
    "core.addresses",
    "core.wallet",
    "core.transactions",
    "core.chain",
    "core.network",
    "platform.dapi",
    "platform.seeds",
    "platform.models",
    "platform.proofs",
    "platform.drive",
    "utils",
    "errors",
    "redact",
)


def _namespace() -> set[str]:
    names = set(dir(ourdash)) | set(dir(builtins))
    for dotted in _SUBMODULES:
        module = importlib.import_module(f"ourdash.{dotted}")
        names |= set(dir(module))
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, Enum):
                names |= set(value.__members__)
            elif isinstance(value, type) and value.__module__.startswith("ourdash"):
                names |= {
                    attr
                    for attr in dir(value)
                    if not attr.startswith("_") or attr in ("__version__",)
                }
    return names


def _guide_text(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def test_guides_exist_with_sections_and_disambiguation() -> None:
    for name in GUIDES:
        path = DOCS / name
        assert path.is_file(), f"missing guide: {name}"
        text = path.read_text(encoding="utf-8")
        for heading in REQUIRED_SECTIONS[name]:
            assert heading in text, f"{name} lacks required section {heading!r}"
        # Name rule (SPEC constraints): every public doc disambiguates.
        assert "Plotly Dash" in text, f"{name} lacks the Dash-vs-Plotly-Dash line"


def test_guide_imports_resolve() -> None:
    from_re = re.compile(r"^from (ourdash\S*) import (.+)$", re.MULTILINE)
    failures: list[str] = []
    for name in GUIDES:
        text = _guide_text(name)
        for module_name, imported in from_re.findall(text):
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                failures.append(f"{name}: cannot import {module_name}")
                continue
            for entry in imported.split(","):
                short = entry.strip().split(" as ")[0].strip()
                if short and not hasattr(module, short):
                    failures.append(f"{name}: {module_name} has no {short}")
    assert failures == [], f"unresolvable guide imports: {failures}"


def test_guide_api_names_resolve() -> None:
    namespace = _namespace()
    span_re = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
    failures: list[str] = []
    for name in GUIDES:
        text = "\n".join(
            line for line in _guide_text(name).splitlines() if not line.startswith("```")
        )
        for span in span_re.findall(text):
            # Paths, URLs, versions, sentences, and shell fragments are not
            # API references — only single code tokens are checked.
            if re.search(r"[\s/\\$<>:\"'\-]", span):
                continue
            token = span.strip()
            if token.endswith("()"):
                token = token[:-2]
            # Dotted module paths (ours or stdlib's) resolve by import;
            # filenames are not API references.
            if "." in token:
                if re.search(r"\.(md|py|toml|yml|yaml|txt|json|cfg|ini)$", token):
                    continue  # filename, not API
                head = token
                is_module_path = False
                while "." in head:
                    head = head.rpartition(".")[0]
                    if not head:
                        break
                    try:
                        importlib.import_module(head)
                        is_module_path = True
                        break
                    except (ImportError, ValueError, TypeError):
                        continue
                if is_module_path:
                    continue
                token = token.split(".")[-1]
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
                continue
            if token not in namespace and token not in NON_API_WORDS:
                failures.append(f"{name}: unresolvable API name `{token}`")
    assert failures == [], f"guide names that resolve nowhere: {failures}"
