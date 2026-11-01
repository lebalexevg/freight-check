import xml.etree.ElementTree as ET
from pathlib import Path

from freight_check.contracts import ExtractedField, RawDocument
from freight_check.parsers.base import BaseParser


class XMLParser(BaseParser):
    def parse(self, file_path: Path) -> RawDocument:
        self._validate_file(file_path)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            cells_data = self._extract_text_from_element(root, row=1)
        except ET.ParseError as e:
            raise ValueError("Ошибка парсинга XML (невалидный формат)") from e
        except Exception as e:
            raise ValueError("Ошибка чтения XML") from e

        return RawDocument(
            file_path=file_path,
            pages=[cells_data],
            document_type="xml",
            metadata={"root_tag": root.tag},
        )

    def _extract_text_from_element(self, element: ET.Element, row: int) -> list[ExtractedField]:
        fields: list[ExtractedField] = []

        # Сохраняем тег вместе с текстом, чтобы семантический модуль понимал контекст
        if element.text and element.text.strip():
            text = element.text.strip()
            fields.append(
                ExtractedField(
                    raw_value=f"{element.tag}: {text}",
                    normalized_value=f"{element.tag}: {text}",
                    confidence=1.0,
                    source_box=(row, 1, 1, 1),
                )
            )
            row += 1

        for attr_name, attr_value in element.attrib.items():
            fields.append(
                ExtractedField(
                    raw_value=f"{element.tag}@{attr_name}={attr_value}",
                    normalized_value=f"{element.tag}@{attr_name}={attr_value.strip()}",
                    confidence=1.0,
                    source_box=(row, 1, 1, 1),
                )
            )
            row += 1

        for child in element:
            fields.extend(self._extract_text_from_element(child, row))
            row += 1

        return fields
