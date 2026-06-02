from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any


def encrypt_json(payload: dict[str, Any]) -> str:
    fernet = _fernet()
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")
    return fernet.encrypt(raw).decode("ascii")


def decrypt_json(ciphertext: str | None) -> dict[str, Any]:
    if not ciphertext:
        return {}
    fernet = _fernet()
    raw = fernet.decrypt(ciphertext.encode("ascii"))
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Encrypted payload must decode to a JSON object.")
    return parsed


def private_lookup_hash(value: str) -> str:
    normalized = value.strip().lower().encode("utf-8")
    return hmac.new(_hash_key(), normalized, hashlib.sha256).hexdigest()


def ticker_lookup_hash(value: str) -> str:
    normalized = value.strip().upper().encode("utf-8")
    return hmac.new(_hash_key(), normalized, hashlib.sha256).hexdigest()


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Encrypted persistent storage requires the 'cryptography' package. "
            "Install project dependencies or run through Docker."
        ) from exc

    return Fernet(_fernet_key())


def _fernet_key() -> bytes:
    key_material = _encryption_key_material()
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _hash_key() -> bytes:
    return _encryption_key_material().encode("utf-8")


def _encryption_key_material() -> str:
    configured = os.getenv("DATA_ENCRYPTION_KEY") or os.getenv("AUTH_SECRET_KEY")
    if configured:
        return configured
    return "dev-only-change-me"
