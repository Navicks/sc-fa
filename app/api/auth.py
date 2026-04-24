import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis as AsyncRedis
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

from app.database import get_async_session
from app.database.redis import create_redis_client
from app.deps import auth
from app.models.user import User

router = APIRouter(tags=["Auth"])


class TokenResponse(SQLModel):
    access_token: str
    access_token_expires: datetime
    refresh_token: str
    refresh_token_expires: datetime
    token_type: str


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Generate API Access Token",
    description="Generate an API access token using client credentials",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid credentials"},
    },
)
async def generate_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: Request,
    response: Response,
) -> TokenResponse:
    user = await auth.authenticate_user(
        email=form_data.username,
        password=form_data.password,
        session=session,
        redis=redis,
    )
    if user is None:
        raise auth.create_unauthorized_exception("Bearer")
    jti = auth.generate_token_id()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    access_token, access_exp = auth.create_access_token(
        sub=user.email, jti=jti, now=now, request=request
    )
    refresh_token, refresh_exp = auth.create_refresh_token(
        sub=user.email, jti=jti, now=now, request=request
    )
    await auth.activate_token(jti, refresh_exp, now, redis)
    response.headers["Authorization"] = f"Bearer {access_token}"
    return TokenResponse(
        access_token=access_token,
        access_token_expires=access_exp,
        refresh_token=refresh_token,
        refresh_token_expires=refresh_exp,
        token_type="bearer",
    )


@router.get(
    "/token/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(auth.is_refresh_token)],
    summary="Refresh API Access Token",
    description="Refresh an API access token using a refresh token",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid or expired refresh token"
        },
    },
)
async def refresh_token(
    user: Annotated[User, Depends(auth.get_current_user)],
    jti: Annotated[uuid.UUID, Depends(auth.get_jti)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    request: Request,
    response: Response,
) -> TokenResponse:
    new_jti = auth.generate_token_id()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    access_token, access_exp = auth.create_access_token(
        sub=user.email, jti=new_jti, now=now, request=request
    )
    refresh_token, refresh_exp = auth.create_refresh_token(
        sub=user.email, jti=new_jti, now=now, request=request
    )
    await auth.activate_token(new_jti, refresh_exp, now, redis)
    await auth.revoke_token(jti, redis)

    response.headers["Authorization"] = f"Bearer {access_token}"
    return TokenResponse(
        access_token=access_token,
        access_token_expires=access_exp,
        refresh_token=refresh_token,
        refresh_token_expires=refresh_exp,
        token_type="bearer",
    )


@router.get(
    "/token/revoke",
    dependencies=[
        Depends(auth.get_current_user),
        Depends(auth.is_access_token),
    ],
    summary="Revoke API Access Token",
    description="Revoke the current API access token",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid or expired access token"
        },
    },
)
async def revoke_token(
    jti: Annotated[uuid.UUID, Depends(auth.get_jti)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
) -> None:
    await auth.revoke_token(jti, redis)
