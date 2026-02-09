from abc import ABC
from datetime import datetime
from enum import IntEnum

import starlette.status as status
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import CreateBase, ReadBase, TableBase, UpdateBase


class TokenStatus(IntEnum):
    MOVED_PERMANENTLY = status.HTTP_301_MOVED_PERMANENTLY
    FOUND = status.HTTP_302_FOUND
    SEE_OTHER = status.HTTP_303_SEE_OTHER
    PERMANENT_REDIRECT = status.HTTP_308_PERMANENT_REDIRECT


class TokenBase(SQLModel, ABC):
    redirect_uri: str | None = Field(default=None, max_length=2048)
    subject: str | None = Field(default=None, max_length=255)
    status_code: TokenStatus = Field(default=TokenStatus.FOUND)
    valid_from: datetime | None = Field(default=None)
    valid_to: datetime | None = Field(default=None)

    __table_args__ = (UniqueConstraint("site_id", "token", name="uix_site_id_token"),)


class Token(TokenBase, TableBase, table=True):
    site_id: int = Field(index=True, foreign_key="site.id")
    token: str = Field(index=True, max_length=255)
    pass


class TokenCreate(TokenBase, CreateBase):
    token: str


class TokenRead(TokenBase, ReadBase):
    site_id: int
    token: str


class TokenUpdate(TokenBase, UpdateBase):
    redirect_uri: str | None = None
    subject: str | None = None
    status_code: TokenStatus | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
