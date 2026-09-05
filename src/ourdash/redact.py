"""Secret-redaction choke point for the ourdash SDK.

All SDK logging and all ``__str__``/``__repr__`` of errors and configs pass
through :func:`redact`. Values stored under a banned key are replaced with
:data:`MASK`; everything else passes through untouched.

Banned-key matching is case-insensitive substring matching, applied
recursively to mappings, lists, and tuples, plus ``key=value`` / ``key: value``
shapes inside free text.

Conservative note: extended public keys (``xpub``) and bare ``user`` names are
safe to log in isolation, but both are banned anyway — over-redaction is
cheaper than a leaked secret.
"""

from __future__ import annotations

import logging
import re
from typing import Any

MASK = "[REDACTED]"

BANNED_KEYS: frozenset[str] = frozenset(
    {
        "mnemonic",
        "seed",
        "xprv",
        "xpub",
        "privkey",
        "private_key",
        "privatekey",
        "password",
        "passphrase",
        "rpcpassword",
        "cookie",
        "auth",
        "user",
    }
)

_BANNED_ALTERNATION = "|".join(
    sorted((re.escape(key) for key in BANNED_KEYS), key=len, reverse=True)
)
_KEY_VALUE_RE = re.compile(
    r"(" + _BANNED_ALTERNATION + r")(\s*['\"]?\s*[:=]\s*['\"]?)([^\s,'\"}\]]+)",
    re.IGNORECASE,
)


def _is_banned(key: str) -> bool:
    lowered = key.lower()
    return any(banned in lowered for banned in BANNED_KEYS)


def redact(obj: Any) -> Any:
    """Return a copy of ``obj`` with secret values replaced by :data:`MASK`.

    Mappings mask values under banned keys (recursing into safe values);
    lists/tuples are mapped element-wise; strings get ``key=value``-shaped
    secrets masked; every other value is returned as-is.
    """
    if isinstance(obj, dict):
        return {
            key: (MASK if _is_banned(str(key)) else redact(value)) for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [redact(value) for value in obj]
    if isinstance(obj, tuple):
        return tuple(redact(value) for value in obj)
    if isinstance(obj, str):
        return _KEY_VALUE_RE.sub(lambda match: match.group(1) + match.group(2) + MASK, obj)
    return obj


class RedactionFilter(logging.Filter):
    """Logging filter that applies :func:`redact` to record message and args."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.msg)
        if record.args:
            record.args = redact(record.args)
        return True
