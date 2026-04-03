from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import NoResultFound
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

from app.database import get_async_session
from app.deps import auth
from app.models.site import Site, SiteCreate, SiteRead, SiteUpdate
from app.models.user import User
from app.models.user_site import SitePermission

router = APIRouter(
    prefix="/sites",
    tags=["Sites"],
)


@router.post(
    "/",
    response_model=SiteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Site",
    description="Create a new site",
)
async def create_site(
    create: SiteCreate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Site:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create new sites",
        )

    site = Site.model_validate(create)
    session.add(site)
    await session.flush()
    await session.refresh(site)
    return site


@router.get(
    "/{site_id}/",
    response_model=SiteRead,
    status_code=status.HTTP_200_OK,
    summary="Get Site by ID",
    description="Get a site by its ID",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def read_site_by_id(
    site_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    user_sites: Annotated[
        dict[int, SitePermission] | None, Depends(auth.get_current_user_site)
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Site:
    if not current_user.is_admin and site_id not in (user_sites or {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )

    stmt = select(Site).where(Site.id == site_id)
    try:
        site = (await session.exec(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        ) from e
    return site


@router.get(
    "/fqdn/{fqdn}/",
    response_model=SiteRead,
    status_code=status.HTTP_200_OK,
    summary="Get Site by FQDN",
    description="Get a site by its FQDN",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def read_site_by_fqdn(
    fqdn: str,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    user_sites: Annotated[
        dict[int, SitePermission] | None, Depends(auth.get_current_user_site)
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Site:
    stmt = select(Site).where(Site.fqdn == fqdn)
    try:
        site = (await session.exec(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        ) from e

    if not current_user.is_admin and site.id not in (user_sites or {}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )
    return site


@router.patch(
    "/{site_id}/",
    response_model=SiteRead,
    status_code=status.HTTP_200_OK,
    summary="Update Site",
    description="Update an existing site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def update_site(
    site_id: int,
    update: SiteUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    user_sites: Annotated[
        dict[int, SitePermission] | None, Depends(auth.get_current_user_site)
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Site:
    site = await read_site_by_id(site_id, current_user, user_sites, session)
    if not current_user.is_admin and (
        user_sites is None or user_sites[site_id] < SitePermission.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(site, key, value)
    await session.flush()
    await session.refresh(site)
    return site
