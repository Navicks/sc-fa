from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis as AsyncRedis
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_async_session
from app.database.redis import create_redis_client
from app.deps import auth

router = APIRouter(tags=["Auth"])


class TokenResponse(SQLModel):
    access_token: str
    token_type: str


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Generate API Access Token",
    description="Generate an API access token using client credentials",
)
async def generate_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TokenResponse:
    user = await auth.authenticate_user(
        email=form_data.username,
        password=form_data.password,
        session=session,
        redis=redis,
    )
    if user is None:
        raise auth.create_unauthorized_exception("Bearer")
    access_token = auth.create_access_token(sub=user.email)
    return TokenResponse(access_token=access_token, token_type="bearer")
