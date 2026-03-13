from abc import ABC

from sqlmodel import Field, SQLModel


class TableBase(SQLModel, ABC):
    __exclude__export__: set = {}
    __import_order__: list[str] = []

    id: int = Field(default=None, primary_key=True)

    @classmethod
    def dump_header(cls) -> list[str]:
        return [
            name
            for name in cls.model_fields.keys()
            if name not in cls.__exclude__export__
        ]

    def dump_dict(self) -> dict:
        return self.model_dump(mode="python", exclude=self.__exclude__export__)

    def dump_list(self) -> list:
        return [getattr(self, name) for name in self.dump_header()]

    @classmethod
    def load_from_list(cls, row: list) -> dict:
        return dict(zip(cls.__import_order__, row))

    @classmethod
    def load_from_dict(cls, row: dict) -> dict:
        return row


class CreateBase(SQLModel, ABC):
    pass


class ReadBase(SQLModel, ABC):
    id: int


class UpdateBase(SQLModel, ABC):
    pass
