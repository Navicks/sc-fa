from fastapi import Depends, FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.api import auth as api_auth
from app.api import site, token, user, user_site
from app.deps import auth
from app.models.user import User

app = FastAPI(
    title="fa API",
    version="0.1.2",
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


app.include_router(api_auth.router)
app.include_router(site.router)
app.include_router(token.router)
app.include_router(user.router)
app.include_router(user_site.router)
