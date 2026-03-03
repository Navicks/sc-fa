import datetime
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import NoResultFound
from sqlmodel import or_, select
from starlette import status

from app.cache import token as cache_token
from app.database import get_async_session
from app.database.redis import create_redis_client
from app.models.site import Site
from app.models.token import Token

app = FastAPI()


@app.get(
    "/{token}",
    status_code=status.HTTP_302_FOUND,
    summary="Redirect Token",
    description="Redirect based on the provided token",
    response_class=RedirectResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Token not found"}},
)
async def token(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    redis: Annotated[AsyncRedis, Depends(create_redis_client)],
    session=Depends(get_async_session),
) -> RedirectResponse:
    host = request.url.hostname
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )

    cache = await cache_token.get(redis, host, token)
    if cache:
        return RedirectResponse(
            status_code=cache[0],
            url=cache[1],
        )

    now = datetime.datetime.now(datetime.timezone.utc)
    stmt = (
        select(Token)
        .join(Token.site)
        .where(
            Token.token == token,
            Site.fqdn == host,
            or_(Token.valid_from.is_(None), Token.valid_from <= now),
            or_(Token.valid_to.is_(None), now < Token.valid_to),
        )
    )
    try:
        site_token = (await session.execute(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        ) from e

    site_token = site_token[0] if isinstance(site_token, Row) else site_token
    background_tasks.add_task(cache_token.set, redis, site_token, now, site=host)
    return RedirectResponse(
        status_code=site_token.status_code,
        url=site_token.redirect_uri,
    )
