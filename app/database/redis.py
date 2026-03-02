from redis.asyncio import Redis as AsyncRedis

from app.settings import redis_settings


def create_redis_client() -> AsyncRedis:
    return AsyncRedis(
        host=redis_settings.redis_host,
        port=redis_settings.redis_port,
        db=redis_settings.redis_db,
        password=redis_settings.redis_password,
        decode_responses=True,
    )
