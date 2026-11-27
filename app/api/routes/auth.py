"""
app/api/routes/auth.py

Authentication routes for GitHub OAuth (primary), Google OAuth (secondary),
and email/password login & registration (fallback).
"""

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.core.security import create_session_token
from app.schemas.auth import AuthUserResponse, LoginRequest, RegisterRequest
from app.services.auth_service import (
    EmailAlreadyExistsError,
    authenticate_with_password,
    get_user_oauth_summary,
    register_user_with_password,
    upsert_oauth_user,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])

_STATE_COOKIE_NAME = "devtrace_oauth_state"


def _set_session_cookie(response: Response, user_id) -> None:
    token = create_session_token(
        user_id=user_id,
        secret_key=settings.auth_secret_key.get_secret_value(),
        max_age_seconds=settings.session_max_age_seconds,
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.environment.lower() == "production",
        max_age=settings.session_max_age_seconds,
        path="/",
    )


def _build_auth_user_response(db: DatabaseSession, user) -> AuthUserResponse:
    providers, github_username = get_user_oauth_summary(db, user)
    return AuthUserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        role=user.role,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        linked_providers=providers,
        github_username=github_username,
    )


@router.post(
    "/register",
    response_model=AuthUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user with email and password",
)
def register(payload: RegisterRequest, response: Response, db: DatabaseSession) -> AuthUserResponse:
    try:
        user = register_user_with_password(
            db,
            name=payload.name,
            email=str(payload.email),
            password=payload.password,
        )
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    _set_session_cookie(response, user.user_id)
    return _build_auth_user_response(db, user)


@router.post(
    "/login",
    response_model=AuthUserResponse,
    summary="Sign in with email and password",
)
def login(payload: LoginRequest, response: Response, db: DatabaseSession) -> AuthUserResponse:
    user = authenticate_with_password(
        db,
        email=str(payload.email),
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    _set_session_cookie(response, user.user_id)
    return _build_auth_user_response(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Clear session cookie")
def logout(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")


@router.get("/me", response_model=AuthUserResponse, summary="Get the current authenticated user")
def get_me(current_user: CurrentUser, db: DatabaseSession) -> AuthUserResponse:
    return _build_auth_user_response(db, current_user)


@router.get("/github/login", summary="Redirect to GitHub OAuth")
def github_login(request: Request) -> RedirectResponse:
    if not settings.github_client_id or not settings.github_client_secret.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured on the server.",
        )

    state = secrets.token_urlsafe(24)
    callback_url = str(request.url_for("github_callback"))
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": callback_url,
            "scope": "read:user user:email repo",
            "state": state,
        }
    )
    redirect = RedirectResponse(url=f"https://github.com/login/oauth/authorize?{params}")
    redirect.set_cookie(
        key=_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return redirect


@router.get("/github/callback", name="github_callback", summary="Handle GitHub OAuth callback")
def github_callback(
    request: Request,
    db: DatabaseSession,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    expected_state = request.cookies.get(_STATE_COOKIE_NAME)
    if not code or not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state.",
        )

    callback_url = str(request.url_for("github_callback"))
    with httpx.Client(timeout=15.0) as client:
        token_res = client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret.get_secret_value(),
                "code": code,
                "redirect_uri": callback_url,
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GitHub token exchange failed.")
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub did not return an access token.")

        gh_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        profile_res = client.get("https://api.github.com/user", headers=gh_headers)
        if profile_res.status_code != 200:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch GitHub profile.")
        profile = profile_res.json()

        email = profile.get("email")
        if not email:
            emails_res = client.get("https://api.github.com/user/emails", headers=gh_headers)
            if emails_res.status_code == 200:
                for item in emails_res.json():
                    if item.get("primary") and item.get("verified"):
                        email = item.get("email")
                        break

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verified email found on GitHub account.",
        )

    user = upsert_oauth_user(
        db,
        provider="github",
        provider_user_id=str(profile["id"]),
        email=email,
        name=profile.get("name") or profile.get("login") or "GitHub User",
        avatar_url=profile.get("avatar_url"),
        provider_username=profile.get("login"),
        access_token=access_token,
        scopes=token_data.get("scope", "read:user user:email repo"),
    )

    redirect = RedirectResponse(url=settings.frontend_url)
    redirect.delete_cookie(key=_STATE_COOKIE_NAME, path="/")
    _set_session_cookie(redirect, user.user_id)
    return redirect


@router.get("/google/login", summary="Redirect to Google OAuth")
def google_login(request: Request) -> RedirectResponse:
    if not settings.google_client_id or not settings.google_client_secret.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on the server.",
        )

    state = secrets.token_urlsafe(24)
    callback_url = str(request.url_for("google_callback"))
    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
        }
    )
    redirect = RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}")
    redirect.set_cookie(
        key=_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return redirect


@router.get("/google/callback", name="google_callback", summary="Handle Google OAuth callback")
def google_callback(
    request: Request,
    db: DatabaseSession,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    expected_state = request.cookies.get(_STATE_COOKIE_NAME)
    if not code or not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state.",
        )

    callback_url = str(request.url_for("google_callback"))
    with httpx.Client(timeout=15.0) as client:
        token_res = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret.get_secret_value(),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_url,
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google token exchange failed.")
        access_token = token_res.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google did not return an access token.")

        userinfo_res = client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_res.status_code != 200:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch Google userinfo.")
        profile = userinfo_res.json()

    email = profile.get("email")
    if not email or not profile.get("email_verified", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No verified Google email available.")

    user = upsert_oauth_user(
        db,
        provider="google",
        provider_user_id=str(profile["sub"]),
        email=email,
        name=profile.get("name") or email.split("@")[0],
        avatar_url=profile.get("picture"),
        provider_username=None,
        access_token=None,
        scopes="openid email profile",
    )

    redirect = RedirectResponse(url=settings.frontend_url)
    redirect.delete_cookie(key=_STATE_COOKIE_NAME, path="/")
    _set_session_cookie(redirect, user.user_id)
    return redirect
