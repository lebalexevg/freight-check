import csv
from pathlib import Path

from freight_check.contracts import ExtractedField, RawDocument
from freight_check.parsers.base import BaseParser


class CSVParser(BaseParser):
    """Парсер для файлов CSV."""

    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)
        fields: list[ExtractedField] = []

        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                sample = f.read(2048)
                f.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                except csv.Error:
                    dialect = csv.excel

                reader = csv.reader(f, dialect)

                for row_idx, row in enumerate(reader, start=1):
                    for col_idx, cell_value in enumerate(row, start=1):
                        if cell_value and cell_value.strip():
                            fields.append(
                                ExtractedField(
                                    raw_value=cell_value,
                                    normalized_value=cell_value.strip(),
                                    confidence=1.0,
                                    source_box=(row_idx, col_idx, 1, 1),
                                )
                            )
        except UnicodeDecodeError:
            try:
                with open(file_path, encoding="cp1251", newline="") as f:
                    sample = f.read(2048)
                    f.seek(0)

                    try:
                        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                    except csv.Error:
                        dialect = csv.excel

                    reader = csv.reader(f, dialect)

                    for row_idx, row in enumerate(reader, start=1):
                        for col_idx, cell_value in enumerate(row, start=1):
                            if cell_value and cell_value.strip():
                                fields.append(
                                    ExtractedField(
                                        raw_value=cell_value,
                                        normalized_value=cell_value.strip(),
                                        confidence=1.0,
                                        source_box=(row_idx, col_idx, 1, 1),
                                    )
                                )
            except Exception as e:
                raise ValueError("Ошибка чтения CSV (не удалось определить кодировку)") from e
        except Exception as e:
            raise ValueError("Ошибка чтения CSV") from e

        return RawDocument(
            file_path=file_path,
            pages=[fields],
            document_type="csv",
            metadata={},
        )
