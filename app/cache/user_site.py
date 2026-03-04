from redis.asyncio import Redis as AsyncRedis

from app.cache import _CACHE_MAX_TTL
from app.cache.user import get_key as get_user_key
from app.models.user import User
from app.models.user_site import SitePermission, UserSite


def get_key(email: str) -> str:
    """Generate a Redis cache key for a given email."""
    return get_user_key(email) + ":sites"


async def get(redis: AsyncRedis, email: str) -> dict[int, SitePermission] | None:
    """Get the Redis cache value for a given email."""
    cache: dict | None = await redis.hgetall(get_key(email))
    if not cache:
        return None
    return {int(k): SitePermission(int(v)) for k, v in cache.items()}


async def set(
    redis: AsyncRedis, user: User | str, user_sites: list[UserSite]
) -> dict[int, SitePermission]:
    """Set the Redis cache for a given UserSite instances."""
    cache = {}
    pipe = redis.pipeline()
    key = get_key(user.email if isinstance(user, User) else user)
    for site in user_sites:
        pipe.hset(key, site.site_id, int(site.permission))
        cache[site.site_id] = site.permission
    pipe.expire(key, _CACHE_MAX_TTL)
    await pipe.execute()
    return cache


async def delete(redis: AsyncRedis, user: User | str):
    """Delete the Redis cache for a given User instance or email."""
    email = user.email if isinstance(user, User) else user
    await redis.delete(get_key(email))
