"""Unit tests for password hashing and signed session tokens."""

from uuid import uuid4

from app.core.security import (
    create_session_token,
    hash_password,
    verify_password,
    verify_session_token,
)


def test_password_hash_and_verify():
    pw = "super-secret-passphrase-123"
    stored = hash_password(pw)

    assert stored.startswith("scrypt$")
    assert verify_password(pw, stored) is True
    assert verify_password("wrong-password", stored) is False
    assert verify_password(pw, None) is False
    assert verify_password(pw, "malformed") is False


def test_password_hash_uses_unique_salts():
    pw = "same-password"
    assert hash_password(pw) != hash_password(pw)


def test_session_token_roundtrip_and_tamper_rejection():
    uid = uuid4()
    secret = "test-secret-key"

    token = create_session_token(uid, secret, max_age_seconds=3600)
    assert verify_session_token(token, secret) == uid

    # Wrong secret fails
    assert verify_session_token(token, "wrong-secret") is None

    # Tampered payload fails
    payload_part, sig_part = token.split(".", 1)
    tampered = f"{payload_part[:-1]}A.{sig_part}"
    assert verify_session_token(tampered, secret) is None


def test_expired_session_token_rejected():
    uid = uuid4()
    secret = "test-secret-key"
    expired = create_session_token(uid, secret, max_age_seconds=-10)
    assert verify_session_token(expired, secret) is None
