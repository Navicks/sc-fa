from typing import AsyncGenerator

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as sa_create_async_engine
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.settings import database_settings


def create_sync_engine() -> Engine:
    return create_engine(
        f"{database_settings.database_sync_schema}://"
        f"{database_settings.database_url_suffix}",
        echo=database_settings.database_echo,
    )


def create_async_engine() -> AsyncEngine:
    return sa_create_async_engine(
        f"{database_settings.database_async_schema}://"
        f"{database_settings.database_url_suffix}",
        echo=database_settings.database_echo,
    )


_engine_async = create_async_engine()


def generate_sync_session(engine: Engine) -> Session:
    return Session(engine)


def generate_async_session() -> AsyncSession:
    return AsyncSession(_engine_async)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with generate_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
