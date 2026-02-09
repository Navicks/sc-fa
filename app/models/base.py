from abc import ABC

from sqlmodel import Field, SQLModel


class TableBase(SQLModel, ABC):
    id: int = Field(default=None, primary_key=True)


class CreateBase(SQLModel, ABC):
    pass


class ReadBase(SQLModel, ABC):
    id: int


class UpdateBase(SQLModel, ABC):
    pass
    pass
