import enum
from abc import ABC
from typing import ClassVar

from sqlmodel import Field, SQLModel

from app.models.base import CreateBase, UpdateBase


class SitePermission(enum.IntEnum):
    READ = 1
    WRITE = 2
    ADMIN = 3


class UserSiteBase(SQLModel, ABC):
    site_id: int = Field(foreign_key="site.id", primary_key=True)
    permission: SitePermission = Field(default=SitePermission.READ)


class UserSiteUserBase(SQLModel, ABC):
    user_id: int = Field(foreign_key="sc_user.id", primary_key=True)


class UserSite(UserSiteBase, UserSiteUserBase, table=True):
    # This table does not have id column,
    # so we use the combination of user_id and site_id as the primary key
    __tablename__: ClassVar[str] = "user_site"  # type: ignore[assignment]
    pass


class UserSiteCreate(UserSiteBase, UserSiteUserBase, CreateBase):
    pass


class UserSiteCreateWithoutUser(UserSiteBase, CreateBase):
    pass


class UserSiteRead(UserSiteBase, UserSiteUserBase):
    pass


class UserSiteUpdate(UpdateBase):
    permission: SitePermission | None = None
