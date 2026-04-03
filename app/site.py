import datetime
import logging
from importlib.metadata import version
from typing import Annotated
from urllib import parse

from fastapi import BackgroundTasks, Depends, FastAPI, Header, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.exc import NoResultFound
from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette import status

from app.cache import token as cache_token
from app.database import get_async_session
from app.database.redis import create_redis_client
from app.models.site import Site
from app.models.token import Token, TokenStatus
from app.settings import app_settings

app = FastAPI(
    title="fa Site",
    version=version("sc_fa"),
    description="fa Site endpoints",
    docs_url="/int/docs" if app_settings.debug else None,
    redoc_url="/int/redoc" if app_settings.debug else None,
)

logger = logging.getLogger("uvicorn.app.site")


successful_responses = {
    s.value: {"description": f"Redirect as {s.name.replace('_', ' ').title()}"}
    for s in TokenStatus
}


def get_hostname(
    request: Request,
    debug_host: str | None = Header(
        None,
        alias="SC-Host",
    ),
) -> str | None:
    """Extract the hostname from the request URL."""
    if app_settings.debug and debug_host:
        return debug_host
    return request.url.hostname


def build_redirect_url(request: Request, base_url: str, have_query: bool) -> str:
    if len(request.query_params) == 0:
        return base_url
    separator = "&" if have_query else "?"
    return f"{base_url}{separator}{request.query_params}"


@app.get(
    "/{token}",
    status_code=status.HTTP_302_FOUND,
    summary="Redirect Token",
    description="Redirect based on the provided token",
    response_class=RedirectResponse,
    responses={
        **successful_responses,
        status.HTTP_404_NOT_FOUND: {"description": "Token not found"},
    },
)
async def token(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    host: Annotated[str | None, Depends(get_hostname)],
) -> RedirectResponse:
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )

    cache = await cache_token.get(redis, host, token)
    if cache:
        url = build_redirect_url(request, cache[1], have_query=cache[2])
        return RedirectResponse(
            status_code=cache[0],
            url=url,
        )

    now = datetime.datetime.now(datetime.timezone.utc)
    stmt = (
        select(Token)
        .join(Site)
        .where(
            Token.token == token,
            Site.fqdn == host,
            or_(Token.valid_from.is_(None), Token.valid_from <= now),
            or_(Token.valid_to.is_(None), now < Token.valid_to),
        )
    )
    try:
        site_token = (await session.exec(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        ) from e

    background_tasks.add_task(cache_token.set, redis, site_token, now, site=host)
    have_query: bool = parse.urlparse(str(site_token.redirect_uri)).query != ""
    url = build_redirect_url(
        request, str(site_token.redirect_uri), have_query=have_query
    )
    return RedirectResponse(
        status_code=site_token.status_code,
        url=url,
    )
