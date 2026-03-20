from abc import ABC
from typing import Annotated, Any, ClassVar

# from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models.base import CreateBase, ReadBase, TableBase, UpdateBase

_password_hash = PasswordHash.recommended()


def _get_password_hash(password: str) -> str:
    return _password_hash.hash(password)


UserEmail = Annotated[EmailStr, Field(max_length=255)]
UserDisplayName = Annotated[str, Field(max_length=255)]


class UserBase(SQLModel, ABC):
    email: UserEmail = Field(index=True, unique=True)
    display_name: UserDisplayName
    disabled: bool = Field(default=False)
    is_admin: bool = Field(default=False, sa_column_kwargs={"server_default": "0"})


class User(UserBase, TableBase, table=True):
    __tablename__: ClassVar[str] = "sc_user"  # type: ignore[assignment]
    __exclude__export__ = {"hashed_password"}
    __import_order__ = ["email", "display_name", "disabled", "is_admin", "password"]

    hashed_password: str

    @classmethod
    def load_from_list(cls, row: list[str]) -> dict[str, Any]:
        r = super().load_from_list(row)
        r["hashed_password"] = _get_password_hash(r.pop("password"))
        return r

    @classmethod
    def load_from_dict(cls, row: dict[str, Any]) -> dict[str, Any]:
        row["hashed_password"] = _get_password_hash(row.pop("password"))
        return row

    def set_password(self, password: str | None) -> None:
        if password is not None:
            self.hashed_password = _get_password_hash(password)

    def verify_password(self, password: str) -> bool:
        return _password_hash.verify(password, self.hashed_password)


class UserCreate(UserBase, CreateBase):
    password: str


class UserRead(UserBase, ReadBase):
    pass


class UserUpdate(UpdateBase):
    email: UserEmail | None = None
    display_name: UserDisplayName | None = None
    password: str | None = None
    is_admin: bool | None = None
