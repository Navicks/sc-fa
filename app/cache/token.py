import datetime
from urllib import parse

from redis.asyncio import Redis as AsyncRedis

from app.cache import _CACHE_MAX_TTL
from app.models.token import Token


def generate_key(host: str, token: str) -> str:
    """Generate a Redis cache key for a given host and token."""
    return f"token:{host}:{token}"


def get_key(token: Token, host: str | None = None) -> str:
    """Get the Redis cache key for a given Token instance."""
    if host is None and token.site is None:
        raise ValueError(
            "Token must be associated with a site or host must be provided"
        )
    return generate_key(
        host or token.site.fqdn, token.token  # type: ignore[attr-defined]
    )


async def get(
    redis: AsyncRedis,
    host: str,
    token: str,
) -> tuple[int, str, bool] | None:
    """Get the Redis cache value for a given host and token."""
    value: dict = await redis.hgetall(generate_key(host, token))  # type: ignore
    if not value:
        return None
    return int(value["s"]), value["u"], value["q"] == "1"


async def set(
    redis: AsyncRedis,
    token: Token,
    now: datetime.datetime,
    site: str | None = None,
) -> None:
    """Set the Redis cache for a given Token instance."""
    ttl: int = (
        _CACHE_MAX_TTL
        if token.valid_to is None
        else min(_CACHE_MAX_TTL, int((token.valid_to - now).total_seconds()))
    )
    key: str = get_key(token, site)
    await redis.hset(
        name=key,
        mapping={
            "s": str(token.status_code),
            "u": str(token.redirect_uri),
            "q": "1" if parse.urlparse(str(token.redirect_uri)).query != "" else "0",
        }
    )  # type: ignore
    await redis.expire(key, ttl)


async def delete(
    redis: AsyncRedis,
    token: Token,
    site: str | None = None,
) -> None:
    """Delete the Redis cache for a given Token instance."""
    await redis.delete(get_key(token, site))
