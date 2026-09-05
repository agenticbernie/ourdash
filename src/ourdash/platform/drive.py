"""Drive query facade: every Platform read returns data plus a proof verdict.

Dash here is Dash crypto from dash.org — not Plotly Dash.

v0.1 transport reality: the SDK ships no Platform query transport (DAPI
unary queries are gRPC-only upstream; :mod:`ourdash.platform.dapi` speaks
the HTTP/JSON L1 surface only). :class:`Drive` therefore shapes requests,
parses envelopes, and funnels every proof through a :class:`Verifier
<ourdash.platform.proofs.Verifier>`, while the actual fetch goes through an
injected ``fetcher`` callable ``(endpoint, request) -> envelope``:

- Fully-Automated tests inject fixtures from ``tests/fixtures/platform/``.
- Live use passes a gRPC-backed fetcher once the transport lands (deferred).
- With ``fetcher=None`` every read raises
  :class:`~ourdash.errors.ProofUnavailableError` — never silent trust,
  never fabricated data.

Verdict semantics (SPEC 11 — explicit fallback): ``trust_node=False``
(the default, keyword-only) verifies via the configured verifier and
returns ``ProvenResult(verdict=CHECKED)``; when no verifiable proof is
available it raises ``ProofUnavailableError``. ``trust_node=True`` (also
keyword-only — positional passing is a ``TypeError`` by construction)
returns ``ProvenResult(verdict=UNCHECKED)`` AND emits a ``UserWarning``
stating the answer is unchecked.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ourdash.errors import DAPIError, ProofUnavailableError
from ourdash.platform.dapi import DAPIClient
from ourdash.platform.models import (
    DataContractInfo,
    DocumentResult,
    IdentityInfo,
    ProofVerdict,
    ProvenResult,
    TokenRules,
    TokenTransferEntry,
    TokenTransferPage,
    UsernameResolution,
)
from ourdash.platform.proofs import ReferenceBridgeVerifier, Verifier
from ourdash.redact import RedactionFilter

logger = logging.getLogger(__name__)
logger.addFilter(RedactionFilter())

#: Documented testnet DPNS system contract (docs.dash.org Platform "Retrieve
#: a name" tutorial, stable edition; recorded 2026-09-05). Overridable per
#: call for other networks — system contract ids are network-specific.
DPNS_TESTNET_CONTRACT_ID = "GWRSAVFMjXx8HpQFaNJMqBV7MBgMK4br5UESsB4S31Ec"

#: Callable shaping ``(endpoint, request) -> envelope`` for live reads.
Fetcher = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]

_UNCHECKED_WARNING = (
    "trust_node=True: this answer is UNCHECKED (proof not verified); "
    "use the default trust_node=False with a verifier for CHECKED reads"
)


def _normalize_label(label: str) -> str:
    """Apply the documented DPNS homograph-safe normalization.

    Lowercase plus ``o`` → ``0`` and ``i``/``l`` → ``1`` (docs.dash.org
    Platform DPNS explanation, verified 2026-09-05).
    """
    return label.lower().replace("o", "0").replace("i", "1").replace("l", "1")


def _mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DAPIError(f"{what} is malformed (expected a mapping)")
    return value


class Drive:
    """Typed Platform reads over an injected fetch seam."""

    def __init__(
        self,
        client: DAPIClient,
        verifier: Verifier | None = None,
        fetcher: Fetcher | None = None,
    ) -> None:
        self.client = client
        # Fail-closed default: the reference bridge raises
        # ProofUnavailableError when its binary is absent, so an
        # unverified envelope can never yield CHECKED by default.
        # Pass an explicit FakeVerifier for offline/fixture tests
        # (verdict plumbing only — never cryptography).
        self.verifier: Verifier = verifier if verifier is not None else ReferenceBridgeVerifier()
        self.fetcher = fetcher

    def _fetch(self, endpoint: str, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.fetcher is None:
            raise ProofUnavailableError(
                f"no verifiable proof is available for {endpoint!r}: v0.1 ships "
                "no Platform query transport (DAPI queries are gRPC-only "
                "upstream; deferred) — pass fetcher=... or query recorded "
                "fixtures from tests/fixtures/platform/"
            )
        envelope = self.fetcher(endpoint, request)
        return _mapping(envelope, f"{endpoint} envelope")

    def _verify(
        self, method: str, envelope: Mapping[str, Any], *, trust_node: bool
    ) -> tuple[ProofVerdict, str]:
        if trust_node:
            warnings.warn(f"Drive.{method}: {_UNCHECKED_WARNING}", UserWarning, stacklevel=4)
            return ProofVerdict.UNCHECKED, "caller opted out via trust_node=True"
        if envelope.get("proof") is None:
            raise ProofUnavailableError(
                f"{method} returned no verifiable proof; refusing silent trust "
                "(pass trust_node=True to accept an UNCHECKED answer explicitly)"
            )
        verdict = self.verifier.verify(envelope)
        return verdict, f"verifier {type(self.verifier).__name__} accepted the proof"

    @staticmethod
    def _data(envelope: Mapping[str, Any], endpoint: str) -> Mapping[str, Any]:
        data = envelope.get("data")
        if data is None:
            raise DAPIError(f"{endpoint} envelope carries no data section")
        return _mapping(data, f"{endpoint} data")

    def query_documents(
        self,
        contract_id: str,
        document_type: str,
        filter: Mapping[str, Any] | None = None,  # noqa: A002 - DAPI calls it `filter`
        limit: int = 100,
        *,
        trust_node: bool = False,
    ) -> ProvenResult:
        """Query ``document_type`` documents; always with a verdict."""
        envelope = self._fetch(
            "getDocuments",
            {
                "contract_id": contract_id,
                "document_type": document_type,
                "filter": dict(filter) if filter else {},
                "limit": limit,
            },
        )
        verdict, note = self._verify("query_documents", envelope, trust_node=trust_node)
        raw_docs = self._data(envelope, "getDocuments").get("documents", [])
        if not isinstance(raw_docs, list):
            raise DAPIError("getDocuments data.documents is malformed")
        documents = []
        for entry in raw_docs:
            item = _mapping(entry, "getDocuments document")
            try:
                documents.append(
                    DocumentResult(
                        doc_id=str(item["doc_id"]),
                        contract_id=str(item.get("contract_id", contract_id)),
                        doc_type=str(item.get("doc_type", document_type)),
                        fields=dict(item.get("fields", {})),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise DAPIError(f"getDocuments document is malformed: {exc}") from exc
        return ProvenResult(data=documents, verdict=verdict, proof_note=note)

    def get_data_contract(self, contract_id: str, *, trust_node: bool = False) -> ProvenResult:
        """Read one data contract (id, version, owner, document types)."""
        envelope = self._fetch("getDataContract", {"contract_id": contract_id})
        verdict, note = self._verify("get_data_contract", envelope, trust_node=trust_node)
        raw = self._data(envelope, "getDataContract").get("contract", {})
        item = _mapping(raw, "getDataContract data.contract")
        try:
            info = DataContractInfo(
                contract_id=str(item["contract_id"]),
                version=int(item.get("version", 1)),
                owner_id=item.get("owner_id"),
                document_types=list(item.get("document_types", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DAPIError(f"getDataContract payload is malformed: {exc}") from exc
        return ProvenResult(data=info, verdict=verdict, proof_note=note)

    def get_identity(self, identity_id: str, *, trust_node: bool = False) -> ProvenResult:
        """Read one identity (keys, credit balance, sequence number)."""
        envelope = self._fetch("getIdentity", {"identity_id": identity_id})
        verdict, note = self._verify("get_identity", envelope, trust_node=trust_node)
        raw = self._data(envelope, "getIdentity").get("identity", {})
        item = _mapping(raw, "getIdentity data.identity")
        try:
            info = IdentityInfo(
                identity_id=str(item["identity_id"]),
                balance=int(item.get("balance", 0)),
                revision=int(item.get("revision", 0)),
                public_keys=list(item.get("public_keys", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DAPIError(f"getIdentity payload is malformed: {exc}") from exc
        return ProvenResult(data=info, verdict=verdict, proof_note=note)

    def resolve_dpns(
        self,
        name: str,
        *,
        contract_id: str = DPNS_TESTNET_CONTRACT_ID,
        trust_node: bool = False,
    ) -> ProvenResult:
        """Resolve a DPNS ``label.dash`` name to its identity id.

        Queries the DPNS contract's ``domain`` documents for the
        homograph-safe normalized label. ``contested`` reports the envelope's
        contested flag for the match (``False`` when the name is settled).
        """
        if not isinstance(name, str) or "." not in name:
            raise DAPIError("DPNS name must look like 'label.dash'")
        label = name.split(".")[0]
        if not label:
            raise DAPIError("DPNS name must look like 'label.dash'")
        normalized = _normalize_label(label)
        envelope = self._fetch(
            "getDocuments",
            {
                "contract_id": contract_id,
                "document_type": "domain",
                "filter": {"normalized_label": normalized},
                "limit": 10,
            },
        )
        verdict, note = self._verify("resolve_dpns", envelope, trust_node=trust_node)
        raw_docs = self._data(envelope, "getDocuments").get("documents", [])
        if not isinstance(raw_docs, list):
            raise DAPIError("getDocuments data.documents is malformed")
        match: Mapping[str, Any] | None = None
        for entry in raw_docs:
            item = _mapping(entry, "getDocuments document")
            fields = item.get("fields", {})
            fields_map = fields if isinstance(fields, Mapping) else {}
            if fields_map.get("normalized_label") == normalized:
                match = item
                break
        if match is None:
            return ProvenResult(
                data=UsernameResolution(name=name, identity_id=None, contested=False),
                verdict=verdict,
                proof_note=note,
            )
        fields = match.get("fields", {})
        fields_map = fields if isinstance(fields, Mapping) else {}
        # The linked identity is the records identity (what DPNS resolveName
        # returns); fall back to the document owner when records are absent.
        owner = fields_map.get("records_identity_id", fields_map.get("owner_id"))
        if owner is None:
            owner = match.get("owner_id")
        contested = fields_map.get("contested", False)
        return ProvenResult(
            data=UsernameResolution(
                name=name,
                identity_id=str(owner) if owner is not None else None,
                contested=bool(contested),
            ),
            verdict=verdict,
            proof_note=note,
        )

    def get_token_rules(self, token_id: str, *, trust_node: bool = False) -> ProvenResult:
        """Read what a token IS: the contract/position pinning its rules."""
        envelope = self._fetch("getTokenContractInfo", {"token_id": token_id})
        verdict, note = self._verify("get_token_rules", envelope, trust_node=trust_node)
        raw = self._data(envelope, "getTokenContractInfo").get("token", {})
        item = _mapping(raw, "getTokenContractInfo data.token")
        try:
            rules = TokenRules(
                token_id=str(item["token_id"]),
                contract_id=str(item["contract_id"]),
                position=int(item.get("position", 0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DAPIError(f"getTokenContractInfo payload is malformed: {exc}") from exc
        return ProvenResult(data=rules, verdict=verdict, proof_note=note)

    def get_token_transfers(
        self,
        token_id: str,
        *,
        identity_ids: Sequence[str] = (),
        limit: int = 100,
        continuation_token: str | None = None,
        trust_node: bool = False,
    ) -> ProvenResult:
        """Read a page of token distribution rows for ``token_id``.

        v0.1 note: DAPI v4.1 exposes no token-transfer-history query, so the
        readable per-token distribution surface is ``getIdentitiesTokenBalances``
        (one balance row per identity). A dedicated transfer-history read is
        deferred with the gRPC transport.
        """
        envelope = self._fetch(
            "getIdentitiesTokenBalances",
            {
                "token_id": token_id,
                "identity_ids": list(identity_ids),
                "limit": limit,
                "continuation_token": continuation_token,
            },
        )
        verdict, note = self._verify("get_token_transfers", envelope, trust_node=trust_node)
        data = self._data(envelope, "getIdentitiesTokenBalances")
        raw_rows = data.get("balances", [])
        if not isinstance(raw_rows, list):
            raise DAPIError("getIdentitiesTokenBalances data.balances is malformed")
        entries = []
        for row in raw_rows:
            item = _mapping(row, "token balance row")
            try:
                entries.append(
                    TokenTransferEntry(
                        identity_id=str(item["identity_id"]),
                        balance=int(item.get("balance", 0)),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise DAPIError(f"token balance row is malformed: {exc}") from exc
        page = TokenTransferPage(
            token_id=token_id,
            entries=entries,
            continuation_token=data.get("continuation_token"),
        )
        return ProvenResult(data=page, verdict=verdict, proof_note=note)
