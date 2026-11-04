from pathlib import Path

import pypdfium2 as pdfium

from freight_check.contracts import RawDocument
from freight_check.parsers.base import BaseParser
from freight_check.parsers.csv_parser import CSVParser
from freight_check.parsers.docx_parser import DOCXParser
from freight_check.parsers.ocr_pipeline import OCRPipeline
from freight_check.parsers.pdf_text_parser import PDFTextParser
from freight_check.parsers.xls_parser import XLSParser
from freight_check.parsers.xlsx_parser import XLSXParser
from freight_check.parsers.xml_parser import XMLParser


class ParserRouter:
    """Маршрутизатор, выбирающий подходящий парсер по расширению файла."""

    _parsers: dict[str, type[BaseParser]] = {
        ".xlsx": XLSXParser,
        ".xls": XLSParser,
        ".csv": CSVParser,
        ".xml": XMLParser,
        ".docx": DOCXParser,
        ".pdf": PDFTextParser,
    }

    _ocr_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

    _PDF_TEXT_CHECK_PAGES = 3

    @classmethod
    def get_parser(cls, file_path: Path) -> BaseParser:
        ext = file_path.suffix.lower()

        if ext in cls._ocr_extensions:
            return OCRPipeline()

        if ext == ".pdf":
            return cls._detect_pdf_type(file_path)

        parser_class = cls._parsers.get(ext)
        if not parser_class:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")

        return parser_class()

    @classmethod
    def _detect_pdf_type(cls, file_path: Path) -> BaseParser:
        """Определяет тип PDF: цифровой или скан.

        Проверяет первые несколько страниц на наличие извлекаемого текста.
        """
        try:
            with pdfium.PdfDocument(str(file_path)) as pdf:
                pages_count = len(pdf)
                if pages_count == 0:
                    return OCRPipeline()

                pages_to_check = min(pages_count, cls._PDF_TEXT_CHECK_PAGES)
                for page_idx in range(pages_to_check):
                    page = pdf[page_idx]
                    text = page.get_textpage().get_text_range()
                    if text.strip():
                        return PDFTextParser()

            return OCRPipeline()
        except Exception:
            return OCRPipeline()

    @classmethod
    def parse(cls, file_path: Path) -> RawDocument:
        """Удобный метод для прямого вызова парсинга."""
        parser = cls.get_parser(file_path)
        return parser.parse(file_path)
