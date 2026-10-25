from pathlib import Path
import xlrd

from freight_check.contracts import ExtractedField
from freight_check.parsers.base import BaseParser
from freight_check.parsers.models import RawDocument


class XLSParser(BaseParser):
    """Парсер для устаревших таблиц Excel (.xls)."""

    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)

        pages: list[list[ExtractedField]] = []

        try:
            workbook = xlrd.open_workbook(file_path, on_demand=True)

            for sheet in workbook.sheets():
                page_fields = self._process_sheet(sheet)
                pages.append(page_fields)

            workbook.release_resources()

        except xlrd.XLRDError as e:
            raise ValueError(f"Ошибка парсинга XLS (поврежденный файл): {str(e)}")
        except Exception as e:
            raise ValueError(f"Ошибка чтения XLS: {str(e)}")

        return RawDocument(
            file_path=file_path,
            pages=pages,
            document_type="xls",
            metadata={"sheets_count": len(pages)}
        )

    def _process_sheet(self, sheet: xlrd.sheet.Sheet) -> list[ExtractedField]:
        fields: list[ExtractedField] = []

        for row_idx in range(sheet.nrows):
            for col_idx in range(sheet.ncols):
                cell = sheet.cell(row_idx, col_idx)

                if cell.ctype != xlrd.XL_CELL_EMPTY and cell.value is not None:
                    str_value = str(cell.value)

                    fields.append(ExtractedField(
                        raw_value=str_value,
                        normalized_value=str_value.strip(),
                        confidence=1.0,
                        # xlrd использует 0-based индексы, делаем 1-based для унификации
                        source_box=(row_idx + 1, col_idx + 1, 1, 1)
                    ))

        return fields