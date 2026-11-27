"""
app/services/auth_service.py

Business logic for email/password registration & login and OAuth account linking.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import encrypt_oauth_token, hash_password, verify_password
from app.models.entities import OAuthAccount, User


class EmailAlreadyExistsError(Exception):
    """Raised when registering with an email that already exists."""


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user_with_password(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
) -> User:
    """Create a new email/password user after checking uniqueness."""
    normalized = _normalize_email(email)
    existing = db.scalar(select(User).where(User.email == normalized))
    if existing is not None:
        raise EmailAlreadyExistsError("An account with this email already exists.")

    user = User(
        name=name.strip(),
        email=normalized,
        role="developer",
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_with_password(
    db: Session,
    *,
    email: str,
    password: str,
) -> User | None:
    """Verify email and password; returns User on success or None on failure."""
    normalized = _normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized))
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def upsert_oauth_user(
    db: Session,
    *,
    provider: str,
    provider_user_id: str,
    email: str,
    name: str,
    avatar_url: str | None = None,
    provider_username: str | None = None,
    access_token: str | None = None,
    scopes: str | None = None,
) -> User:
    """
    Find or create a User for an OAuth login and persist/refresh their OAuthAccount.

    Resolution order:
    1. Existing (provider, provider_user_id) row -> refresh token/username/avatar.
    2. Existing app_user with matching verified email -> link new OAuthAccount.
    3. Neither exists -> create new app_user + OAuthAccount in one transaction.
    """
    encrypted_token = (
        encrypt_oauth_token(access_token, settings.auth_secret_key.get_secret_value())
        if access_token
        else None
    )

    oauth_row = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )

    if oauth_row is not None:
        if provider_username is not None:
            oauth_row.provider_username = provider_username
        if encrypted_token is not None:
            oauth_row.access_token_encrypted = encrypted_token
        if scopes is not None:
            oauth_row.scopes = scopes

        user = db.scalar(select(User).where(User.user_id == oauth_row.user_id))
        if user is not None and avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        db.commit()
        if user is not None:
            db.refresh(user)
        return user  # type: ignore[return-value]

    normalized_email = _normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        user = User(
            name=name.strip() or normalized_email.split("@")[0],
            email=normalized_email,
            role="developer",
            avatar_url=avatar_url,
            password_hash=None,
        )
        db.add(user)
        db.flush()
    elif avatar_url and not user.avatar_url:
        user.avatar_url = avatar_url

    new_oauth = OAuthAccount(
        user_id=user.user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_username=provider_username,
        access_token_encrypted=encrypted_token,
        scopes=scopes,
    )
    db.add(new_oauth)
    db.commit()
    db.refresh(user)
    return user


def get_user_oauth_summary(db: Session, user: User) -> tuple[list[str], str | None]:
    """Return (linked_providers, github_username) for a user."""
    accounts = list(
        db.scalars(select(OAuthAccount).where(OAuthAccount.user_id == user.user_id)).all()
    )
    providers = [acc.provider for acc in accounts]
    github_username = next(
        (acc.provider_username for acc in accounts if acc.provider == "github"),
        None,
    )
    return providers, github_username
