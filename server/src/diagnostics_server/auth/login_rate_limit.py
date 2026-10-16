from fastapi import HTTPException, status
from redis import Redis
from redis.exceptions import RedisError

from diagnostics_server.config import settings

FAILURE_LIMIT = 5
WINDOW_SECONDS = 15 * 60

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def _key(client_ip: str) -> str:
    return f"anas:auth:login-failures:{client_ip}"


def _redis_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Login protection is temporarily unavailable",
        headers={"Retry-After": "30"},
    )


def reserve_login_attempt(client_ip: str) -> None:
    """Atomically reserve an attempt or reject it when the limit is reached."""
    try:
        key = _key(client_ip)
        allowed = redis_client.eval(
            """
            local current = tonumber(redis.call('GET', KEYS[1]) or '0')
            local limit = tonumber(ARGV[1])

            if current >= limit then
                return 0
            end

            local count = redis.call('INCR', KEYS[1])
            if count == 1 then
                redis.call('EXPIRE', KEYS[1], ARGV[2])
            end

            return 1
            """,
            1,
            key,
            FAILURE_LIMIT,
            WINDOW_SECONDS,
        )

        if not allowed:
            ttl = redis_client.ttl(key)
            retry_after = ttl if ttl > 0 else WINDOW_SECONDS
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except RedisError as exc:
        raise _redis_unavailable(exc) from exc


def release_login_attempt(client_ip: str) -> None:
    """Release only this successful attempt; preserve other failures."""
    try:
        redis_client.eval(
            """
            local current = tonumber(redis.call('GET', KEYS[1]) or '0')

            if current <= 1 then
                redis.call('DEL', KEYS[1])
            else
                redis.call('DECR', KEYS[1])
            end

            return 1
            """,
            1,
            _key(client_ip),
        )
    except RedisError as exc:
        raise _redis_unavailable(exc) from exc
