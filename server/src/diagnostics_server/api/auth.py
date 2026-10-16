import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

from diagnostics_server.auth.login_rate_limit import (
    release_login_attempt,
    reserve_login_attempt,
)
from diagnostics_server.auth.session_store import (
    SESSION_TTL_SECONDS,
    register_session,
    revoke_session,
    session_is_active,
)
from diagnostics_server.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

SESSION_COOKIE = "anas_admin_session"
SESSION_SALT = "anas-labs-admin-session"

password_hasher = PasswordHash.recommended()
serializer = URLSafeTimedSerializer(
    settings.session_secret,
    salt=SESSION_SALT,
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


def valid_session(cookie: str | None) -> bool:
    if not cookie:
        return False

    try:
        payload = serializer.loads(cookie, max_age=SESSION_TTL_SECONDS)
    except (BadSignature, ValueError, TypeError):
        return False

    if not isinstance(payload, dict):
        return False

    if payload.get("sub") != settings.admin_username:
        return False

    session_id = payload.get("jti")
    if not isinstance(session_id, str) or not session_id:
        return False

    return session_is_active(session_id)


def require_admin(cookie: str | None) -> None:
    if not valid_session(cookie):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )


@router.post("/login")
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
) -> dict[str, str]:
    client_ip = request.client.host if request.client else "unknown"
    reserve_login_attempt(client_ip)

    password_valid = password_hasher.verify(
        data.password,
        settings.admin_password_hash,
    )

    if data.username != settings.admin_username or not password_valid:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    session_id = secrets.token_urlsafe(32)
    register_session(session_id)

    token = serializer.dumps({
        "sub": settings.admin_username,
        "jti": session_id,
    })
    release_login_attempt(client_ip)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )

    return {
        "authenticated": "true",
        "username": settings.admin_username,
    }


@router.get("/me")
def current_admin(
    cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict[str, str]:
    require_admin(cookie)
    return {"authenticated": "true", "username": settings.admin_username}


@router.post("/logout")
def logout(
    response: Response,
    cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict[str, str]:
    # Expire the browser cookie even if Redis is temporarily unavailable.
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
    )

    if cookie:
        try:
            payload = serializer.loads(cookie, max_age=SESSION_TTL_SECONDS)
        except (BadSignature, ValueError, TypeError):
            payload = None

        if isinstance(payload, dict):
            session_id = payload.get("jti")
            if isinstance(session_id, str) and session_id:
                try:
                    revoke_session(session_id)
                except HTTPException as exc:
                    # The cookie is cleared, but report that server-side
                    # revocation could not be confirmed.
                    response.status_code = exc.status_code
                    return {
                        "authenticated": "false",
                        "detail": "Cookie cleared; session revocation unavailable",
                    }

    return {"authenticated": "false"}
