"""ourdash — Modern Python SDK for Dash (Dash crypto from dash.org, not Plotly Dash).

Top-level re-exports of the stable v0.1 surface (reads + offline payments +
proof verdicts). Import here for the common case::

    from ourdash import DashRPC, Wallet, validate_address

Deeper models and facades stay importable from their owning modules
(``ourdash.core.*``, ``ourdash.platform.*``).
"""

from ourdash.core.addresses import AddressInfo as AddressInfo
from ourdash.core.addresses import validate_address as validate_address
from ourdash.core.rpc import DashRPC as DashRPC
from ourdash.core.rpc import DashRPCConfig as DashRPCConfig
from ourdash.core.transactions import ConfirmationStatus as ConfirmationStatus
from ourdash.core.transactions import SignedTx as SignedTx
from ourdash.core.transactions import UnsignedTx as UnsignedTx
from ourdash.core.wallet import Wallet as Wallet
from ourdash.errors import AddressError as AddressError
from ourdash.errors import ConfigError as ConfigError
from ourdash.errors import DAPIError as DAPIError
from ourdash.errors import OurdashError as OurdashError
from ourdash.errors import PaymentError as PaymentError
from ourdash.errors import ProofError as ProofError
from ourdash.errors import ProofUnavailableError as ProofUnavailableError
from ourdash.errors import RpcAuthError as RpcAuthError
from ourdash.errors import RpcConnectionError as RpcConnectionError
from ourdash.errors import RpcError as RpcError
from ourdash.errors import RpcTimeoutError as RpcTimeoutError
from ourdash.errors import WalletError as WalletError
from ourdash.platform.dapi import DAPIClient as DAPIClient
from ourdash.platform.dapi import DAPIConfig as DAPIConfig
from ourdash.platform.models import ProofVerdict as ProofVerdict
from ourdash.platform.models import ProvenResult as ProvenResult

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DashRPC",
    "DashRPCConfig",
    "DAPIClient",
    "DAPIConfig",
    "AddressInfo",
    "validate_address",
    "Wallet",
    "UnsignedTx",
    "SignedTx",
    "ConfirmationStatus",
    "ProofVerdict",
    "ProvenResult",
    "OurdashError",
    "RpcError",
    "RpcAuthError",
    "RpcConnectionError",
    "RpcTimeoutError",
    "ConfigError",
    "AddressError",
    "WalletError",
    "PaymentError",
    "DAPIError",
    "ProofError",
    "ProofUnavailableError",
]
