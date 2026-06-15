import csv
import enum
import textwrap
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, Generic, Sequence, TypeVar, cast

from aiocsv import AsyncWriter
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.functions import file
from app.models.base import TableBase

TModel = TypeVar("TModel", bound=TableBase)


class Exporter(ABC, Generic[TModel]):
    _f: file.AioTextFile
    _model_class: type[TModel]

    def __init__(self, f: file.AioTextFile, model_class: type[TModel]) -> None:
        super().__init__()
        self._f = f
        self._model_class = model_class

    async def header(self) -> None:
        pass

    @abstractmethod
    async def export_data(self, chunk: Sequence[TModel]) -> None:
        raise NotImplementedError

    async def footer(self) -> None:
        pass


class JSONExporter(Exporter[TModel]):
    first: bool = True

    async def header(self) -> None:
        await self._f.write("[\n")
        self.first = True

    async def export_data(self, chunk: Sequence[TModel]) -> None:
        for row in chunk:
            if not self.first:
                await self._f.write(",\n")
            row_json = row.model_dump_json(
                exclude=self._model_class.get_exclude_export_fields(),
                ensure_ascii=True,
                indent=4,
            )
            await self._f.write(textwrap.indent(row_json, "    "))
            self.first = False

    async def footer(self) -> None:
        await self._f.write("\n]\n")


class NDJSONExporter(Exporter[TModel]):
    async def export_data(self, chunk: Sequence[TModel]) -> None:
        for row in chunk:
            await self._f.write(
                row.model_dump_json(
                    exclude=self._model_class.get_exclude_export_fields()
                )
                + "\n"
            )


class CSVExporter(Exporter[TModel]):
    def __init__(self, f: file.AioTextFile, model_class: type[TModel]) -> None:
        super().__init__(f, model_class)
        self._writer = AsyncWriter(f, quoting=csv.QUOTE_NONNUMERIC)

    async def header(self) -> None:
        await self._writer.writerow(self._model_class.dump_header())

    async def export_data(self, chunk: Sequence[TModel]) -> None:
        await self._writer.writerows([row.dump_list() for row in chunk])


class TSVExporter(Exporter[TModel]):
    def __init__(self, f: file.AioTextFile, model_class: type[TModel]) -> None:
        super().__init__(f, model_class)
        self._writer = AsyncWriter(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

    async def header(self) -> None:
        await self._writer.writerow(self._model_class.dump_header())

    async def export_data(self, chunk: Sequence[TModel]) -> None:
        await self._writer.writerows([row.dump_list() for row in chunk])


class ExportFormat(enum.Enum):
    JSON = "json"
    NDJSON = "ndjson"
    CSV = "csv"
    TSV = "tsv"


def resolve_exporter(fmt: ExportFormat) -> type[Exporter[Any]]:
    mapping: dict[ExportFormat, type[Exporter[Any]]] = {
        ExportFormat.JSON: JSONExporter,
        ExportFormat.NDJSON: NDJSONExporter,
        ExportFormat.CSV: CSVExporter,
        ExportFormat.TSV: TSVExporter,
    }
    return mapping[fmt]


async def _iter_chunks(
    session: AsyncSession,
    stmt: Select[TModel] | SelectOfScalar[TModel],
    model_class: type[TModel],
    chunk_size: int,
) -> AsyncIterator[Sequence[TModel]]:
    last_id = 0
    while True:
        s = (
            stmt.where(model_class.id > last_id)
            .order_by(col(model_class.id))
            .limit(chunk_size)
        )
        chunk = (await session.exec(s)).all()
        if not chunk:
            break
        yield chunk
        last_id = chunk[-1].id


async def export_models(
    session: AsyncSession,
    model_class: type[TModel],
    path: str | None,
    fmt: ExportFormat,
    chunk_size: int = 1000,
    stmt: Select[TModel] | SelectOfScalar[TModel] | None = None,
) -> None:
    exporter_cls = cast(type[Exporter[TModel]], resolve_exporter(fmt))
    f = await file.open_output_file(path)
    ex = exporter_cls(f, model_class)
    await ex.header()
    async for chunk in _iter_chunks(
        session,
        select(model_class) if stmt is None else stmt,
        model_class,
        chunk_size,
    ):
        await ex.export_data(chunk)
    await ex.footer()
    await file.close(f)
