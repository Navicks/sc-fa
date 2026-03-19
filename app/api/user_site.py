from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlmodel import select
from starlette import status

from app.api import user as api_user
from app.cache import user_site as cache_user_site
from app.database import get_async_session
from app.database.redis import create_redis_client
from app.deps import auth
from app.models.user import User
from app.models.user_site import (
    UserSite,
    UserSiteCreateWithoutUser,
    UserSiteRead,
    UserSiteUpdate,
)

router = APIRouter(
    prefix="/users",
    tags=["User-Sites"],
)


@router.post(
    "/{user_id}/sites/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserSiteRead,
    summary="Assign Site to User",
    description="Assign a site to a user",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Only admin users can assign sites to users"
        },
        status.HTTP_404_NOT_FOUND: {"description": "User or site not found"},
        status.HTTP_409_CONFLICT: {"description": "User already has access to site"},
    },
)
async def assign_site_to_user(
    user_id: int,
    create: UserSiteCreateWithoutUser,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session=Depends(get_async_session),
) -> UserSite:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can assign sites to users",
        )

    target_user = await api_user.read_user_by_id(user_id, current_user, session)

    try:
        user_site = UserSite.model_validate(create.model_dump() | {"user_id": user_id})
        session.add(user_site)
        await cache_user_site.delete(redis, target_user)
        await session.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User and site is already associated",
        ) from e
    await session.refresh(user_site)

    return user_site


@router.get(
    "/me/sites/",
    response_model=list[UserSiteRead],
    summary="Get Sites for Current User",
    description="Get all sites assigned to the current user",
)
async def get_sites_for_current_user(
    current_user: Annotated[User, Depends(auth.get_current_user)],
    l: int = Query(default=10, gt=0, le=1000),
    o: int = Query(default=0, ge=0),
    session=Depends(get_async_session),
) -> list[UserSite]:
    stmt = (
        select(UserSite).where(UserSite.user_id == current_user.id).limit(l).offset(o)
    )
    rows = (await session.exec(stmt)).all()
    return rows


@router.get(
    "/{user_id}/sites/",
    response_model=list[UserSiteRead],
    summary="Get Sites for User",
    description="Get all sites assigned to a user",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Only admin users can view sites for users"
        },
        status.HTTP_404_NOT_FOUND: {"description": "User or site not found"},
    },
)
async def get_sites_for_user(
    user_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    l: int = Query(default=10, gt=0, le=1000),
    o: int = Query(default=0, ge=0),
    session=Depends(get_async_session),
) -> list[UserSite]:
    await api_user.read_user_by_id(user_id, current_user, session)

    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can view sites for users",
        )

    stmt = select(UserSite).where(UserSite.user_id == user_id).limit(l).offset(o)
    rows = (await session.exec(stmt)).all()
    return rows


@router.patch(
    "/{user_id}/sites/{site_id}/",
    response_model=UserSiteRead,
    summary="Update User-Site Permission",
    description="Update a user's permission for a specific site",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Only admin users can update user-site permissions"
        },
        status.HTTP_404_NOT_FOUND: {"description": "User or site not found"},
    },
)
async def update_user_site_permission(
    user_id: int,
    site_id: int,
    update: UserSiteUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session=Depends(get_async_session),
) -> UserSite:
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can update user-site permissions",
        )
    target_user = await api_user.read_user_by_id(user_id, current_user, session)

    stmt = select(UserSite).where(
        UserSite.user_id == user_id, UserSite.site_id == site_id
    )
    try:
        user_site = (await session.exec(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User or site not found"
        ) from e

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(user_site, key, value)

    await cache_user_site.delete(redis, target_user, site_id)
    await session.commit()
    await session.refresh(user_site)
    return user_site
