from pathlib import Path
from typing import Any

import openpyxl

from freight_check.contracts import ExtractedField, RawDocument
from freight_check.parsers.base import BaseParser


class XLSXParser(BaseParser):
    """Парсер для таблиц Excel (.xlsx)."""

    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)

        pages: list[list[ExtractedField]] = []

        try:
            workbook = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
            try:
                for sheet in workbook.worksheets:
                    page_data = self._process_sheet(sheet)
                    pages.append(page_data)
            finally:
                workbook.close()
        except Exception as e:
            raise ValueError(f"Ошибка чтения XLSX: {e}") from e

        return RawDocument(
            file_path=file_path,
            pages=pages,
            document_type="xlsx",
            metadata={"sheets_count": len(pages)},
        )

    def _process_sheet(self, sheet: Any) -> list[ExtractedField]:
        cells_data: list[ExtractedField] = []

        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    extracted = ExtractedField(
                        raw_value=str(cell.value),
                        normalized_value=str(cell.value).strip(),
                        confidence=1.0,
                        source_box=(cell.row, cell.column, 1, 1),
                    )
                    cells_data.append(extracted)

        return cells_data
