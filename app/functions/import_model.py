import csv
import enum
import io
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from sqlmodel.ext.asyncio.session import AsyncSession

from app.functions import file
from app.models.base import TableBase

T = TypeVar("T", bound="TableBase")


class Importer(ABC):
    _f: Any
    _model_class: type[TableBase]

    def __init__(self, f: Any, model_class: type[TableBase]) -> None:
        super().__init__()
        self._f = f
        self._model_class = model_class

    @abstractmethod
    async def import_data(self) -> AsyncIterator[TableBase]:
        raise NotImplementedError


class JSONImporter(Importer):
    async def import_data(self) -> AsyncIterator[TableBase]:
        import json

        data = json.loads(await self._f.read())
        for row in data:
            yield self._model_class.model_validate(
                self._model_class.load_from_dict(row)
            )


class NDJSONImporter(Importer):
    async def import_data(self) -> AsyncIterator[TableBase]:
        import json

        while True:
            line = await self._f.readline()
            if not line:
                break
            row = json.loads(line)
            yield self._model_class.model_validate(
                self._model_class.load_from_dict(row)
            )


class CSVImporter(Importer):
    async def import_data(self) -> AsyncIterator[TableBase]:
        content = await self._f.read()
        reader = csv.reader(io.StringIO(content))
        for row in reader:
            yield self._model_class.model_validate(
                self._model_class.load_from_list(row)
            )


class TSVImporter(Importer):
    async def import_data(self) -> AsyncIterator[TableBase]:
        content = await self._f.read()
        reader = csv.reader(io.StringIO(content), delimiter="\t")
        for row in reader:
            yield self._model_class.model_validate(
                self._model_class.load_from_list(row)
            )


class ImportFormat(enum.Enum):
    JSON = "json"
    NDJSON = "ndjson"
    CSV = "csv"
    TSV = "tsv"

    @property
    def importer_class(self) -> type[Importer]:
        return {
            self.JSON: JSONImporter,
            self.NDJSON: NDJSONImporter,
            self.CSV: CSVImporter,
            self.TSV: TSVImporter,
        }[self]


async def import_models(
    session: AsyncSession,
    model_class: type[T],
    path: str | None,
    importer: type[Importer],
) -> None:
    f = await file.open_input_file(path)
    importer = importer(f, model_class)
    async for model in importer.import_data():
        session.add(model)
    await session.commit()
    await file.close(f)
