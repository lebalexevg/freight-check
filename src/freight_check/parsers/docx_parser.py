from pathlib import Path
from docx import Document

from freight_check.contracts import ExtractedField
from freight_check.parsers.base import BaseParser
from freight_check.parsers.models import RawDocument


class DOCXParser(BaseParser):
    """Парсер для документов Word (.docx)."""

    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)

        fields: list[ExtractedField] = []

        try:
            doc = Document(file_path)

            # 1. Извлекаем абзацы
            for row_idx, para in enumerate(doc.paragraphs, start=1):
                text = para.text.strip()
                if text:
                    fields.append(ExtractedField(
                        raw_value=text,
                        normalized_value=text,
                        confidence=1.0,
                        source_box=(row_idx, 1, 1, 1)
                    ))

            # 2. Извлекаем таблицы
            row_idx = len(doc.paragraphs) + 1

            for table in doc.tables:
                for row in table.rows:
                    for col_idx, cell in enumerate(row.cells, start=1):
                        text = cell.text.strip()
                        if text:
                            fields.append(ExtractedField(
                                raw_value=text,
                                normalized_value=text,
                                confidence=1.0,
                                source_box=(row_idx, col_idx, 1, 1)
                            ))
                    row_idx += 1

        except Exception as e:
            raise ValueError(f"Ошибка чтения DOCX: {str(e)}")

        return RawDocument(
            file_path=file_path,
            pages=[fields],
            document_type="docx",
            metadata={
                "paragraphs_count": len(doc.paragraphs),
                "tables_count": len(doc.tables)
            }
        )