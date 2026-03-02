import datetime

from redis.asyncio import Redis as AsyncRedis

from app.cache import _CACHE_MAX_TTL
from app.models.token import Token


def generate_key(host: str, token: str) -> str:
    """Generate a Redis cache key for a given host and token."""
    return f"token:{host}:{token}"


def get_key(token: Token, host: str | None = None) -> str:
    """Get the Redis cache key for a given Token instance."""
    return generate_key(host or token.site.fqdn, token.token)


async def get(
    redis: AsyncRedis,
    host: str,
    token: str,
) -> tuple[int, str] | None:
    """Get the Redis cache value for a given host and token."""
    value: str | None = await redis.get(generate_key(host, token))
    if value is None:
        return None
    status_code, redirect_uri = value.split("|", 1)
    return int(status_code), redirect_uri


async def set(
    redis: AsyncRedis,
    token: Token,
    now: datetime.datetime,
    site: str | None = None,
):
    """Set the Redis cache for a given Token instance."""
    ttl: int = (
        _CACHE_MAX_TTL
        if token.valid_to is None
        else min(_CACHE_MAX_TTL, int((token.valid_to - now).total_seconds()))
    )
    await redis.set(
        get_key(token, site),
        f"{token.status_code}|{token.redirect_uri}",
        ex=ttl,
    )


async def delete(
    redis: AsyncRedis,
    token: Token,
    site: str | None = None,
):
    """Delete the Redis cache for a given Token instance."""
    await redis.delete(get_key(token, site))
