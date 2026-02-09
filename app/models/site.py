from abc import ABC

from sqlmodel import Field, SQLModel

from app.models.base import CreateBase, ReadBase, TableBase, UpdateBase


class SiteBase(SQLModel, ABC):
    fqdn: str = Field(index=True, unique=True)
    name: str = Field(max_length=255)


class Site(SiteBase, TableBase, table=True):
    pass


class SiteCreate(SiteBase, CreateBase):
    pass


class SiteRead(SiteBase, ReadBase):
    pass


class SiteUpdate(SiteBase, UpdateBase):
    fqdn: str | None = None
    name: str | None = None
