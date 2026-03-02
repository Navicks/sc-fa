from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as sa_create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.settings import database_settings


def create_async_engine() -> AsyncEngine:
    return sa_create_async_engine(database_settings.database_url, echo=True)


_engine_async = create_async_engine()


def generate_async_session():
    return AsyncSession(_engine_async)


async def get_async_session():
    async with generate_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
