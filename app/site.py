from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import HTTPException
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import NoResultFound
from sqlmodel import select

from app.database import get_async_session
from app.database.redis import create_redis_client
from app.models.site import Site
from app.models.token import Token

app = FastAPI()


@app.get(
    "/{token}",
    status_code=302,
    summary="Redirect Token",
    description="Redirect based on the provided token",
    responses={404: {"description": "Token not found"}},
)
async def token(
    token: str,
    request: Request,
    host: str | None = Header(default=None),
    session=Depends(get_async_session),
    redis: AsyncRedis = Depends(create_redis_client),
):
    host = request.url.hostname
    if host is None:
        raise HTTPException(status_code=404, detail="Site not found")

    cache = await redis.get(f"token:{host}:{token}")
    if cache:
        status_code, redirect_uri = cache.split("|", 1)
        raise HTTPException(
            status_code=int(status_code),
            headers={"Location": redirect_uri},
        )

    stmt = select(Token).join(Site).where(Token.token == token, Site.fqdn == host)
    try:
        site_token = (await session.execute(stmt)).one()
    except NoResultFound as e:
        raise HTTPException(status_code=404, detail="Token not found") from e

    site_token = site_token[0] if isinstance(site_token, Row) else site_token
    await redis.set(
        f"token:{host}:{token}",
        f"{site_token.status_code}|{site_token.redirect_uri}",
        ex=300,
    )
    raise HTTPException(
        status_code=site_token.status_code,
        headers={"Location": site_token.redirect_uri},
    )
