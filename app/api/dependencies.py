
"""
DevTrace API Dependencies
=========================

Purpose
-------
Defines reusable dependencies shared by FastAPI endpoints. This module
provides request-scoped database sessions and resolves a development user
from an X-User-ID request header.

Database Session Lifecycle
--------------------------
The get_db dependency from app.db.session creates and yields a session for
the request. Its existing implementation is responsible for closing the
session and rolling back when an exception escapes the dependency scope.

Endpoints should use the injected session instead of creating independent
sessions, so database operations remain consistently scoped to the request.

Development Identity Resolution
-------------------------------
get_current_user parses the X-User-ID header as a UUID and checks whether
the corresponding user exists in app_user. Unknown user IDs are rejected.

Security Limitation
-------------------
A UUID header is not proof of identity. Any client that knows or guesses
another user's UUID may be able to impersonate that user. This dependency
is suitable only as a temporary development bridge.

Before public deployment, replace this mechanism with verified
authentication, such as signed access tokens or a trusted session system.
Authorization policies must still be applied separately to individual
projects and other protected resources.

Dependencies
------------
- app.db.session.get_db: request-scoped SQLAlchemy session provider.
- app.models.entities.User: persisted application-user entity.
- FastAPI dependency injection and HTTP exception handling.

This module does not register users, issue authentication credentials,
or decide whether a user has permission to access a particular project.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_session_token
from app.db.session import get_db
from app.models.entities import User


# Reuse one type alias throughout the API to make database-session injection
# consistent and to avoid duplicating Depends(get_db) in every endpoint.
DatabaseSession = Annotated[Session, Depends(get_db)]


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def get_current_user(
    request: Request,
    db: DatabaseSession,
    x_user_id: Annotated[UUID | None, Header(alias="X-User-ID")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User:
    """
    Resolve the authenticated user from a signed session cookie or Bearer token.

    In development/testing environments, falls back to the legacy X-User-ID header
    when no session token is supplied so existing integration tests and Swagger demos
    continue to work. Disabled in production.
    """
    secret = settings.auth_secret_key.get_secret_value()
    raw_token = request.cookies.get(settings.session_cookie_name) or _extract_bearer_token(
        authorization
    )

    resolved_user_id: UUID | None = None
    if raw_token:
        resolved_user_id = verify_session_token(raw_token, secret)
        if resolved_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session.",
            )
    elif x_user_id is not None and (
        settings.debug or settings.environment.lower() in ("development", "testing")
    ):
        resolved_user_id = x_user_id
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    statement = select(User).where(User.user_id == resolved_user_id)
    user = db.scalar(statement)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown user ID.",
        )

    return user


# Endpoints can declare current_user: CurrentUser instead of repeating the
# dependency declaration. FastAPI resolves get_current_user automatically.
CurrentUser = Annotated[User, Depends(get_current_user)]
