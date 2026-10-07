from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import hmac
import json
import secrets
from uuid import uuid4

from linkedin.core.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return (
        f"pbkdf2_sha256${iterations}$"
        f"{_b64url_encode(salt)}${_b64url_encode(digest)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iterations_text)
        salt = _b64url_decode(salt_text)
        expected_digest = _b64url_decode(digest_text)
    except (TypeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_jwt_token(
    *,
    subject: str,
    email: str,
    token_type: str,
    expires_at: datetime,
) -> str:
    now = datetime.now(UTC)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "email": email,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid4().hex,
    }

    signing_input = (
        f"{_b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
        f"{_b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
    )
    signature = hmac.new(
        settings.auth_jwt_secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_jwt_token(token: str, *, expected_type: str | None = None) -> dict[str, str | int]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
    except ValueError as exc:
        raise ValueError("Invalid token format.") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = hmac.new(
        settings.auth_jwt_secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    try:
        actual_signature = _b64url_decode(encoded_signature)
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid token encoding.") from exc

    if not hmac.compare_digest(actual_signature, expected_signature):
        raise ValueError("Invalid token signature.")

    exp = payload.get("exp")
    token_type = payload.get("type")
    subject = payload.get("sub")
    email = payload.get("email")

    if not isinstance(exp, int):
        raise ValueError("Invalid token expiration.")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Invalid token subject.")
    if not isinstance(email, str) or not email:
        raise ValueError("Invalid token email.")
    if not isinstance(token_type, str) or not token_type:
        raise ValueError("Invalid token type.")
    if datetime.now(UTC).timestamp() >= exp:
        raise ValueError("Token has expired.")
    if expected_type is not None and token_type != expected_type:
        raise ValueError("Invalid token type.")

    return payload
