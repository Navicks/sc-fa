import csv
import enum
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Generic, TypeVar, cast

from aiocsv import AsyncDictReader
from sqlmodel.ext.asyncio.session import AsyncSession

from app.functions import file
from app.models.base import TableBase

TModel = TypeVar("TModel", bound=TableBase)


class ImportError(Exception):
    pass


class Importer(ABC, Generic[TModel]):
    _f: file.AioTextFile
    _model_class: type[TModel]
    _static_fields: dict[str, Any] | None

    def __init__(
        self,
        f: file.AioTextFile,
        model_class: type[TModel],
        static_fields: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self._f = f
        self._model_class = model_class
        self._static_fields = static_fields

    def _load_model(self, row: dict[str, Any]) -> TModel:
        row = self._model_class.hook_import(row) | (self._static_fields or {})
        return self._model_class.model_validate(row)

    def _validate_header(self, header: list[str]) -> None:
        unacceptable: set[str] = set(header) - self._model_class.get_importable_fields()
        if len(unacceptable) > 0:
            raise ImportError(f"Invalid field name: {unacceptable}")

    @abstractmethod
    def import_data(self) -> AsyncIterator[TModel]:
        raise NotImplementedError


class JSONImporter(Importer[TModel]):
    async def import_data(self) -> AsyncIterator[TModel]:
        import json

        data = json.loads(await self._f.read())
        for row in data:
            yield super()._load_model(row)


class NDJSONImporter(Importer[TModel]):
    async def import_data(self) -> AsyncIterator[TModel]:
        import json

        while True:
            line = await self._f.readline()
            if not line:
                break
            row = json.loads(line)
            yield super()._load_model(row)


class CSVImporterBase(Importer[TModel], ABC):
    _reader: AsyncDictReader

    async def import_data(self) -> AsyncIterator[TModel]:
        async for row in self._reader:
            row = {k: None if v == "" else v for k, v in row}
            yield super()._load_model(row)


class CSVImporter(CSVImporterBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reader = AsyncDictReader(
            self._f,
            quoting=csv.QUOTE_NONNUMERIC,
            skipinitialspace=True,
        )
        super()._validate_header(self._reader.fieldnames or [])


class CSVWithoutHeaderImporter(CSVImporterBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reader = AsyncDictReader(
            self._f,
            skipinitialspace=True,
            fieldnames=self._model_class.get_default_import_fields()
        )


class TSVImporter(Importer[TModel]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reader = AsyncDictReader(
            self._f,
            delimiter="\t",
            skipinitialspace=True
        )
        super()._validate_header(self._reader.fieldnames or [])


class ImportFormat(enum.Enum):
    JSON = "json"
    NDJSON = "ndjson"
    CSV = "csv"
    CSVWOH = "csv-woh"
    TSV = "tsv"


def resolve_importer(fmt: ImportFormat) -> type[Importer[Any]]:
    mapping: dict[ImportFormat, type[Importer[Any]]] = {
        ImportFormat.JSON: JSONImporter,
        ImportFormat.NDJSON: NDJSONImporter,
        ImportFormat.CSV: CSVImporter,
        ImportFormat.CSVWOH: CSVWithoutHeaderImporter,
        ImportFormat.TSV: TSVImporter,
    }
    return mapping[fmt]


async def import_models(
    session: AsyncSession,
    model_class: type[TModel],
    path: str | None,
    fmt: ImportFormat,
    static_fields: dict[str, Any] | None = None,
) -> None:
    importer_cls = cast(type[Importer[TModel]], resolve_importer(fmt))
    f = await file.open_input_file(path)
    im = importer_cls(f, model_class, static_fields)
    async for model in im.import_data():
        session.add(model)
    await session.commit()
    await file.close(f)
