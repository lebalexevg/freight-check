from pathlib import Path
import openpyxl

from freight_check.contracts import DocumentPackage, ExtractedField
from freight_check.parsers.base import BaseParser


class XLSXParser(BaseParser):
    """Парсер для таблиц Excel (.xlsx)."""

    def parse(self, file_path: Path) -> DocumentPackage:
        self._validate_file(file_path)

        package = DocumentPackage(
            document_role="unknown",
            file_path=str(file_path)
        )

        try:
            workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)

            raw_rows = []
            for sheet in workbook.worksheets:
                raw_rows.extend(self._process_sheet(sheet))

            workbook.close()

            # Пока что во временное поле для последующей семантической обработки
            package._raw_rows = raw_rows

        except Exception as e:
            package.parsing_errors.append(f"Ошибка чтения XLSX: {str(e)}")

        return package

    def _process_sheet(self, sheet) -> list[list[ExtractedField]]:
        """Проходит по ячейкам листа и извлекает текст с координатами."""
        rows_data = []

        for row in sheet.iter_rows():
            row_data = []
            for cell in row:
                if cell.value is not None:
                    extracted = ExtractedField(
                        raw_value=str(cell.value),
                        normalized_value=str(cell.value).strip(),
                        confidence=1.0,
                        source_box=(cell.row, cell.column, 1, 1)
                    )
                    row_data.append(extracted)
                else:
                    row_data.append(None)
            rows_data.append(row_data)

        return rows_data