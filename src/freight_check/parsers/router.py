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
    """Маршрутизатор, выбирающий подходящий парсер на основе расширения файла."""

    _parsers: dict[str, type[BaseParser]] = {
        ".xlsx": XLSXParser,
        ".xls": XLSParser,
        ".csv": CSVParser,
        ".xml": XMLParser,
        ".docx": DOCXParser,
        ".pdf": PDFTextParser,
    }

    _ocr_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

    @classmethod
    def get_parser(cls, file_path: Path) -> BaseParser:
        ext = file_path.suffix.lower()

        # Для изображений всегда используем OCR
        if ext in cls._ocr_extensions:
            return OCRPipeline()

        # Для PDF нужно определить: цифровой или скан
        if ext == ".pdf":
            return cls._detect_pdf_type(file_path)

        parser_class = cls._parsers.get(ext)

        if not parser_class:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")

        return parser_class()

    @classmethod
    def _detect_pdf_type(cls, file_path: Path) -> BaseParser:
        """Определяет тип PDF: цифровой или скан."""
        try:
            pdf = pdfium.PdfDocument(str(file_path))
            page = pdf[0]
            text = page.get_textpage().get_text_range()
            pdf.close()

            # Если есть извлекаемый текст — цифровой PDF
            if text.strip():
                return PDFTextParser()
            else:
                return OCRPipeline()
        except Exception:
            # Если не удалось прочитать — предполагаем скан
            return OCRPipeline()

    @classmethod
    def parse(cls, file_path: Path) -> RawDocument:
        """Удобный метод для прямого вызова парсинга."""
        parser = cls.get_parser(file_path)
        return parser.parse(file_path)
