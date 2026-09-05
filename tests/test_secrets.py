"""Phase 6: secrets never leak (SPEC 16). Fully-Automated, no node.

Two gates:

1. Sentinel scan: fixed UNIQUE fake secrets are threaded through wallet
   build/sign, failing-RPC calls, and error rendering under
   ``caplog``/``capsys`` capture. The test FAILS if any sentinel appears in
   captured logs, exception strings/``repr``\\ s, or any file under
   ``tmp_path`` written during the run.
2. Source-literal scan: ``src/`` text must not contain banned literals
   (dead URL, valued ``rpcpassword=``, private-key-looking hex).
"""

from __future__ import annotations

import json
import logging
import re
import warnings
from pathlib import Path

from ourdash.core.rpc import DashRPC, DashRPCConfig
from ourdash.core.transactions import build, review, sign
from ourdash.core.wallet import Wallet
from ourdash.errors import OurdashError

# Leak canaries. The mnemonic is a PUBLISHED BIP39 test vector (never a real
# secret) used here as a mnemonic-shaped canary because wallet restore
# requires a checksum-valid phrase. The password and cookie values are fake,
# unique to this file, and match no real credential.
SENTINEL_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon abandon abandon about"
)
SENTINEL_PASSWORD = "p6-sentinel-pw-9f27c14e"
SENTINEL_COOKIE_USER = "p6sentinel"
SENTINEL_COOKIE_SECRET = "p6-sentinel-cookie-3b81de07"

SENTINELS = (SENTINEL_MNEMONIC, SENTINEL_PASSWORD, SENTINEL_COOKIE_SECRET)

FAKE_TXID = "0123456789abcdef" * 4

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"

# Allowlist for the hex-literal rule below: test vectors (fake txids, fixture
# hashes) live in tests/ and NEVER in src/, so this stays empty. Any 33+
# hex-char literal added to src/ must be justified here or the gate fails.
HEX_LITERAL_ALLOWLIST: frozenset[str] = frozenset()


def _check_haystack(haystack: str) -> list[str]:
    return [sentinel for sentinel in SENTINELS if sentinel in haystack]


def test_sentinels_absent_from_logs_errors_and_files(
    tmp_path: Path, caplog: object, capsys: object
) -> None:
    logs = caplog  # type: ignore[attr-defined]
    out = capsys  # type: ignore[attr-defined]
    logs.set_level(logging.DEBUG)  # type: ignore[attr-defined]
    errors: list[str] = []

    def _capture(action: object) -> None:
        try:
            action()  # type: ignore[operator]
        except OurdashError as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            errors.append(repr(exc))

    wallet = Wallet.from_mnemonic(SENTINEL_MNEMONIC, passphrase=SENTINEL_PASSWORD)
    sender = wallet.receiving_address(0)
    unsigned = build(
        [{"txid": FAKE_TXID, "vout": 0, "amount_duffs": 100_000, "address": sender}],
        [{"address": wallet.receiving_address(1), "amount_duffs": 99_000}],
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        signed = sign(unsigned, wallet, allow_sign=True)
    review_text = json.dumps(review(unsigned)) + json.dumps(review(signed))
    wallet_repr = repr(wallet) + repr(unsigned) + repr(signed) + str(signed)

    # Failing RPC with sentinel password (closed port: refused, never sent).
    _capture(
        lambda: DashRPC(
            DashRPCConfig(host="127.0.0.1", port=1, user="u", password=SENTINEL_PASSWORD)
        ).call("getblockcount")
    )
    errors.append(repr(DashRPCConfig(host="127.0.0.1", user="u", password=SENTINEL_PASSWORD)))

    # Cookie-file auth with sentinel cookie secret (refused before any secret use).
    # NOTE: the cookie file is credential INPUT (test setup), not SDK output —
    # the SDK must never WRITE secrets, so only sdk_out/ is scanned below.
    cookie_file = tmp_path / "cookie"
    cookie_file.write_text(f"{SENTINEL_COOKIE_USER}:{SENTINEL_COOKIE_SECRET}", encoding="utf-8")
    cookie_cfg = DashRPCConfig(host="127.0.0.1", port=1, cookie_path=str(cookie_file))
    errors.append(repr(cookie_cfg))
    _capture(lambda: DashRPC(cookie_cfg).call("getblockcount"))

    # Bad-phrase refusal must not echo its input either.
    _capture(lambda: Wallet.from_mnemonic("not a real phrase " + SENTINEL_PASSWORD))

    probe = tmp_path / "sdk-output" / "captured.txt"
    probe.parent.mkdir(exist_ok=True)
    probe.write_text(review_text + wallet_repr + "\n".join(errors), encoding="utf-8")

    haystack = (
        logs.text  # type: ignore[attr-defined]
        + out.readouterr().out  # type: ignore[attr-defined]
        + out.readouterr().err  # type: ignore[attr-defined]
        + "".join(
            path.read_text(encoding="utf-8")
            for path in sorted((tmp_path / "sdk-output").rglob("*"))
            if path.is_file()
        )
    )
    leaked = _check_haystack(haystack)
    assert leaked == [], f"secret sentinels leaked into logs/errors/files: {len(leaked)} hit(s)"

    # Key material derived from the canary phrase must be absent too.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        priv_hex = wallet.private_key_bytes(0, allow_sign=True).hex()
    assert priv_hex not in haystack
    assert wallet._seed.hex() not in haystack


def test_source_has_no_secret_literals() -> None:
    dead_url_hits: list[str] = []
    rpcpassword_hits: list[str] = []
    hex_hits: list[str] = []
    rpcpassword_re = re.compile(r"rpcpassword\s*=\s*\S", re.IGNORECASE)
    hex_re = re.compile(r"\b[0-9a-fA-F]{33,}\b")
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "api.dash.org" in text:
            dead_url_hits.append(str(path))
        for lineno, line in enumerate(text.splitlines(), 1):
            if rpcpassword_re.search(line):
                rpcpassword_hits.append(f"{path}:{lineno}")
            for match in hex_re.findall(line):
                if match not in HEX_LITERAL_ALLOWLIST:
                    hex_hits.append(f"{path}:{lineno}:{match[:16]}...")
    assert dead_url_hits == [], f"dead URL ships in src: {dead_url_hits}"
    assert rpcpassword_hits == [], f"valued rpcpassword= in src: {rpcpassword_hits}"
    assert hex_hits == [], f"private-key-looking hex literal in src: {hex_hits}"
