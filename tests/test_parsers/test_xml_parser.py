from pathlib import Path

import pytest

from freight_check.contracts import RawDocument
from freight_check.parsers.xml_parser import XMLParser


@pytest.fixture
def sample_xml(tmp_path: Path) -> Path:
    """Создает тестовый XML-файл, имитирующий структуру ЭТрН."""
    file_path = tmp_path / "test_etrn.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Документ Идентификатор="ID-12345" Дата="2023-10-25">
    <Груз>
        <Наименование>Стройматериалы</Наименование>
        <Вес>20000</Вес>
    </Груз>
    <Транспорт>
        <Госномер>А123ВС77</Госномер>
    </Транспорт>
</Документ>
"""
    file_path.write_text(xml_content, encoding="utf-8")
    return file_path


@pytest.fixture
def invalid_xml(tmp_path: Path) -> Path:
    """Создает невалидный XML-файл (без закрывающего тега)."""
    file_path = tmp_path / "invalid.xml"
    file_path.write_text("<Документ><Груз>Тест", encoding="utf-8")
    return file_path


def test_parse_valid_xml(sample_xml: Path) -> None:
    """Тест успешного парсинга валидного XML."""
    parser = XMLParser()
    raw_doc = parser.parse(sample_xml)

    assert isinstance(raw_doc, RawDocument)
    assert raw_doc.document_type == "xml"
    assert raw_doc.metadata["root_tag"] == "Документ"
    assert len(raw_doc.pages) == 1

    flat_cells = raw_doc.pages[0]
    values = [cell.normalized_value for cell in flat_cells]

    # Проверяем атрибуты
    assert any("ID-12345" in v for v in values)
    # Проверяем тексты с тегами
    assert any("Стройматериалы" in v for v in values)
    assert any("А123ВС77" in v for v in values)
    assert any("20000" in v for v in values)

    assert all(cell.confidence == 1.0 for cell in flat_cells)


def test_parse_file_not_found() -> None:
    """Тест обработки несуществующего файла."""
    parser = XMLParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("nonexistent.xml"))


def test_parse_invalid_xml(invalid_xml: Path) -> None:
    """Тест обработки невалидного XML (должен выбросить ValueError)."""
    parser = XMLParser()
    with pytest.raises(ValueError, match="Ошибка парсинга XML"):
        parser.parse(invalid_xml)
