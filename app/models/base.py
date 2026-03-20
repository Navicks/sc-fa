from abc import ABC
from typing import Any, TypeVar

from sqlmodel import Field, SQLModel

TTable = TypeVar("TTable", bound="TableBase")


class TableBase(SQLModel, ABC):
    __exclude__export__: set = set()
    __import_order__: list[str] = []

    id: int = Field(default=None, primary_key=True)

    @classmethod
    def dump_header(cls) -> list[str]:
        return [
            name
            for name in cls.model_fields.keys()
            if name not in cls.__exclude__export__
        ]

    def dump_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python", exclude=self.__exclude__export__)

    def dump_list(self) -> list[Any]:
        return [getattr(self, name) for name in self.dump_header()]

    @classmethod
    def load_from_list(cls: type[TTable], row: list[str]) -> dict[str, Any]:
        return dict(zip(cls.__import_order__, row))

    @classmethod
    def load_from_dict(cls: type[TTable], row: dict[str, Any]) -> dict[str, Any]:
        return row


class CreateBase(SQLModel, ABC):
    pass


class ReadBase(SQLModel, ABC):
    id: int


class UpdateBase(SQLModel, ABC):
    pass
