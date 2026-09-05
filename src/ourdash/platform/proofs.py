"""Verifier contract: the seam between Platform reads and proof checking.

Dash here is Dash crypto from dash.org — not Plotly Dash.

Every :mod:`ourdash.platform.drive` read funnels its response envelope
through a :class:`Verifier`:

- :class:`FakeVerifier` — structural check used by ALL Fully-Automated
  Platform tests: ``CHECKED`` when the envelope carries a well-formed proof
  (``grovedb_proof`` + ``quorum_hash`` + ``signature`` all present and
  non-empty), :class:`~ourdash.errors.ProofError` otherwise. It proves
  verdict PLUMBING, never proof cryptography.
- :class:`ReferenceBridgeVerifier` — boundary to the pinned external
  reference verifier. A greenfield pure-Python GroveDB-proof port is NOT
  attempted in v0.1 (cryptographic consensus code is the wrong thing to
  reimplement blind); the bridge shells out instead.

Reference pin (resolved 2026-09-05 from the SPEC-pinned proof-capable JS
toolkit): ``@dashevo/dapi-client@4.1.1`` with ``@dashevo/dapi-grpc@4.1.1``
(the toolkit verifies GroveDB proofs from ``getDocuments``/``getIdentity``/
``getDataContract`` responses against quorum info internally — see its
``lib/methods/platform/*/...Response.js`` plus ``lib/methods/platform/
response/Proof.js``). Invocation schema: input = proof bytes (the
``grovedb_proof`` field) + quorum-info JSON (``quorum_hash``,
``quorum_type``, ``block_id_hash``, ``round``); output = boolean
(proof valid or not). The bridge expects a ``dash-proof-verify`` executable
implementing that schema on ``PATH``; when it is absent (as in this
environment) every call raises
:class:`~ourdash.errors.ProofUnavailableError` with install instructions
instead of guessing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Mapping
from typing import Any, Protocol

from ourdash.errors import ProofError, ProofUnavailableError
from ourdash.platform.models import ProofVerdict

#: Proof fields a well-formed envelope proof MUST carry (base64 strings).
_REQUIRED_PROOF_FIELDS: tuple[str, ...] = (
    "grovedb_proof_b64",
    "quorum_hash_b64",
    "signature_b64",
)

#: npm pin of the reference verifier family (resolved 2026-09-05).
REFERENCE_VERIFIER_PIN = "@dashevo/dapi-client@4.1.1 + @dashevo/dapi-grpc@4.1.1"

#: Executable the bridge shells out to (input: proof bytes + quorum-info
#: JSON on stdin; output: "true"/"false" on stdout).
BRIDGE_BINARY = "dash-proof-verify"


class Verifier(Protocol):
    """Structural contract: check an envelope proof, return the verdict."""

    def verify(self, envelope: Mapping[str, Any]) -> ProofVerdict:
        """Return ``CHECKED`` for a valid proof; raise otherwise."""
        ...  # pragma: no cover - protocol surface


def proof_from_envelope(envelope: Mapping[str, Any]) -> Mapping[str, Any]:
    """Extract the proof mapping, raising :class:`ProofError` when malformed."""
    if not isinstance(envelope, Mapping):
        raise ProofError("proof envelope must be a mapping")
    proof = envelope.get("proof")
    if not isinstance(proof, Mapping):
        raise ProofError("proof envelope carries no proof mapping")
    missing = [field for field in _REQUIRED_PROOF_FIELDS if not proof.get(field)]
    if missing:
        raise ProofError(f"proof is missing fields: {', '.join(missing)}")
    return proof


class FakeVerifier:
    """Structural verifier for tests: well-formed proof → ``CHECKED``."""

    def verify(self, envelope: Mapping[str, Any]) -> ProofVerdict:
        """Return ``CHECKED``; raise :class:`ProofError` when malformed."""
        proof_from_envelope(envelope)
        return ProofVerdict.CHECKED


class ReferenceBridgeVerifier:
    """Boundary to the pinned external reference verifier (absent → raise).

    ``binary`` overrides the executable name (tests inject a fake); by
    default the bridge looks for :data:`BRIDGE_BINARY` on ``PATH``.
    """

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or BRIDGE_BINARY

    def verify(self, envelope: Mapping[str, Any]) -> ProofVerdict:
        """Shell out per the invocation schema; map the boolean to a verdict.

        ``False`` from the reference verifier means the proof FAILED:
        raise :class:`ProofError` (never label bad proofs ``CHECKED``).
        """
        proof = proof_from_envelope(envelope)
        helper = shutil.which(self.binary)
        if helper is None:
            raise ProofUnavailableError(
                f"reference proof verifier {self.binary!r} is not installed; "
                f"install the pinned reference ({REFERENCE_VERIFIER_PIN}) and "
                "provide a 'dash-proof-verify' helper taking proof bytes + "
                "quorum-info JSON on stdin and printing 'true'/'false'. "
                "See the module docstring for the pin and invocation schema."
            )
        payload = {
            "grovedb_proof_b64": proof["grovedb_proof_b64"],
            "quorum_info": {
                "quorum_hash_b64": proof.get("quorum_hash_b64"),
                "quorum_type": proof.get("quorum_type"),
                "block_id_hash_b64": proof.get("block_id_hash_b64"),
                "round": proof.get("round"),
            },
        }
        try:
            completed = subprocess.run(
                [helper],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ProofUnavailableError(
                f"reference proof verifier {self.binary!r} could not run: {exc}"
            ) from exc
        if completed.returncode != 0:
            raise ProofUnavailableError(
                f"reference proof verifier {self.binary!r} exited "
                f"{completed.returncode}: {completed.stderr.strip()[:200]}"
            )
        if completed.stdout.strip().lower() == "true":
            return ProofVerdict.CHECKED
        raise ProofError("reference verifier rejected the proof")
