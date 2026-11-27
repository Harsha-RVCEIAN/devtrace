"""Unit tests for auth routes and session-cookie / X-User-ID dependency resolution."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.core.config import settings
from app.core.security import create_session_token, hash_password
from app.main import app


def _make_user(email: str = "dev@example.com", password: str = "password123"):
    return SimpleNamespace(
        user_id=uuid4(),
        name="Dev User",
        email=email,
        role="developer",
        avatar_url=None,
        password_hash=hash_password(password),
        created_at=datetime.now(timezone.utc),
    )


def test_register_sets_session_cookie_and_returns_user():
    fake_user = _make_user()
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with (
            patch("app.api.routes.auth.register_user_with_password", return_value=fake_user),
            patch("app.api.routes.auth.get_user_oauth_summary", return_value=([], None)),
        ):
            client = TestClient(app)
            res = client.post(
                "/auth/register",
                json={"name": "Dev User", "email": "dev@example.com", "password": "password123"},
            )
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 201
    assert res.json()["email"] == "dev@example.com"
    assert settings.session_cookie_name in res.cookies


def test_login_invalid_credentials_returns_401():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with patch("app.api.routes.auth.authenticate_with_password", return_value=None):
            client = TestClient(app)
            res = client.post(
                "/auth/login",
                json={"email": "dev@example.com", "password": "wrong-password"},
            )
    finally:
        app.dependency_overrides.clear()

    assert res.status_code == 401


def test_me_requires_valid_session_cookie_and_blocks_x_user_id_in_production():
    fake_user = _make_user()
    mock_db = MagicMock()
    mock_db.scalar.return_value = fake_user
    app.dependency_overrides[get_db] = lambda: mock_db

    token = create_session_token(
        fake_user.user_id,
        settings.auth_secret_key.get_secret_value(),
    )

    try:
        with patch("app.api.routes.auth.get_user_oauth_summary", return_value=(["github"], "octocat")):
            client = TestClient(app)

            # 1. Valid session cookie succeeds
            client.cookies.set(settings.session_cookie_name, token)
            res = client.get("/auth/me")
            assert res.status_code == 200
            assert res.json()["github_username"] == "octocat"

            # 2. Without cookie in production, X-User-ID is rejected
            client.cookies.clear()
            with patch.object(settings, "environment", "production"), patch.object(settings, "debug", False):
                res_prod = client.get("/auth/me", headers={"X-User-ID": str(fake_user.user_id)})
                assert res_prod.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_github_login_returns_503_when_unconfigured():
    client = TestClient(app)
    with patch.object(settings, "github_client_id", ""):
        res = client.get("/auth/github/login")
    assert res.status_code == 503
