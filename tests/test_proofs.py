"""Platform proof-verdict tests over recorded envelopes (offline).

Every read goes through the `FakeVerifier` + models seam against fixtures in
`tests/fixtures/platform/` — three live testnet captures plus one
structurally-faithful synthetic token envelope marked
`synthetic-pending-recapture`.
"""

from __future__ import annotations

import base64
import json
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from ourdash.errors import DAPIError, ProofError, ProofUnavailableError
from ourdash.platform.dapi import DAPIClient
from ourdash.platform.drive import Drive
from ourdash.platform.models import (
    DataContractInfo,
    DocumentResult,
    IdentityInfo,
    ProofVerdict,
    ProvenResult,
    TokenRules,
    TokenTransferPage,
    UsernameResolution,
)
from ourdash.platform.proofs import (
    FakeVerifier,
    ReferenceBridgeVerifier,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "platform"

DPNS_CONTRACT = "GWRSAVFMjXx8HpQFaNJMqBV7MBgMK4br5UESsB4S31Ec"
IDENTITY_QE = "BNnn19SAJZuvsUu787dMzPDXASwuCrm4yQ864tEpQFvo"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture()
def envelopes() -> dict[str, dict[str, Any]]:
    return {
        "getDocuments": _load("getdocuments_dpns_testnet.json"),
        "getDataContract": _load("getdatacontract_dpns_testnet.json"),
        "getIdentity": _load("getidentity_quantumexplorer_testnet.json"),
        "tokens": _load("gettoken_synthetic_pending_recapture.json"),
    }


def _fetcher(envelopes: dict[str, dict[str, Any]]) -> Any:
    def fetch(endpoint: str, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if endpoint == "getDocuments":
            return envelopes["getDocuments"]
        if endpoint == "getDataContract":
            return envelopes["getDataContract"]
        if endpoint == "getIdentity":
            return envelopes["getIdentity"]
        if endpoint in ("getTokenContractInfo", "getIdentitiesTokenBalances"):
            return envelopes["tokens"]
        raise AssertionError(f"unexpected endpoint {endpoint!r}")

    return fetch


@pytest.fixture()
def drive(envelopes: dict[str, dict[str, Any]]) -> Drive:
    return Drive(
        DAPIClient.from_network("testnet"),
        verifier=FakeVerifier(),
        fetcher=_fetcher(envelopes),
    )


def test_verdict_has_exactly_two_members() -> None:
    assert {member.value for member in ProofVerdict} == {"CHECKED", "UNCHECKED"}


def test_fake_verifier_accepts_well_formed(envelopes: dict[str, dict[str, Any]]) -> None:
    assert FakeVerifier().verify(envelopes["getDocuments"]) is ProofVerdict.CHECKED


def test_fake_verifier_rejects_malformed() -> None:
    verifier = FakeVerifier()
    for bad in (
        {},
        {"proof": None},
        {"proof": {"grovedb_proof_b64": "", "quorum_hash_b64": "x", "signature_b64": "y"}},
        {"proof": {"grovedb_proof_b64": "x"}},
        "not-a-mapping",
    ):
        with pytest.raises(ProofError):
            verifier.verify(bad)  # type: ignore[arg-type]


def test_query_documents_returns_checked_models(drive: Drive) -> None:
    result = drive.query_documents(DPNS_CONTRACT, "domain")
    assert isinstance(result, ProvenResult)
    assert result.verdict is ProofVerdict.CHECKED
    assert result.proof_note
    docs = result.data
    assert len(docs) == 2 and all(isinstance(doc, DocumentResult) for doc in docs)
    labels = {doc.fields["label"] for doc in docs}
    assert labels == {"mvp-mmlv0l8o", "test-invite-21"}
    for doc in docs:
        assert doc.contract_id == DPNS_CONTRACT
        assert doc.fields["normalized_parent_domain_name"] == "dash"
        round_tripped = doc.to_dict()
        assert round_tripped["fields"]["label"] in labels
    assert json.dumps(result.to_dict())


def test_document_labels_match_raw_bytes(envelopes: dict[str, dict[str, Any]]) -> None:
    envelope = envelopes["getDocuments"]
    raws = [base64.b64decode(blob) for blob in envelope["raw"]["document_blobs_b64"]]
    for doc in envelope["data"]["documents"]:
        assert doc["fields"]["label"].encode() in raws[0] + raws[1]


def test_get_data_contract(drive: Drive, envelopes: dict[str, dict[str, Any]]) -> None:
    result = drive.get_data_contract(DPNS_CONTRACT)
    assert result.verdict is ProofVerdict.CHECKED
    info = result.data
    assert isinstance(info, DataContractInfo)
    assert info.contract_id == DPNS_CONTRACT
    assert info.version == 1
    assert info.owner_id
    assert set(info.document_types) == {"domain", "preorder"}
    raw = base64.b64decode(envelopes["getDataContract"]["raw"]["contract_blob_b64"])
    assert b"domain" in raw and b"preorder" in raw
    assert json.dumps(info.to_dict())


def test_get_identity(drive: Drive, envelopes: dict[str, dict[str, Any]]) -> None:
    result = drive.get_identity(IDENTITY_QE)
    assert result.verdict is ProofVerdict.CHECKED
    info = result.data
    assert isinstance(info, IdentityInfo)
    assert info.identity_id == IDENTITY_QE
    assert info.balance == 4
    assert info.revision == 0
    assert len(info.public_keys) == 4
    raw = base64.b64decode(envelopes["getIdentity"]["raw"]["identity_blob_b64"])
    assert _b58decode(IDENTITY_QE) == raw[1:33]
    assert json.dumps(info.to_dict())


def _b58decode(text: str) -> bytes:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = 0
    for char in text:
        number = number * 58 + alphabet.index(char)
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return (b"\x00" * (len(text) - len(text.lstrip("1"))) + raw).rjust(32, b"\x00")


def test_resolve_dpns_matches_display_name(drive: Drive) -> None:
    result = drive.resolve_dpns("test-invite-21.dash")
    assert result.verdict is ProofVerdict.CHECKED
    resolution = result.data
    assert isinstance(resolution, UsernameResolution)
    assert resolution.name == "test-invite-21.dash"
    assert resolution.identity_id == "BPpoW5ia6pGYcaEXYcW5K2L7yqhQWkPGZLd2AjWUX6G7"
    assert resolution.contested is False


def test_resolve_dpns_normalizes_homographs(drive: Drive) -> None:
    upper = drive.resolve_dpns("TEST-INVITE-21.dash")
    assert upper.data.identity_id == "BPpoW5ia6pGYcaEXYcW5K2L7yqhQWkPGZLd2AjWUX6G7"


def test_resolve_dpns_unknown_name_returns_empty(drive: Drive) -> None:
    result = drive.resolve_dpns("nobody-registers-this.dash")
    assert result.verdict is ProofVerdict.CHECKED
    assert result.data.identity_id is None


def test_resolve_dpns_rejects_bad_names(drive: Drive) -> None:
    for bad in ("", "nolabel", ".dash"):
        with pytest.raises(DAPIError):
            drive.resolve_dpns(bad)


def test_token_rules_and_transfers_are_synthetic_aware(
    drive: Drive, envelopes: dict[str, dict[str, Any]]
) -> None:
    assert envelopes["tokens"]["synthetic"] == "synthetic-pending-recapture"
    rules_result = drive.get_token_rules("whatever-token")
    rules = rules_result.data
    assert isinstance(rules, TokenRules)
    assert rules_result.verdict is ProofVerdict.CHECKED
    assert rules.contract_id == envelopes["tokens"]["data"]["token"]["contract_id"]
    page_result = drive.get_token_transfers("whatever-token", identity_ids=[IDENTITY_QE])
    page = page_result.data
    assert isinstance(page, TokenTransferPage)
    assert page_result.verdict is ProofVerdict.CHECKED
    assert [entry.identity_id for entry in page.entries] == [IDENTITY_QE]
    assert page.entries[0].balance == 1000
    assert page.continuation_token is None
    assert json.dumps(page.to_dict())


def test_trust_node_true_returns_unchecked_with_warning(drive: Drive) -> None:
    with pytest.warns(UserWarning, match="UNCHECKED"):
        result = drive.get_identity(IDENTITY_QE, trust_node=True)
    assert result.verdict is ProofVerdict.UNCHECKED
    assert isinstance(result.data, IdentityInfo)
    with pytest.warns(UserWarning, match="UNCHECKED"):
        docs = drive.query_documents(DPNS_CONTRACT, "domain", trust_node=True)
    assert docs.verdict is ProofVerdict.UNCHECKED


def test_trust_node_is_keyword_only(drive: Drive) -> None:
    with pytest.raises(TypeError):
        drive.query_documents(DPNS_CONTRACT, "domain", {}, 100, True)  # type: ignore[misc]
    with pytest.raises(TypeError):
        drive.get_identity(IDENTITY_QE, True)  # type: ignore[misc]


def test_proof_absent_without_opt_in_raises(drive: Drive) -> None:
    drive.fetcher = lambda endpoint, request: {"data": {"identity": {}}, "proof": None}
    with pytest.raises(ProofUnavailableError):
        drive.get_identity(IDENTITY_QE)


def test_missing_fetcher_raises_proof_unavailable() -> None:
    bare = Drive(DAPIClient.from_network("testnet"), verifier=FakeVerifier())
    with pytest.raises(ProofUnavailableError, match="fetcher"):
        bare.get_identity(IDENTITY_QE)
    # Even explicit opt-in needs a data source: no fetcher, no answer.
    with pytest.raises(ProofUnavailableError, match="fetcher"):
        bare.get_identity(IDENTITY_QE, trust_node=True)


def test_malformed_envelope_surfaces_typed_error(drive: Drive) -> None:
    drive.fetcher = lambda endpoint, request: {
        "data": {"identity": {"balance": "nan"}},
        "proof": None,
    }
    with pytest.raises(ProofUnavailableError):
        drive.get_identity(IDENTITY_QE, trust_node=False)


def test_bridge_without_binary_is_unavailable(
    envelopes: dict[str, dict[str, Any]],
) -> None:
    bridge = ReferenceBridgeVerifier(binary="definitely-not-installed-ourdash")
    with pytest.raises(ProofUnavailableError, match="not installed"):
        bridge.verify(envelopes["getDocuments"])


def test_bridge_round_trips_a_helper_script(
    tmp_path: Path, envelopes: dict[str, dict[str, Any]]
) -> None:
    helper = tmp_path / "dash-proof-verify"
    helper.write_text('#!/bin/sh\ncat > /dev/null\necho "true"\n', encoding="utf-8")
    helper.chmod(helper.stat().st_mode | stat.S_IEXEC)
    assert (
        ReferenceBridgeVerifier(binary=str(helper)).verify(envelopes["getDocuments"])
        is ProofVerdict.CHECKED
    )
    helper.write_text('#!/bin/sh\ncat > /dev/null\necho "false"\n', encoding="utf-8")
    with pytest.raises(ProofError):
        ReferenceBridgeVerifier(binary=str(helper)).verify(envelopes["getDocuments"])
    with pytest.raises(ProofError):
        ReferenceBridgeVerifier(binary=str(helper)).verify({"proof": None})


def test_recorded_envelopes_carry_provenance(
    envelopes: dict[str, dict[str, Any]],
) -> None:
    for name, envelope in envelopes.items():
        assert envelope["captured"] == "2026-09-05", name
        assert envelope["source"], name
        assert (FIXTURES / "README.md").exists()
