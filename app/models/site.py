from abc import ABC
from typing import TYPE_CHECKING, Annotated

from pydantic import StringConstraints
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import CreateBase, ReadBase, TableBase, UpdateBase

if TYPE_CHECKING:
    from app.models.token import Token

SiteName = Annotated[str, StringConstraints(max_length=255)]
FQDN = Annotated[
    str,
    StringConstraints(
        pattern=r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$",
        strip_whitespace=True,
        max_length=255,
    ),
]


class SiteBase(SQLModel, ABC):
    fqdn: str = Field(index=True, unique=True)
    name: SiteName


class Site(SiteBase, TableBase, table=True):
    __import_order__ = ["fqdn", "site"]

    tokens: list["Token"] = Relationship(back_populates="site")


class SiteCreate(SiteBase, CreateBase):
    pass


class SiteRead(SiteBase, ReadBase):
    pass


class SiteUpdate(UpdateBase):
    fqdn: str | None = None
    name: SiteName | None = None
