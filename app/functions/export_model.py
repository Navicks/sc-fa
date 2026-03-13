import csv
import enum
import textwrap
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import TextIO, TypeVar

from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.functions import file
from app.models.base import TableBase

T = TypeVar("T", bound="TableBase")


class Exporter(ABC):
    _f: TextIO
    _model_class: type[TableBase]

    def __init__(self, f: TextIO, model_class: type[TableBase]) -> None:
        super().__init__()
        self._f = f
        self._model_class = model_class

    def header(self) -> None:
        pass

    @abstractmethod
    def export_data(self, chunk: list[TableBase]) -> None:
        raise NotImplementedError

    def footer(self) -> None:
        pass


class JSONExporter(Exporter):
    first: bool = True

    def header(self) -> None:
        self._f.write("[\n")
        self.first = True

    def export_data(self, chunk: list[TableBase]) -> None:
        for row in chunk:
            if not self.first:
                self._f.write(",\n")
            row = row.model_dump_json(ensure_ascii=True, indent=4)
            self._f.write(textwrap.indent(row, "    "))
            self.first = False

    def footer(self) -> None:
        self._f.write("\n]\n")


class NDJSONExporter(Exporter):
    def export_data(self, chunk: list[TableBase]) -> None:
        for row in chunk:
            self._f.write(row.model_dump_json() + "\n")


class CSVExporter(Exporter):
    def __init__(self, f: TextIO, model_class: type[TableBase]):
        super().__init__(f, model_class)
        self.writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)

    def export_data(self, chunk: list[TableBase]) -> None:
        self.writer.writerow(self._model_class.dump_header())
        self.writer.writerows([row.dump_list() for row in chunk])


class TSVExporter(Exporter):
    def __init__(self, f: TextIO, model_class: type[TableBase]):
        super().__init__(f, model_class)
        self.writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

    def export_data(self, chunk: list[TableBase]) -> None:
        self.writer.writerow(self._model_class.dump_header())
        self.writer.writerows([row.dump_list() for row in chunk])


class ExportFormat(enum.Enum):
    JSON = "json"
    NDJSON = "ndjson"
    CSV = "csv"
    TSV = "tsv"

    @property
    def exporter_class(self) -> type[Exporter]:
        return {
            ExportFormat.JSON: JSONExporter,
            ExportFormat.NDJSON: NDJSONExporter,
            ExportFormat.CSV: CSVExporter,
            ExportFormat.TSV: TSVExporter,
        }[self]


def _iter_chunks(
    session: Session,
    stmt: SelectOfScalar[T],
    model_class: type[T],
    chunk_size: int,
) -> Iterator[list[T]]:
    last_id = 0
    while True:
        s = (
            stmt.where(model_class.id > last_id)
            .order_by(model_class.id)
            .limit(chunk_size)
        )
        chunk = session.exec(s).all()
        if not chunk:
            break
        yield chunk
        last_id = chunk[-1].id


def export_models(
    session: Session,
    model_class: type[TableBase],
    path: str,
    exporter: type[Exporter],
    chunk_size: int = 1000,
):
    f = file.open_output_file(path)
    ex = exporter(f, model_class)
    ex.header()
    for chunk in _iter_chunks(session, select(model_class), model_class, chunk_size):
        ex.export_data(chunk)
    ex.footer()
    file.close(f)
