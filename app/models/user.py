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


class User(UserBase, TableBase, table=True):
    hashed_password: str

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
