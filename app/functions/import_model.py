import csv
import enum
import io
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Generic, TypeVar, cast

from sqlmodel.ext.asyncio.session import AsyncSession

from app.functions import file
from app.models.base import TableBase

TModel = TypeVar("TModel", bound=TableBase)


class Importer(ABC, Generic[TModel]):
    _f: file.AioTextFile
    _model_class: type[TModel]

    def __init__(self, f: file.AioTextFile, model_class: type[TModel]) -> None:
        super().__init__()
        self._f = f
        self._model_class = model_class

    @abstractmethod
    def import_data(self) -> AsyncIterator[TModel]:
        raise NotImplementedError


class JSONImporter(Importer[TModel]):
    async def import_data(self) -> AsyncIterator[TModel]:
        import json

        data = json.loads(await self._f.read())
        for row in data:
            yield self._model_class.model_validate(
                self._model_class.load_from_dict(cast(dict[str, Any], row))
            )


class NDJSONImporter(Importer[TModel]):
    async def import_data(self) -> AsyncIterator[TModel]:
        import json

        while True:
            line = await self._f.readline()
            if not line:
                break
            row = json.loads(line)
            yield self._model_class.model_validate(
                self._model_class.load_from_dict(cast(dict[str, Any], row))
            )


class CSVImporter(Importer[TModel]):
    async def import_data(self) -> AsyncIterator[TModel]:
        content = await self._f.read()
        reader = csv.reader(io.StringIO(content))
        for row in reader:
            yield self._model_class.model_validate(
                self._model_class.load_from_list(row)
            )


class TSVImporter(Importer[TModel]):
    async def import_data(self) -> AsyncIterator[TModel]:
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


def resolve_importer(fmt: ImportFormat) -> type[Importer[Any]]:
    mapping: dict[ImportFormat, type[Importer[Any]]] = {
        ImportFormat.JSON: JSONImporter,
        ImportFormat.NDJSON: NDJSONImporter,
        ImportFormat.CSV: CSVImporter,
        ImportFormat.TSV: TSVImporter,
    }
    return mapping[fmt]


async def import_models(
    session: AsyncSession,
    model_class: type[TModel],
    path: str | None,
    fmt: ImportFormat,
) -> None:
    importer_cls = cast(type[Importer[TModel]], resolve_importer(fmt))
    f = await file.open_input_file(path)
    im = importer_cls(f, model_class)
    async for model in im.import_data():
        session.add(model)
    await session.commit()
    await file.close(f)
