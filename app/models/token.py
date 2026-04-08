from abc import ABC
from datetime import datetime, timezone
from enum import IntEnum
from typing import Annotated

import starlette.status as status
from pydantic import HttpUrl, StringConstraints, field_validator, model_validator
from sqlalchemy import DateTime, TypeDecorator, UniqueConstraint
from sqlmodel import VARCHAR, Field, Relationship, SQLModel

from app.models.base import CreateBase, ReadBase, TableBase, UpdateBase
from app.models.site import Site

TokenType = Annotated[
    str,
    StringConstraints(
        pattern=r"^[0-9A-Za-z_-]{1,255}$", strip_whitespace=True, max_length=255
    ),
]


def _normalize_to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class UtcDateTime(TypeDecorator):
    """SQLAlchemy type that ensures datetimes are always UTC-aware."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        return _normalize_to_utc(value)


class HttpUrlType(TypeDecorator):
    """SQLAlchemy type that stores HttpUrl as string."""

    impl = VARCHAR(2048)
    cache_ok = True

    def process_bind_param(self, value: HttpUrl | None, dialect) -> str | None:
        return str(value) if value is not None else None

    def process_result_value(self, value: str | None, dialect) -> HttpUrl | None:
        return HttpUrl(value) if value is not None else None


class TokenStatus(IntEnum):
    MOVED_PERMANENTLY = status.HTTP_301_MOVED_PERMANENTLY
    FOUND = status.HTTP_302_FOUND
    SEE_OTHER = status.HTTP_303_SEE_OTHER
    PERMANENT_REDIRECT = status.HTTP_308_PERMANENT_REDIRECT


class TokenBase(SQLModel, ABC):
    redirect_uri: HttpUrl | None = Field(
        default=None, max_length=2048, sa_type=HttpUrlType
    )
    subject: str | None = Field(default=None, max_length=255)
    status_code: TokenStatus = Field(default=TokenStatus.FOUND)
    valid_from: datetime | None = Field(default=None, sa_type=UtcDateTime)
    valid_to: datetime | None = Field(default=None, sa_type=UtcDateTime)

    __table_args__ = (UniqueConstraint("site_id", "token", name="uix_site_id_token"),)

    @field_validator("valid_from", "valid_to", mode="after")
    @classmethod
    def normalize_to_utc(cls, v: datetime | None) -> datetime | None:
        return _normalize_to_utc(v)

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_from and self.valid_to and self.valid_from >= self.valid_to:
            raise ValueError("valid_from must be before valid_to")
        return self


class Token(TokenBase, TableBase, table=True):
    token: TokenType = Field(index=True)

    site_id: int = Field(index=True, foreign_key="site.id")
    site: Site | None = Relationship(back_populates="tokens")


class TokenCreate(TokenBase, CreateBase):
    token: TokenType


class TokenRead(TokenBase, ReadBase):
    site_id: int
    token: TokenType


class TokenUpdate(UpdateBase):
    redirect_uri: HttpUrl | None = None
    subject: str | None = None
    status_code: TokenStatus | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    token: TokenType | None = None

    @field_validator("valid_from", "valid_to", mode="after")
    @classmethod
    def normalize_to_utc(cls, v: datetime | None) -> datetime | None:
        return _normalize_to_utc(v)

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_from and self.valid_to and self.valid_from >= self.valid_to:
            raise ValueError("valid_from must be before valid_to")
        return self
