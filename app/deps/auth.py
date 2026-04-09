import datetime
import uuid
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.exc import NoResultFound
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

import app.cache.user as cache_user
import app.cache.user_site as cache_user_site
from app.database import get_async_session
from app.database.redis import create_redis_client
from app.models.user import User
from app.models.user_site import SitePermission, UserSite
from app.settings import app_settings, auth_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
http_basic = HTTPBasic(auto_error=False)


def create_unauthorized_exception(scheme: str = "Bearer") -> HTTPException:
    """Create a 401 Unauthorized exception for the given authentication scheme."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": scheme},
    )


async def get_user_by_email(
    email: str, session: AsyncSession, redis: AsyncRedis, ignore_cache: bool = False
) -> User | None:
    """Get a user by email. Returns None if not found."""
    if not ignore_cache:
        cache = await cache_user.get(redis, email)
        if cache:
            return cache

    stmt = select(User).where(User.email == email)
    try:
        user = (await session.exec(stmt)).one()
    except NoResultFound:
        return None
    await cache_user.set(redis, user)
    return user


async def authenticate_user(
    email: str, password: str, session: AsyncSession, redis: AsyncRedis
) -> User | None:
    """Authenticate a user by email and password. Returns None on failure."""
    user = await get_user_by_email(email, session, redis, ignore_cache=True)
    if user is None or not user.verify_password(password) or user.disabled:
        return None
    return user


def generate_token_id() -> uuid.UUID:
    return uuid.uuid4()


def create_access_token(
    sub: str, jti: uuid.UUID, now: datetime.datetime
) -> tuple[str, datetime.datetime]:
    expire = now + datetime.timedelta(minutes=auth_settings.access_token_expire_minutes)
    payload = {
        "iss": "fa-api access",
        "sub": sub,
        "jti": str(jti),
        "exp": expire,
    }
    return (
        jwt.encode(
            payload,
            auth_settings.secret_key,
            algorithm=auth_settings.algorithm,
        ),
        expire,
    )


def create_refresh_token(
    sub: str, jti: uuid.UUID, now: datetime.datetime
) -> tuple[str, datetime.datetime]:
    expire = now + datetime.timedelta(
        minutes=auth_settings.refresh_token_expire_minutes
    )
    payload = {
        "iss": "fa-api refresh",
        "sub": sub,
        "jti": str(jti),
        "exp": expire,
    }
    return (
        jwt.encode(
            payload,
            auth_settings.secret_key,
            algorithm=auth_settings.algorithm,
        ),
        expire,
    )


def _get_token_key(jti: uuid.UUID) -> str:
    return f"active_token:{jti}"


async def activate_token(
    jti: uuid.UUID, exp: datetime.datetime, now: datetime.datetime, redis: AsyncRedis
):
    """Mark a token as active in Redis (for revocation tracking)."""
    ttl = int((exp - now).total_seconds())
    return await redis.set(_get_token_key(jti), "true", ex=ttl)


async def revoke_token(jti: uuid.UUID, redis: AsyncRedis):
    """Revoke a token by its JTI."""
    return await redis.delete(_get_token_key(jti))


async def is_token_active(jti: uuid.UUID, redis: AsyncRedis) -> bool:
    """Check if a token is active (not revoked)."""
    return await redis.exists(_get_token_key(jti)) == 1


def get_token_payload(token: Annotated[str, Depends(oauth2_scheme)]) -> dict[str, Any]:
    """Decode a JWT token and return its payload."""
    try:
        payload = jwt.decode(
            token,
            auth_settings.secret_key,
            algorithms=[auth_settings.algorithm],
        )
        return payload
    except jwt.PyJWTError:
        raise create_unauthorized_exception("Bearer")


async def get_current_user(
    payload: Annotated[dict[str, Any], Depends(get_token_payload)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    """Get the current user from a Bearer token."""
    unauthorized = create_unauthorized_exception("Bearer")
    email: str | None = payload.get("sub")
    if email is None:
        raise unauthorized
    if not await is_token_active(get_jti(payload), redis):
        raise unauthorized
    exp = payload.get("exp")
    if exp is None or datetime.datetime.fromtimestamp(
        exp, tz=datetime.timezone.utc
    ) < datetime.datetime.now(tz=datetime.timezone.utc):
        raise unauthorized

    user = await get_user_by_email(email, session, redis)
    if user is None:
        raise unauthorized
    return user


def get_jti(
    payload: Annotated[dict[str, Any], Depends(get_token_payload)],
) -> uuid.UUID:
    """Get the JTI (token ID) from a Bearer token payload."""
    jti: str | None = payload.get("jti")
    if jti is None:
        raise create_unauthorized_exception("Bearer")
    return uuid.UUID(jti)


async def docs_authenticate(
    credentials: Annotated[HTTPBasicCredentials, Depends(http_basic)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    """Authenticate a user via Basic auth (for API docs access)."""
    if app_settings.debug:
        return User(
            id=0,
            email="debug@example.com",
            display_name="Debug User",
            disabled=False,
            is_admin=True,
            hashed_password="",
        )
    if credentials is None:
        raise create_unauthorized_exception("Basic")

    user = await authenticate_user(
        credentials.username,
        credentials.password,
        session,
        redis,
    )
    if user is None:
        raise create_unauthorized_exception("Basic")
    return user


async def get_current_user_site(
    current_user: Annotated[User, Depends(get_current_user)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[int, SitePermission] | None:
    """Get the current user's site association, if any."""
    cache = await cache_user_site.get(redis, current_user.email)
    if cache:
        return cache

    stmt = select(UserSite).where(UserSite.user_id == current_user.id)
    rows = (await session.exec(stmt)).all()
    return await cache_user_site.set(redis, current_user, rows)
