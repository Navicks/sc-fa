from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException, RequestValidationError
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.exc import NoResultFound
from sqlmodel import select
from starlette import status

from app.api import site as api_site
from app.cache import token as cache_token
from app.database import get_async_session
from app.database.redis import create_redis_client
from app.deps import auth
from app.models.token import Token, TokenCreate, TokenRead, TokenUpdate
from app.models.user import User
from app.models.user_site import SitePermission, UserSite

router = APIRouter(
    prefix="/sites",
    tags=["Tokens"],
)


@router.post(
    "/{site_id}/tokens/",
    response_model=TokenRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Token",
    description="Create a new token for a site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def create_token(
    site_id: int,
    create: TokenCreate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    user_sites: Annotated[
        dict[int, UserSite] | None, Depends(auth.get_current_user_site)
    ],
    session=Depends(get_async_session),
) -> Token:
    await api_site.read_site_by_id(site_id, current_user, user_sites, session)
    if not current_user.is_admin and user_sites[site_id] <= SitePermission.WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    token = Token.model_validate(create.model_dump() | {"site_id": site_id})
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


@router.get(
    "/{site_id}/tokens/",
    response_model=list[TokenRead],
    summary="Get Tokens for Site",
    description="Get all tokens for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def read_tokens_for_site(
    site_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    user_sites: Annotated[
        dict[int, UserSite] | None, Depends(auth.get_current_user_site)
    ],
    l: int = Query(default=10, gt=0, le=1000),
    o: int = Query(default=0, ge=0),
    session=Depends(get_async_session),
) -> list[Token]:
    if not current_user.is_admin and site_id not in (user_sites or {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )

    stmt = select(Token).where(Token.site_id == site_id).limit(l).offset(o)
    tokens = (await session.execute(stmt)).scalars().all()
    return tokens


@router.get(
    "/{site_id}/tokens/{token}/",
    response_model=TokenRead,
    status_code=status.HTTP_200_OK,
    summary="Get Token by Token String",
    description="Get a token by its token string for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site or token not found"}},
)
async def read_token_by_token(
    site_id: int,
    token: str,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    user_sites: Annotated[
        dict[int, UserSite] | None, Depends(auth.get_current_user_site)
    ],
    session=Depends(get_async_session),
) -> Token:
    if not current_user.is_admin and site_id not in (user_sites or {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site or token not found"
        )

    stmt = select(Token).where(Token.token == token, Token.site_id == site_id)
    try:
        token = (await session.execute(stmt)).scalars().one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site or token not found"
        ) from e
    return token


@router.get(
    "/{site_id}/tokens/id/{token_id}/",
    response_model=TokenRead,
    status_code=status.HTTP_200_OK,
    summary="Get Token by ID",
    description="Get a token by its ID for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site or token not found"}},
)
async def read_token_by_id(
    site_id: int,
    token_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    user_sites: Annotated[
        dict[int, UserSite] | None, Depends(auth.get_current_user_site)
    ],
    session=Depends(get_async_session),
) -> Token:
    if not current_user.is_admin and site_id not in (user_sites or {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site or token not found"
        )

    stmt = select(Token).where(Token.id == token_id, Token.site_id == site_id)
    try:
        token = (await session.execute(stmt)).scalars().one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site or token not found"
        ) from e
    return token


@router.patch(
    "/{site_id}/tokens/id/{token_id}/",
    response_model=TokenRead,
    status_code=status.HTTP_200_OK,
    summary="Update Token",
    description="Update an existing token for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site or token not found"}},
)
async def update_token(
    site_id: int,
    token_id: int,
    update: TokenUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    user_sites: Annotated[
        dict[int, UserSite] | None, Depends(auth.get_current_user_site)
    ],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session=Depends(get_async_session),
) -> Token:
    token = await read_token_by_id(site_id, token_id, current_user, user_sites, session)

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(token, key, value)

    if token.valid_from and token.valid_to and token.valid_from >= token.valid_to:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": (
                        "valid_from" if update.valid_from is not None else "valid_to",
                    ),
                    "msg": "Value error, valid_from must be before valid_to",
                    "input": (
                        {"valid_from": update.valid_from}
                        if update.valid_from is not None
                        else {"valid_to": update.valid_to}
                    ),
                    "ctx": {
                        "error": None,
                        **(
                            {"valid_to": token.valid_to}
                            if update.valid_from is not None
                            else {"valid_from": token.valid_from}
                        ),
                    },
                },
            ]
        )

    await session.refresh(token, attribute_names=["site"])
    await cache_token.delete(redis, token)
    await session.commit()
    return token


@router.delete(
    "/{site_id}/tokens/id/{token_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Token",
    description="Delete an existing token for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site or token not found"}},
)
async def delete_token(
    site_id: int,
    token_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    user_sites: Annotated[
        dict[int, UserSite] | None, Depends(auth.get_current_user_site)
    ],
    session=Depends(get_async_session),
) -> None:
    token = await read_token_by_id(site_id, token_id, current_user, user_sites, session)
    await session.refresh(token, attribute_names=["site"])
    await cache_token.delete(redis, token)
    await session.delete(token)
    await session.commit()
    return None
