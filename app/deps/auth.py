import datetime
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import NoResultFound
from sqlmodel import select
from starlette import status

from app.database import get_async_session
from app.models.user import User
from app.settings import auth_settings

UNAUTHORIZED_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def authenticate_user(email: str, password: str, session) -> User | None:
    print("Entring authenticate_user")
    stmt = select(User).where(User.email == email)
    try:
        user = (await session.execute(stmt)).one()
    except NoResultFound:
        raise UNAUTHORIZED_EXCEPTION
    if isinstance(user, Row):
        user = user[0]
    if not user.verify_password(password):
        raise UNAUTHORIZED_EXCEPTION
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
            raise UNAUTHORIZED_EXCEPTION
    except jwt.PyJWTError:
        raise UNAUTHORIZED_EXCEPTION
    stmt = select(User).where(User.email == email)
    try:
        user = (await session.execute(stmt)).one()
    except NoResultFound:
        raise UNAUTHORIZED_EXCEPTION
    return user
