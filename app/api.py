from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import NoResultFound
from sqlmodel import SQLModel, select
from starlette import status

from app.database import get_async_session
from app.deps import auth
from app.models.site import Site, SiteCreate, SiteRead, SiteUpdate
from app.models.token import Token, TokenCreate, TokenRead, TokenUpdate
from app.models.user import User, UserCreate, UserRead, UserUpdate

app = FastAPI(
    title="fa API",
    version="0.1.0",
    description="fa API endpoints",
    docs_url=None,
    redoc_url=None,
)


@app.get("/int/docs", response_class=HTMLResponse, include_in_schema=False)
async def swagger_docs(_: User = Depends(auth.docs_authenticate)):
    return get_swagger_ui_html(
        openapi_url=app.openapi_url, title=app.title + " - Swagger UI"
    )


@app.get("/int/redoc", response_class=HTMLResponse, include_in_schema=False)
async def redoc_docs(_: User = Depends(auth.docs_authenticate)):
    return get_redoc_html(openapi_url=app.openapi_url, title=app.title + " - ReDoc")


@app.get("/", include_in_schema=False)
async def read_root():
    return {"message": "Hello"}


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
    if user is None:
        raise auth.create_unauthorized_exception("Bearer")
    access_token = auth.create_access_token(sub=user.email)
    return TokenResponse(access_token=access_token, token_type="bearer")


@app.post(
    "/sites/",
    response_model=SiteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Site",
    description="Create a new site",
)
async def create_site(
    create: SiteCreate,
    _: Annotated[User, Depends(auth.get_current_user)],
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
    status_code=status.HTTP_200_OK,
    summary="Get Site by ID",
    description="Get a site by its ID",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def read_site_by_id(
    site_id: int,
    _: Annotated[User, Depends(auth.get_current_user)],
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
    status_code=status.HTTP_200_OK,
    summary="Get Site by FQDN",
    description="Get a site by its FQDN",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def read_site_by_fqdn(
    fqdn: str,
    _: Annotated[User, Depends(auth.get_current_user)],
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
    status_code=status.HTTP_200_OK,
    summary="Update Site",
    description="Update an existing site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Site not found"}},
)
async def update_site(
    site_id: int,
    update: SiteUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Site:
    site = await read_site_by_id(site_id, current_user, session)

    for key, value in update.model_dump(exclude_unset=True).items():
        print(f"{key} = '{value}'")
        setattr(site, key, value)

    await session.commit()
    await session.refresh(site)
    return site


@app.post(
    "/sites/{site_id}/tokens/",
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
    session=Depends(get_async_session),
) -> Token:
    await read_site_by_id(site_id, current_user, session)

    token = Token.model_validate(create.model_dump() | {"site_id": site_id})
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


@app.get(
    "/sites/{site_id}/tokens/{token}/",
    response_model=TokenRead,
    status_code=status.HTTP_200_OK,
    summary="Get Token by Token String",
    description="Get a token by its token string for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Token not found"}},
)
async def read_token_by_token(
    site_id: int,
    token: str,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Token:
    await read_site_by_id(site_id, current_user, session)

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
    status_code=status.HTTP_200_OK,
    summary="Get Token by ID",
    description="Get a token by its ID for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Token not found"}},
)
async def read_token_by_id(
    site_id: int,
    token_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Token:
    await read_site_by_id(site_id, current_user, session)

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
    status_code=status.HTTP_200_OK,
    summary="Update Token",
    description="Update an existing token for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Token not found"}},
)
async def update_token(
    site_id: int,
    token_id: int,
    update: TokenUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> Token:
    token = await read_token_by_id(site_id, token_id, current_user, session)

    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(token, key, value)

    await session.commit()
    await session.refresh(token)
    return token


@app.delete(
    "/sites/{site_id}/tokens/id/{token_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Token",
    description="Delete an existing token for a specific site",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Token not found"}},
)
async def delete_token(
    site_id: int,
    token_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> None:
    token = await read_token_by_id(site_id, token_id, current_user, session)
    await session.delete(token)
    await session.commit()
    return None


@app.post(
    "/users/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user",
)
async def create_user(
    create: UserCreate,
    _: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> User:
    new_user = User.model_validate(create.model_dump() | {"hashed_password": ""})
    new_user.set_password(create.password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@app.get(
    "/users/me/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get Current User",
    description="Get the currently authenticated user",
)
async def read_current_user(
    current_user: Annotated[User, Depends(auth.get_current_user)],
) -> User:
    return current_user


@app.get(
    "/users/{user_id}/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get User by ID",
    description="Get a user by their ID",
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def read_user_by_id(
    user_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> User:
    if current_user.id == user_id:
        return current_user

    stmt = select(User).where(User.id == user_id)
    try:
        user = (await session.execute(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        ) from e
    return user[0] if isinstance(user, Row) else user


@app.get(
    "/users/c/{email}/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get User by Email",
    description="Get a user by their email",
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def read_user_by_email(
    email: str,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> User:
    if current_user.email == email:
        return current_user

    user = await auth.get_user_by_email(email, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user[0] if isinstance(user, Row) else user


@app.patch(
    "/users/me/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update Current User",
    description="Update the currently authenticated user",
)
async def update_current_user(
    update: UserUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> User:
    user = current_user

    for key, value in update.model_dump(exclude_unset=True).items():
        if key == "password":
            user.set_password(value)
        else:
            setattr(user, key, value)

    await session.commit()
    await session.refresh(user)
    return user


@app.patch(
    "/users/{user_id}/",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update User",
    description="Update an existing user",
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found"}},
)
async def update_user(
    user_id: int,
    update: UserUpdate,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> User:
    user = await read_user_by_id(user_id, current_user, session)

    for key, value in update.model_dump(exclude_unset=True).items():
        if key == "password":
            user.set_password(value)
        else:
            setattr(user, key, value)

    await session.commit()
    await session.refresh(user)
    return user


@app.delete(
    "/users/{user_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User",
    description="Delete an existing user",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Users cannot delete themselves"},
        status.HTTP_404_NOT_FOUND: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(auth.get_current_user)],
    session=Depends(get_async_session),
) -> None:
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users cannot delete themselves",
        )

    user = await read_user_by_id(user_id, current_user, session)
    await session.delete(user)
    await session.commit()
    return None
