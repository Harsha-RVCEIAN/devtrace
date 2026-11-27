"""
app/core/security.py

Cryptographic primitives for password hashing and signed session tokens.

Uses Python's standard library (hashlib.scrypt + hmac + sha256) so authentication
works reliably with zero external crypto dependencies.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from uuid import UUID


_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using scrypt with a random 16-byte salt.

    Stored format: "scrypt$<salt_b64>$<derived_key_b64>"
    """
    salt = os.urandom(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii")
    derived_b64 = base64.urlsafe_b64encode(derived).decode("ascii")
    return f"scrypt${salt_b64}${derived_b64}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Verify a plaintext password against a stored scrypt hash in constant time."""
    if not stored_hash:
        return False

    parts = stored_hash.split("$")
    if len(parts) != 3 or parts[0] != "scrypt":
        return False

    try:
        salt = base64.urlsafe_b64decode(parts[1].encode("ascii"))
        expected = base64.urlsafe_b64decode(parts[2].encode("ascii"))
    except Exception:
        return False

    actual = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=len(expected),
    )
    return hmac.compare_digest(actual, expected)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def create_session_token(
    user_id: UUID,
    secret_key: str,
    max_age_seconds: int = 60 * 60 * 24 * 7,
) -> str:
    """
    Create an HMAC-SHA256 signed session token containing user_id and expiry.

    Format: "<payload_b64url>.<signature_b64url>"
    """
    payload = {
        "sub": str(user_id),
        "exp": int(time.time()) + max_age_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    sig = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_b64url_encode(sig)}"


def verify_session_token(token: str, secret_key: str) -> UUID | None:
    """
    Validate signature and expiration of a session token.

    Returns the user UUID if valid, otherwise None.
    """
    if not token or "." not in token:
        return None

    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(
        secret_key.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()

    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        return None

    if not hmac.compare_digest(actual_sig, expected_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload["exp"]) < int(time.time()):
            return None
        return UUID(payload["sub"])
    except Exception:
        return None


def _derive_fernet_key(secret_key: str) -> bytes:
    """Derive a 32-byte URL-safe base64 key suitable for Fernet from auth_secret_key."""
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_oauth_token(plaintext_token: str, secret_key: str) -> str:
    """Encrypt an OAuth access token at rest using Fernet (AES-128-CBC + HMAC-SHA256)."""
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError(
            "The 'cryptography' package is required to encrypt OAuth tokens at rest. "
            "Install it with: uv add cryptography"
        ) from exc

    fernet = Fernet(_derive_fernet_key(secret_key))
    return fernet.encrypt(plaintext_token.encode("utf-8")).decode("ascii")


def decrypt_oauth_token(encrypted_token: str, secret_key: str) -> str:
    """Decrypt a stored OAuth access token using Fernet."""
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError(
            "The 'cryptography' package is required to decrypt OAuth tokens. "
            "Install it with: uv add cryptography"
        ) from exc

    fernet = Fernet(_derive_fernet_key(secret_key))
    return fernet.decrypt(encrypted_token.encode("ascii")).decode("utf-8")
