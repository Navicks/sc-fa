from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import NoResultFound
from sqlmodel import SQLModel, select
from starlette import status

from app.database import get_async_session
from app.deps import auth
from app.models.site import Site, SiteCreate, SiteRead, SiteUpdate
from app.models.token import Token, TokenCreate, TokenRead, TokenUpdate
from app.models.user import User

app = FastAPI()


@app.get("/")
async def read_root():
    return {"message": "Hello from fa!"}


class TokenResponse(SQLModel):
    access_token: str
    token_type: str


@app.post(
    "/token",
    response_model=TokenResponse,
    summary="Generate API Access Token",
    description="Generate an API access token using client credentials",
)
async def generate_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session=Depends(get_async_session),
) -> TokenResponse:
    user = await auth.authenticate_user(
        email=form_data.username,
        password=form_data.password,
        session=session,
    )
    access_token = auth.create_access_token(sub=user.email)
    return TokenResponse(access_token=access_token, token_type="bearer")


@app.post(
    "/sites/",
    response_model=SiteRead,
    status_code=201,
    summary="Create Site",
    description="Create a new site",
)
async def create_site(
    create: SiteCreate,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Site:
    site = Site.model_validate(create)
    session.add(site)
    await session.commit()
    await session.refresh(site)
    return site


@app.get(
    "/sites/{site_id}/",
    response_model=SiteRead,
    status_code=200,
    summary="Get Site by ID",
    description="Get a site by its ID",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def read_site_by_id(
    site_id: int,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Site:
    stmt = select(Site).where(Site.id == site_id)
    try:
        site = (await session.execute(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        ) from e
    return site[0] if isinstance(site, Row) else site


@app.get(
    "/sites/fqdn/{fqdn}/",
    response_model=SiteRead,
    status_code=200,
    summary="Get Site by FQDN",
    description="Get a site by its FQDN",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def read_site_by_fqdn(
    fqdn: str,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Site:
    stmt = select(Site).where(Site.fqdn == fqdn)
    try:
        site = (await session.execute(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        ) from e
    return site[0] if isinstance(site, Row) else site


@app.patch(
    "/sites/{site_id}/",
    response_model=SiteRead,
    status_code=200,
    summary="Update Site",
    description="Update an existing site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def update_site(
    site_id: int,
    update: SiteUpdate,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Site:
    site = await read_site_by_id(site_id, user, session)

    for key, value in update.model_dump(exclude_unset=True).items():
        print(f"{key} = '{value}'")
        setattr(site, key, value)

    await session.commit()
    await session.refresh(site)
    return site


@app.post(
    "/sites/{site_id}/tokens/",
    response_model=TokenRead,
    status_code=201,
    summary="Create Token",
    description="Create a new token for a site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def create_token(
    site_id: int,
    create: TokenCreate,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Token:
    await read_site_by_id(site_id, user, session)

    token = Token.model_validate(create.model_dump() | {"site_id": site_id})
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


@app.get(
    "/sites/{site_id}/tokens/{token}/",
    response_model=TokenRead,
    status_code=200,
    summary="Get Token by Token String",
    description="Get a token by its token string for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Token not found"}},
)
async def read_token_by_token(
    site_id: int,
    token: str,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Token:
    await read_site_by_id(site_id, user, session)

    stmt = select(Token).where(Token.token == token, Token.site_id == site_id)
    try:
        token = (await session.execute(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        ) from e
    return token[0] if isinstance(token, Row) else token


@app.get(
    "/sites/{site_id}/tokens/id/{token_id}/",
    response_model=TokenRead,
    status_code=200,
    summary="Get Token by ID",
    description="Get a token by its ID for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Token not found"}},
)
async def read_token_by_id(
    site_id: int,
    token_id: int,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Token:
    await read_site_by_id(site_id, user, session)

    stmt = select(Token).where(Token.id == token_id, Token.site_id == site_id)
    try:
        token = (await session.execute(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        ) from e
    return token[0] if isinstance(token, Row) else token


@app.patch(
    "/sites/{site_id}/tokens/id/{token_id}/",
    response_model=TokenRead,
    status_code=200,
    summary="Update Token",
    description="Update an existing token for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Token not found"}},
)
async def update_token(
    site_id: int,
    token_id: int,
    update: TokenUpdate,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Token:
    token = await read_token_by_id(site_id, token_id, user, session)

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(token, key, value)

    await session.commit()
    await session.refresh(token)
    return token


@app.delete(
    "/sites/{site_id}/tokens/id/{token_id}/",
    status_code=204,
    summary="Delete Token",
    description="Delete an existing token for a specific site",
    responses={404: {"description": "Token not found"}},
)
async def delete_token(
    site_id: int,
    token_id: int,
    user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> None:
    token = await read_token_by_id(site_id, token_id, user, session)
    await session.delete(token)
    await session.commit()
    return None
