"""Typed Platform read models: every read returns data plus a proof verdict.

Dash here is Dash crypto from dash.org — not Plotly Dash.

A Platform app developer queries documents/contracts, identities/usernames,
and tokens, and ALWAYS gets the data together with a trust verdict
(:class:`ProofVerdict`): ``CHECKED`` when a verifier accepted the response
proof, ``UNCHECKED`` only via the explicit keyword-only ``trust_node=True``
opt-in on the :mod:`ourdash.platform.drive` facade (which additionally emits
a ``UserWarning``).

Pydantic lives HERE (curated facade), never in the transport seam
(:mod:`ourdash.platform.dapi`, :mod:`ourdash.platform.seeds`).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProofVerdict(str, Enum):
    """Trust verdict attached to every Platform read. Exactly two members."""

    CHECKED = "CHECKED"
    UNCHECKED = "UNCHECKED"


class ProvenResult(BaseModel):
    """Data plus its verdict. ``proof_note`` says HOW the verdict was reached."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    data: Any
    verdict: ProofVerdict
    proof_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        dumped = self.model_dump(mode="python")
        verdict = dumped.get("verdict")
        if isinstance(verdict, Enum):
            dumped["verdict"] = verdict.value
        return dict(dumped)


class DocumentResult(BaseModel):
    """One Drive document: identity plus its decoded fields."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    doc_id: str
    contract_id: str
    doc_type: str
    fields: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class DataContractInfo(BaseModel):
    """A data contract: id, version, owner, and the document types it defines."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    contract_id: str
    version: int = 1
    owner_id: str | None = None
    document_types: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class IdentityInfo(BaseModel):
    """An identity: keys, credit balance, and sequence (revision) number."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    identity_id: str
    balance: int = 0
    revision: int = 0
    public_keys: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class UsernameResolution(BaseModel):
    """A DPNS name → identity id lookup, with its contested flag."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    name: str
    identity_id: str | None = None
    contested: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class TokenRules(BaseModel):
    """What a token IS: its id plus the contract/position pinning its rules.

    v0.1 reads the pin via DAPI ``getTokenContractInfo``; the full rule set
    (conventions, supply, change control) lives in the owning data
    contract, retrievable via :meth:`drive.get_data_contract`.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    token_id: str
    contract_id: str
    position: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class TokenTransferEntry(BaseModel):
    """One row of a token distribution page: identity → balance."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    identity_id: str
    balance: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")


class TokenTransferPage(BaseModel):
    """A page of token distribution rows plus its continuation token."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    token_id: str
    entries: list[TokenTransferEntry] = []
    continuation_token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-object view (stdlib types only)."""
        return self.model_dump(mode="python")
