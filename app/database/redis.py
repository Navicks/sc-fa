from redis.asyncio import Redis as AsyncRedis


def create_redis_client() -> AsyncRedis:
    return AsyncRedis(
        host="localhost",
        port=6379,
        db=0,
        decode_responses=True,
    )
