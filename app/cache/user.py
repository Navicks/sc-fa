import hashlib

from redis.asyncio import Redis as AsyncRedis

from app.cache import _CACHE_MAX_TTL
from app.models.user import User


def get_key(email: str) -> str:
    """Generate a Redis cache key for a given email."""
    return f"user:{hashlib.sha256(email.encode()).hexdigest()}"


async def get(redis: AsyncRedis, email: str) -> User | None:
    """Get the Redis cache value for a given email."""
    cache: str | None = await redis.get(get_key(email))
    if cache is None:
        return None
    return User.model_validate_json(cache)


async def set(redis: AsyncRedis, user: User):
    """Set the Redis cache for a given User instance."""
    await redis.set(
        get_key(user.email),
        user.model_dump_json(),
        ex=_CACHE_MAX_TTL,
    )


async def delete(redis: AsyncRedis, user: User | str):
    """Delete the Redis cache for a given User instance or email."""
    email = user.email if isinstance(user, User) else user
    await redis.delete(get_key(email))
