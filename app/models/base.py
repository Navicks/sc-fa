from abc import ABC
from typing import Any, TypeVar

from sqlmodel import Field, SQLModel

TTable = TypeVar("TTable", bound="TableBase")


class TableBase(SQLModel, ABC):
    __exclude_export__: set[str] = set()
    __exclude_import__: set[str] = set()
    __ignore_import__: set[str] = set()
    __import_default_order__: list[str] = []

    id: int = Field(default=None, primary_key=True)

    @classmethod
    def dump_header(cls) -> list[str]:
        return [
            name
            for name in cls.model_fields.keys()
            if name not in cls.__exclude_export__
        ]

    @classmethod
    def get_exclude_export_fields(cls) -> set[str]:
        return cls.__exclude_export__

    @classmethod
    def get_importable_fields(cls) -> set[str]:
        return {
            name for name in cls.model_fields.keys()
            if name not in cls.__exclude_import__
         } | cls.__ignore_import__

    @classmethod
    def get_default_import_fields(cls) -> list[str]:
        return cls.__import_default_order__

    def dump_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="python", exclude=self.__exclude_export__)

    def dump_list(self) -> list[Any]:
        return [getattr(self, name) for name in self.dump_header()]

    @classmethod
    def hook_import(cls: type[TTable], row: dict[str, Any]) -> dict[str, Any]:
        return row


class CreateBase(SQLModel, ABC):
    pass


class ReadBase(SQLModel, ABC):
    id: int


class UpdateBase(SQLModel, ABC):
    pass
