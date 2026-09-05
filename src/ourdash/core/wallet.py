"""Offline HD wallet: BIP39 restore → BIP32/44 (Dash coin type 5) → P2PKH addresses.

Dash here is Dash crypto from dash.org — not Plotly Dash.

Derivation refs: BIP39 recovery phrases (PBKDF2-HMAC-SHA512, 2048 rounds,
salt ``"mnemonic" + passphrase``) validated against the ``mnemonic`` package
wordlist; BIP32 HD derivation (``"Bitcoin seed"`` HMAC-SHA512 master key,
hardened ``0x00 || priv || index`` / normal ``pub || index`` child steps);
BIP44 account path ``m/44'/5'/0'`` with Dash coin type ``5``; first receiving
address at exactly ``m/44'/5'/0'/0/0``. P2PKH address encoding reuses Phase 2
(:func:`ourdash.core.addresses.derive_p2pkh`).

Custody model: :func:`from_mnemonic` returns a pydantic :class:`Wallet` with
``watch_only=True`` by default. Private material (seed, account private key,
chain code) lives ONLY in private attributes (``_seed``, ``_account_priv``,
``_account_chain``) — never in model fields, logs, ``repr``/``str``, or
raised errors. The ONLY accessor that returns key material is
:meth:`Wallet.private_key_bytes`, which requires the explicit keyword-only
opt-in ``allow_sign=True`` (exact name) and always emits a ``UserWarning``
carrying custody wording. There is no silent signing path: ``allow_sign``
defaults to ``False`` and every refusal raises without echoing secrets.

Scope fence: only P2PKH outputs are supported (v0.1). Anything script-based
is refused downstream in :mod:`ourdash.core.transactions` with an explicit
deferral, never silently mishandled.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import warnings
from typing import Final

from ecdsa import SECP256k1, SigningKey  # type: ignore[import-untyped]
from mnemonic import Mnemonic
from pydantic import BaseModel, PrivateAttr, field_validator

from ourdash.core.addresses import derive_p2pkh
from ourdash.errors import WalletError
from ourdash.redact import RedactionFilter, redact

logger = logging.getLogger(__name__)
logger.addFilter(RedactionFilter())

_NETWORKS: Final[tuple[str, ...]] = ("mainnet", "testnet", "regtest", "devnet")

#: Dash BIP44 coin type (``m/44'/5'/...``).
COIN_TYPE: Final[int] = 5
#: Full derivation path of the first receiving address.
FIRST_ADDRESS_PATH: Final[str] = "m/44'/5'/0'/0/0"
_HARDENED: Final[int] = 0x80000000
_MAX_CHILD_INDEX: Final[int] = 0x80000000  # receiving/change indexes stay non-hardened

_CURVE_ORDER: Final[int] = int(SECP256k1.order)

CUSTODY_WARNING: Final[str] = (
    "Custody warning: this wallet defaults to watch-only; signing spends real funds "
    "(not your keys flow — review before signing). Inspect review() output and only "
    "sign what you verified."
)


def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()


def _priv_to_compressed_pub(priv: bytes) -> bytes:
    """Return the 33-byte compressed SECP256k1 public key for a 32-byte secret."""
    raw: bytes = SigningKey.from_secret_exponent(
        int.from_bytes(priv, "big"), curve=SECP256k1
    ).verifying_key.to_string()  # 64 bytes: x || y
    prefix = b"\x02" if raw[63] % 2 == 0 else b"\x03"
    return prefix + raw[:32]


def _hash160(data: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()


def _ckd_priv(parent_priv: bytes, parent_chain: bytes, index: int) -> tuple[bytes, bytes]:
    """Derive one BIP32 child (private) key. Raises :class:`WalletError` on bad input."""
    if not 0 <= index < 2**32:
        raise WalletError(f"child index out of range: {index!r}")
    if index >= _HARDENED:
        data = b"\x00" + parent_priv + index.to_bytes(4, "big")
    else:
        data = _priv_to_compressed_pub(parent_priv) + index.to_bytes(4, "big")
    digest = _hmac_sha512(parent_chain, data)
    tweak = int.from_bytes(digest[:32], "big")
    if not 0 < tweak < _CURVE_ORDER:
        raise WalletError("BIP32 child derivation produced an invalid tweak")
    child = (tweak + int.from_bytes(parent_priv, "big")) % _CURVE_ORDER
    if child == 0:
        raise WalletError("BIP32 child derivation produced the zero key")
    return child.to_bytes(32, "big"), digest[32:]


class Wallet(BaseModel):
    """Restored HD wallet handle. ``watch_only=True`` by default.

    Public fields carry only safe metadata. Key material is kept in private
    attributes and is reachable solely via :meth:`private_key_bytes` with the
    explicit ``allow_sign=True`` opt-in.
    """

    network: str = "mainnet"
    watch_only: bool = True
    account_fingerprint: str = ""

    _seed: bytes = PrivateAttr(default=b"")
    _account_priv: bytes = PrivateAttr(default=b"")
    _account_chain: bytes = PrivateAttr(default=b"")

    @field_validator("network")
    @classmethod
    def _check_network(cls, value: str) -> str:
        if value not in _NETWORKS:
            raise ValueError(f"unknown network {value!r}")
        return value

    @classmethod
    def from_mnemonic(cls, phrase: str, passphrase: str = "", network: str = "mainnet") -> Wallet:
        """Restore a wallet from a BIP39 recovery phrase (checksum-validated).

        Raises :class:`ourdash.errors.WalletError` for a bad checksum/wordlist,
        a non-string/empty phrase, or an unknown network — never echoing the
        phrase, passphrase, or derived secrets.
        """
        if network not in _NETWORKS:
            raise WalletError(f"unknown network {redact(network)!r}")
        if not isinstance(phrase, str) or not phrase.strip():
            raise WalletError("recovery phrase must be a non-empty string")
        if not isinstance(passphrase, str):
            raise WalletError("passphrase must be a string")
        normalized = " ".join(phrase.strip().split())
        if not Mnemonic("english").check(normalized):
            raise WalletError("invalid recovery phrase (wordlist or checksum failure)")
        seed = Mnemonic("english").to_seed(normalized, passphrase=passphrase)
        master = _hmac_sha512(b"Bitcoin seed", seed)
        master_priv, master_chain = master[:32], master[32:]
        if not 0 < int.from_bytes(master_priv, "big") < _CURVE_ORDER:
            raise WalletError("BIP32 master key derivation failed")
        account_priv, account_chain = master_priv, master_chain
        for level in (44 + _HARDENED, COIN_TYPE + _HARDENED, _HARDENED):
            account_priv, account_chain = _ckd_priv(account_priv, account_chain, level)
        fingerprint = _hash160(_priv_to_compressed_pub(account_priv))[:4].hex()
        wallet = cls(network=network, watch_only=True, account_fingerprint=fingerprint)
        wallet._seed = seed
        wallet._account_priv = account_priv
        wallet._account_chain = account_chain
        logger.debug("restored wallet network=%s fingerprint=%s", network, fingerprint)
        return wallet

    def derivation_path(self, index: int = 0) -> str:
        """Return the BIP44 path string for a receiving ``index``."""
        self._check_index(index)
        return f"m/44'/{COIN_TYPE}'/0'/0/{index}"

    def _receiving_priv(self, index: int) -> bytes:
        """Return the secret key at ``m/44'/5'/0'/0/{index}``."""
        node_priv, node_chain = _ckd_priv(self._account_priv, self._account_chain, 0)
        priv, _ = _ckd_priv(node_priv, node_chain, index)
        return priv

    def receiving_address(self, index: int = 0) -> str:
        """Derive the P2PKH receiving address at ``m/44'/5'/0'/0/{index}``."""
        self._check_index(index)
        priv = self._receiving_priv(index)
        address = derive_p2pkh(_hash160(_priv_to_compressed_pub(priv)), self.network)
        logger.debug("derived address network=%s index=%d", self.network, index)
        return address

    def public_key_bytes(self, index: int = 0) -> bytes:
        """Return the 33-byte compressed public key for a receiving ``index`` (public)."""
        self._check_index(index)
        return _priv_to_compressed_pub(self._receiving_priv(index))

    def private_key_bytes(self, index: int = 0, *, allow_sign: bool = False) -> bytes:
        """Return the 32-byte secret for a receiving ``index`` (explicit opt-in only).

        Requires ``allow_sign=True`` and always emits a custody ``UserWarning``.
        Anything else raises :class:`ourdash.errors.WalletError`.
        """
        self._check_index(index)
        if allow_sign is not True:
            raise WalletError(
                "refusing to expose private key material without explicit "
                "allow_sign=True (wallet is watch-only by default)"
            )
        warnings.warn(CUSTODY_WARNING, UserWarning, stacklevel=2)
        return self._receiving_priv(index)

    @staticmethod
    def _check_index(index: int) -> None:
        if isinstance(index, bool) or not isinstance(index, int):
            raise WalletError(f"address index must be an int, got {type(index).__name__}")
        if not 0 <= index < _MAX_CHILD_INDEX:
            raise WalletError(f"address index out of range: {index!r}")

    def __repr__(self) -> str:
        return str(
            redact(
                f"Wallet(network={self.network!r}, watch_only={self.watch_only!r}, "
                f"account_fingerprint={self.account_fingerprint!r})"
            )
        )

    def __str__(self) -> str:
        return repr(self)


def from_mnemonic(phrase: str, passphrase: str = "", network: str = "mainnet") -> Wallet:
    """Restore a :class:`Wallet` from a BIP39 recovery phrase. See :meth:`Wallet.from_mnemonic`."""
    return Wallet.from_mnemonic(phrase, passphrase=passphrase, network=network)
