"""Shared fixtures: dashd regtest node (Hybrid — skips without the binary)."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from secrets import token_hex
from typing import Any

import pytest

from ourdash.core.rpc import DashRPC, DashRPCConfig


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def dashd_regtest(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[dict[str, Any]]:
    """Boot a private regtest node on loopback; skip cleanly without ``dashd``."""
    binary = os.environ.get("OURDASH_DASHD_BIN", "dashd")
    if shutil.which(binary) is None:
        pytest.skip(f"regtest binary not found: {binary!r} (set OURDASH_DASHD_BIN)")
    datadir = tmp_path_factory.mktemp("dashd-regtest")
    rpc_user = "ourdash-rpc"
    rpc_password = token_hex(16)
    rpc_port = _free_port()
    proc = subprocess.Popen(
        [
            binary,
            "-regtest",
            f"-datadir={datadir}",
            "-server",
            "-listen=0",
            "-discover=0",
            "-dnsseed=0",
            "-rpcbind=127.0.0.1",
            f"-rpcport={rpc_port}",
            f"-rpcuser={rpc_user}",
            f"-rpcpassword={rpc_password}",
            "-fallbackfee=0.00010",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    rpc = DashRPC(
        DashRPCConfig(host="127.0.0.1", port=rpc_port, user=rpc_user, password=rpc_password)
    )
    ready = False
    deadline = time.time() + 60.0
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            rpc.call("getblockcount")
            ready = True
            break
        except Exception:  # noqa: BLE001 - readiness probe; node may refuse mid-boot
            time.sleep(0.5)
    if not ready:
        proc.terminate()
        pytest.skip("dashd regtest did not become ready in time")

    def mine(nblocks: int = 1) -> Any:
        address = rpc.call("getnewaddress")
        return rpc.call("generatetoaddress", nblocks, address)

    try:
        yield {"rpc": rpc, "mine": mine, "datadir": datadir, "process": proc}
    finally:
        try:
            rpc.call("stop")
        except Exception:  # noqa: BLE001 - teardown must not fail the suite
            pass
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
