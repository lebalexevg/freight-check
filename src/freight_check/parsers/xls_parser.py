from pathlib import Path
from typing import Any

import xlrd
from xlrd.biffh import XLRDError

from freight_check.contracts import ExtractedField, RawDocument
from freight_check.parsers.base import BaseParser


class XLSParser(BaseParser):
    """Парсер для устаревших таблиц Excel (.xls)."""

    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)
        pages: list[list[ExtractedField]] = []

        try:
            workbook = xlrd.open_workbook(str(file_path), on_demand=True)
            for sheet in workbook.sheets():
                pages.append(self._process_sheet(sheet))
            workbook.release_resources()
        except XLRDError as e:
            raise ValueError("Ошибка парсинга XLS (поврежденный файл)") from e
        except Exception as e:
            raise ValueError("Ошибка чтения XLS") from e

        return RawDocument(
            file_path=file_path,
            pages=pages,
            document_type="xls",
            metadata={"sheets_count": len(pages)},
        )

    def _process_sheet(self, sheet: Any) -> list[ExtractedField]:
        fields: list[ExtractedField] = []

        for row_idx in range(sheet.nrows):
            for col_idx in range(sheet.ncols):
                cell = sheet.cell(row_idx, col_idx)

                if cell.ctype != xlrd.XL_CELL_EMPTY and cell.value is not None:
                    val = cell.value
                    if isinstance(val, float) and val.is_integer():
                        str_value = str(int(val))
                    else:
                        str_value = str(val)

                    fields.append(
                        ExtractedField(
                            raw_value=str_value,
                            normalized_value=str_value.strip(),
                            confidence=1.0,
                            source_box=(row_idx + 1, col_idx + 1, 1, 1),
                        )
                    )
        return fields
