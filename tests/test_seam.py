"""Seam lint: transport stays validation-lib-free; core never imports platform."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "src" / "ourdash" / "core"
RPC = CORE / "rpc.py"
DAPI = REPO / "src" / "ourdash" / "platform" / "dapi.py"


def test_transport_files_have_no_pydantic() -> None:
    for path in (RPC, DAPI):
        assert "pydantic" not in path.read_text(
            encoding="utf-8"
        ), f"{path} must not mention pydantic"


def test_core_never_imports_platform() -> None:
    offenders = []
    for path in sorted(CORE.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "from ourdash.platform" in text or "from ..platform" in text:
            offenders.append(path.name)
    assert offenders == []
