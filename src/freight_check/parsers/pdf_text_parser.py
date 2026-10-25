from pathlib import Path
import pdfplumber

from freight_check.contracts import ExtractedField
from freight_check.parsers.base import BaseParser
from freight_check.parsers.models import RawDocument


class PDFTextParser(BaseParser):
    """Парсер для цифровых PDF-файлов (с текстовым слоем)."""

    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)

        pages: list[list[ExtractedField]] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_fields = self._process_page(page)
                    pages.append(page_fields)

        except Exception as e:
            raise ValueError(f"Ошибка чтения PDF: {str(e)}")

        return RawDocument(
            file_path=file_path,
            pages=pages,
            document_type="pdf",
            metadata={"pages_count": len(pages)}
        )

    def _process_page(self, page) -> list[ExtractedField]:
        """Извлекает текст и координаты со страницы PDF."""
        fields: list[ExtractedField] = []

        words = page.extract_words(x_tolerance=3, y_tolerance=3)

        for word in words:
            text = word.get("text", "").strip()
            if text:
                x0 = round(word.get("x0", 0))
                top = round(word.get("top", 0))
                x1 = round(word.get("x1", 0))
                bottom = round(word.get("bottom", 0))
                width = x1 - x0
                height = bottom - top

                fields.append(ExtractedField(
                    raw_value=text,
                    normalized_value=text,
                    confidence=1.0,
                    source_box=(x0, top, width, height)
                ))

        tables = page.extract_tables()
        for table in tables:
            for row_idx, row in enumerate(table):
                for col_idx, cell_value in enumerate(row):
                    if cell_value and str(cell_value).strip():
                        text = str(cell_value).strip()
                        fields.append(ExtractedField(
                            raw_value=text,
                            normalized_value=text,
                            confidence=1.0,
                            source_box=(row_idx + 1, col_idx + 1, 1, 1)
                        ))

        return fields