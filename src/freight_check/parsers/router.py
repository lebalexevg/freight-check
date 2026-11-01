from pathlib import Path

from freight_check.contracts import RawDocument
from freight_check.parsers.base import BaseParser
from freight_check.parsers.csv_parser import CSVParser
from freight_check.parsers.docx_parser import DOCXParser
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

    @classmethod
    def get_parser(cls, file_path: Path) -> BaseParser:
        ext = file_path.suffix.lower()
        parser_class = cls._parsers.get(ext)

        if not parser_class:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")

        return parser_class()

    @classmethod
    def parse(cls, file_path: Path) -> RawDocument:
        """Удобный метод для прямого вызова парсинга."""
        parser = cls.get_parser(file_path)
        return parser.parse(file_path)
