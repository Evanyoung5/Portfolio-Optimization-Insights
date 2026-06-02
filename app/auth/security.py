from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

_PASSWORD_ITERATIONS = 260_000
_TOKEN_ALGORITHM = "HS256"
_DEFAULT_TOKEN_SECONDS = 60 * 60 * 24 * 7


class AuthError(ValueError):
    """Raised when an auth token is invalid or expired."""


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise ValueError("A valid email address is required.")
    return normalized


def hash_password(password: str) -> str:
    _validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PASSWORD_ITERATIONS,
    )
    return "pbkdf2_sha256${iterations}${salt}${digest}".format(
        iterations=_PASSWORD_ITERATIONS,
        salt=base64.urlsafe_b64encode(salt).decode("ascii"),
        digest=base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            base64.urlsafe_b64decode(salt.encode("ascii")),
            int(iterations),
        )
        encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
        return hmac.compare_digest(encoded_digest, expected_digest)
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    user_id: str,
    email: str,
    expires_in_seconds: int = _DEFAULT_TOKEN_SECONDS,
) -> str:
    now = int(time.time())
    header = {"alg": _TOKEN_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": normalize_email(email),
        "iat": now,
        "exp": now + expires_in_seconds,
        "token_type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    signing_input = f"{_b64_json(header)}.{_b64_json(payload)}"
    signature = _sign(signing_input)
    return f"{signing_input}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature = token.split(".", 2)
    except ValueError as exc:
        raise AuthError("Invalid access token.") from exc

    signing_input = f"{header_b64}.{payload_b64}"
    expected_signature = _sign(signing_input)
    if not hmac.compare_digest(signature, expected_signature):
        raise AuthError("Invalid access token signature.")

    header = _from_b64_json(header_b64)
    if header.get("alg") != _TOKEN_ALGORITHM:
        raise AuthError("Unsupported access token algorithm.")

    payload = _from_b64_json(payload_b64)
    if int(payload.get("exp", 0)) < int(time.time()):
        raise AuthError("Access token has expired.")
    if payload.get("token_type") != "access":
        raise AuthError("Access token has an invalid type.")
    if not payload.get("sub"):
        raise AuthError("Access token is missing a subject.")
    return payload


def create_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hmac.new(_secret_key(), token.encode("utf-8"), hashlib.sha256).hexdigest()


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")


def _secret_key() -> bytes:
    configured = os.getenv("AUTH_SECRET_KEY")
    if configured:
        return configured.encode("utf-8")
    return b"dev-only-change-me"


def _sign(signing_input: str) -> str:
    signature = hmac.new(_secret_key(), signing_input.encode("ascii"), hashlib.sha256).digest()
    return _b64(signature)


def _b64_json(value: dict[str, Any]) -> str:
    return _b64(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _from_b64_json(value: str) -> dict[str, Any]:
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode((value + padding).encode("ascii"))
        parsed = json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthError("Invalid access token payload.") from exc
    if not isinstance(parsed, dict):
        raise AuthError("Invalid access token payload.")
    return parsed
