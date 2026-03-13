from abc import ABC

# from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models.base import CreateBase, ReadBase, TableBase, UpdateBase

_password_hash = PasswordHash.recommended()


def _get_password_hash(password: str) -> str:
    return _password_hash.hash(password)


class UserBase(SQLModel, ABC):
    email: EmailStr = Field(index=True, unique=True, max_length=255)
    display_name: str = Field(max_length=255)
    disabled: bool = Field(default=False)
    is_admin: bool = Field(default=False, sa_column_kwargs={"server_default": "0"})


class User(UserBase, TableBase, table=True):
    __tablename__ = "sc_user"
    __exclude__export__ = {"hashed_password"}
    __import_order__ = ["email", "display_name", "disabled", "is_admin", "password"]

    hashed_password: str

    @classmethod
    def load_from_list(cls, row: list) -> dict:
        row = super().load_from_list(row)
        row["hashed_password"] = _get_password_hash(row.pop("password"))
        return row

    @classmethod
    def load_from_dict(cls, row: dict) -> dict:
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


class UserUpdate(UserBase, UpdateBase):
    email: EmailStr | None = None
    display_name: str | None = None
    password: str | None = None
    is_admin: bool | None = None
