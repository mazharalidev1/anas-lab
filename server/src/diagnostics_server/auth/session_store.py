from fastapi import HTTPException, status
from redis import Redis
from redis.exceptions import RedisError

from diagnostics_server.config import settings

SESSION_TTL_SECONDS = 8 * 60 * 60
SESSION_KEY_PREFIX = "anas:auth:sessions:"

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def _redis_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Session service is temporarily unavailable",
        headers={"Retry-After": "30"},
    )


def register_session(session_id: str) -> None:
    try:
        redis_client.set(
            f"{SESSION_KEY_PREFIX}{session_id}",
            "1",
            ex=SESSION_TTL_SECONDS,
        )
    except RedisError as exc:
        raise _redis_unavailable(exc) from exc


def session_is_active(session_id: str) -> bool:
    try:
        return bool(redis_client.exists(f"{SESSION_KEY_PREFIX}{session_id}"))
    except RedisError as exc:
        raise _redis_unavailable(exc) from exc


def revoke_session(session_id: str) -> None:
    try:
        redis_client.delete(f"{SESSION_KEY_PREFIX}{session_id}")
    except RedisError as exc:
        raise _redis_unavailable(exc) from exc
