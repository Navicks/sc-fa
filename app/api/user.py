from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.exc import NoResultFound
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

from app.cache import user as cache_user
from app.database import get_async_session
from app.database.redis import create_redis_client
from app.deps import auth
from app.models.user import User, UserCreate, UserRead, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Only admin users can create new users"
        }
    },
)
async def create_user(
    create: UserCreate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create new users",
        )

    new_user = User.model_validate(create.model_dump() | {"hashed_password": ""})
    new_user.set_password(create.password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@router.get(
    "/me/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get the currently authenticated user",
)
async def read_current_user(
    current_user: Annotated[User, Depends(auth.get_current_user)],
) -> User:
    return current_user


@router.get(
    "/{user_id}/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get User by ID",
    description="Get a user by their ID",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Only admin users can access other users' information"
        },
        status.HTTP_404_NOT_FOUND: {"description": "User not found"},
    },
)
async def read_user_by_id(
    user_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    if current_user.id == user_id:
        return current_user

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access other users' information",
        )

    stmt = select(User).where(User.id == user_id)
    try:
        user = (await session.exec(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        ) from e
    return user


@router.get(
    "/email/{email}/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get User by Email",
    description="Get a user by their email",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Only admin users can access other users' information"
        },
        status.HTTP_404_NOT_FOUND: {"description": "User not found"},
    },
)
async def read_user_by_email(
    email: str,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    redis: Annotated[AsyncRedis, Depends(auth.create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    if current_user.email == email:
        return current_user

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access other users' information",
        )

    user = await auth.get_user_by_email(email, session, redis)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.patch(
    "/me/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update Current User",
    description="Update the currently authenticated user",
)
async def update_current_user(
    update: UserUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    user = current_user

    for key, value in update.model_dump(exclude_unset=True).items():
        if key == "password":
            user.set_password(value)
        else:
            setattr(user, key, value)

    await cache_user.delete(redis, user)
    await session.commit()
    await session.refresh(user)
    return user


@router.patch(
    "/{user_id}/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update User",
    description="Update an existing user",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Only admin users can access other users' information"
        },
        status.HTTP_404_NOT_FOUND: {"description": "User not found"},
    },
)
async def update_user(
    user_id: int,
    update: UserUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access other users' information",
        )

    user = await read_user_by_id(user_id, current_user, session)
    for key, value in update.model_dump(exclude_unset=True).items():
        if key == "password":
            user.set_password(value)
        else:
            setattr(user, key, value)

    await cache_user.delete(redis, user)
    await session.commit()
    await session.refresh(user)
    return user


@router.delete(
    "/{user_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User",
    description="Delete an existing user",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Users cannot delete themselves"},
        status.HTTP_403_FORBIDDEN: {
            "description": "Only admin users can delete other users"
        },
        status.HTTP_404_NOT_FOUND: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> None:
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users cannot delete themselves",
        )

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can delete other users",
        )

    user = await read_user_by_id(user_id, current_user, session)
    await cache_user.delete(redis, user)
    await session.delete(user)
    await session.commit()
    return None
