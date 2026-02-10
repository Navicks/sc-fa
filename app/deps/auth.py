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

UNAUTHORIZED_BEARER_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

UNAUTHORIZED_BASIC_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
    headers={"WWW-Authenticate": "Basic"},
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
http_basic = HTTPBasic()


async def authenticate_user(email: str, password: str, session) -> User | None:
    stmt = select(User).where(User.email == email)
    try:
        user = (await session.execute(stmt)).one()
    except NoResultFound:
        raise UNAUTHORIZED_BEARER_EXCEPTION
    if isinstance(user, Row):
        user = user[0]
    if not user.verify_password(password):
        raise UNAUTHORIZED_BEARER_EXCEPTION
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
) -> User | None:
    try:
        payload = jwt.decode(
            token,
            auth_settings.secret_key,
            algorithms=[auth_settings.algorithm],
        )
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        if email is None:
            raise UNAUTHORIZED_BEARER_EXCEPTION
    except jwt.PyJWTError:
        raise UNAUTHORIZED_BEARER_EXCEPTION
    stmt = select(User).where(User.email == email)
    try:
        user = (await session.execute(stmt)).one()
    except NoResultFound:
        raise UNAUTHORIZED_BEARER_EXCEPTION
    return user[0] if isinstance(user, Row) else user


async def docs_authenticate(
    credentials: Annotated[HTTPBasicCredentials, Depends(http_basic)],
    session=Depends(get_async_session),
) -> User | None:
    try:
        user = await authenticate_user(
            credentials.username,
            credentials.password,
            session,
        )
    except HTTPException:
        raise UNAUTHORIZED_BASIC_EXCEPTION
    if user is None:
        raise UNAUTHORIZED_BASIC_EXCEPTION
    return user
