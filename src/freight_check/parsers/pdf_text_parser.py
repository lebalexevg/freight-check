from pathlib import Path
from typing import Any

import pdfplumber

from freight_check.contracts import ExtractedField, RawDocument
from freight_check.parsers.base import BaseParser


class PDFTextParser(BaseParser):
    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)

        pages: list[list[ExtractedField]] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    pages.append(self._process_page(page))
        except Exception as e:
            raise ValueError("Ошибка чтения PDF") from e

        return RawDocument(
            file_path=file_path,
            pages=pages,
            document_type="pdf",
            metadata={"pages_count": len(pages)},
        )

    def _process_page(self, page: Any) -> list[ExtractedField]:
        fields: list[ExtractedField] = []
        words = page.extract_words(x_tolerance=3, y_tolerance=3)

        for word in words:
            text = word.get("text", "").strip()
            if text:
                x0 = round(float(word.get("x0", 0)))
                top = round(float(word.get("top", 0)))
                x1 = round(float(word.get("x1", 0)))
                bottom = round(float(word.get("bottom", 0)))

                fields.append(
                    ExtractedField(
                        raw_value=text,
                        normalized_value=text,
                        confidence=1.0,
                        source_box=(x0, top, x1 - x0, bottom - top),
                    )
                )

        return fields
