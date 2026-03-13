import csv
import enum
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import TextIO, TypeVar

from sqlmodel import Session

from app.functions import file
from app.models.base import TableBase

T = TypeVar("T", bound="TableBase")


class Importer(ABC):
    _f: TextIO
    _model_class: type[TableBase]

    def __init__(self, f: TextIO, model_class: type[TableBase]) -> None:
        super().__init__()
        self._f = f
        self._model_class = model_class

    @abstractmethod
    def import_data(self) -> Iterator[TableBase]:
        raise NotImplementedError


class JSONImporter(Importer):
    def import_data(self) -> Iterator[TableBase]:
        import json

        data = json.load(self._f)
        for row in data:
            yield self._model_class.model_validate(
                self._model_class.load_from_dict(row)
            )


class NDJSONImporter(Importer):
    def import_data(self) -> Iterator[TableBase]:
        import json

        for line in self._f:
            row = json.loads(line)
            yield self._model_class.model_validate(
                self._model_class.load_from_dict(row)
            )


class CSVImporter(Importer):
    def import_data(self) -> Iterator[TableBase]:
        reader = csv.reader(self._f)
        for row in reader:
            yield self._model_class.model_validate(
                self._model_class.load_from_list(row)
            )


class TSVImporter(Importer):
    def import_data(self) -> Iterator[TableBase]:
        reader = csv.reader(self._f, delimiter="\t")
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


def import_models(
    session: Session,
    model_class: type[T],
    path: str | None,
    importer: Importer,
) -> None:
    f = file.open_input_file(path)
    importer = importer(f, model_class)
    for model in importer.import_data():
        session.add(model)
    session.commit()
    file.close(f)
