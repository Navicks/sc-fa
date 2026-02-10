import datetime
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import NoResultFound
from sqlmodel import select
from starlette import status

from app.database import get_async_session
from app.models.user import User
from app.settings import auth_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
http_basic = HTTPBasic()


def create_unauthorized_exception(scheme: str = "Bearer") -> HTTPException:
    """Create a 401 Unauthorized exception for the given authentication scheme."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": scheme},
    )


async def get_user_by_email(email: str, session) -> User | None:
    """Get a user by email. Returns None if not found."""
    stmt = select(User).where(User.email == email)
    try:
        result = (await session.execute(stmt)).one()
        return result[0] if isinstance(result, Row) else result
    except NoResultFound:
        return None


async def authenticate_user(email: str, password: str, session) -> User | None:
    """Authenticate a user by email and password. Returns None on failure."""
    user = await get_user_by_email(email, session)
    if user is None or not user.verify_password(password):
        return None
    return user


def create_access_token(sub: str) -> str:
    payload = {
        "sub": sub,
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=auth_settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        auth_settings.secret_key,
        algorithm=auth_settings.algorithm,
    )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session=Depends(get_async_session)
) -> User:
    """Get the current user from a Bearer token."""
    unauthorized = create_unauthorized_exception("Bearer")
    try:
        payload = jwt.decode(
            token,
            auth_settings.secret_key,
            algorithms=[auth_settings.algorithm],
        )
        email: str | None = payload.get("sub")
        if email is None:
            raise unauthorized
    except jwt.PyJWTError:
        raise unauthorized

    user = await get_user_by_email(email, session)
    if user is None:
        raise unauthorized
    return user


async def docs_authenticate(
    credentials: Annotated[HTTPBasicCredentials, Depends(http_basic)],
    session=Depends(get_async_session),
) -> User:
    """Authenticate a user via Basic auth (for API docs access)."""
    user = await authenticate_user(
        credentials.username,
        credentials.password,
        session,
    )
    if user is None:
        raise create_unauthorized_exception("Basic")
    return user
