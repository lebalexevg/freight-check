from pathlib import Path
import xml.etree.ElementTree as ET

from freight_check.contracts import ExtractedField
from freight_check.parsers.base import BaseParser
from freight_check.parsers.models import RawDocument


class XMLParser(BaseParser):
    """Парсер для XML-файлов (включая титулы ЭТрН формата ФНС)."""

    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            cells_data = self._extract_text_from_element(root, row=1)

        except ET.ParseError as e:
            raise ValueError(f"Ошибка парсинга XML (невалидный формат): {str(e)}")
        except Exception as e:
            raise ValueError(f"Ошибка чтения XML: {str(e)}")

        return RawDocument(
            file_path=file_path,
            pages=[cells_data],  # Страниц нет, но контракты соблюдать нада
            document_type="xml",
            metadata={"root_tag": root.tag}
        )

    def _extract_text_from_element(self, element: ET.Element, row: int) -> list[ExtractedField]:
        """Рекурсивно извлекает текст и атрибуты из XML-дерева."""
        fields: list[ExtractedField] = []

        if element.text and element.text.strip():
            fields.append(ExtractedField(
                raw_value=element.text.strip(),
                normalized_value=element.text.strip(),
                confidence=1.0,
                # Для XML используем условные координаты: (глубина/row, col=1, w=1, h=1)
                source_box=(row, 1, 1, 1)
            ))
            row += 1

        for attr_name, attr_value in element.attrib.items():
            fields.append(ExtractedField(
                raw_value=f"{attr_name}={attr_value}",
                normalized_value=f"{attr_name}={attr_value.strip()}",
                confidence=1.0,
                source_box=(row, 1, 1, 1)
            ))
            row += 1

        for child in element:
            fields.extend(self._extract_text_from_element(child, row))

            row += len([f for f in fields if f.source_box[0] >= row]) or 1

        return fields