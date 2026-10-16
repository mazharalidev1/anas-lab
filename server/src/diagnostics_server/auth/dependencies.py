import secrets

from fastapi import Header, HTTPException, status

from diagnostics_server.config import settings


def require_agent_token(authorization: str | None = Header(default=None)) -> None:
    expected = settings.agent_token
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not expected or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token", headers={"WWW-Authenticate": "Bearer"})
