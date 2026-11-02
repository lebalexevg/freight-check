from pathlib import Path

import pytest

from freight_check.contracts import RawDocument
from freight_check.parsers.csv_parser import CSVParser


@pytest.fixture
def sample_csv_utf8(tmp_path: Path) -> Path:
    """Создает тестовый CSV файл в кодировке UTF-8 с BOM."""
    file_path = tmp_path / "test_utf8.csv"
    content = "Параметр;Значение\nГосномер;А123ВС77\nВес;20000"
    file_path.write_text(content, encoding="utf-8-sig")
    return file_path


@pytest.fixture
def sample_csv_cp1251(tmp_path: Path) -> Path:
    """Создает тестовый CSV файл в кодировке CP1251 (имитация выгрузки из 1С)."""
    file_path = tmp_path / "test_cp1251.csv"
    content = "Параметр;Значение\nГосномер;А123ВС77\nВес;20000"
    file_path.write_bytes(content.encode("cp1251"))
    return file_path


@pytest.fixture
def empty_csv(tmp_path: Path) -> Path:
    """Создает пустой CSV файл."""
    file_path = tmp_path / "empty.csv"
    file_path.write_text("", encoding="utf-8")
    return file_path


def test_parse_valid_csv_utf8(sample_csv_utf8: Path) -> None:
    """Тест успешного парсинга валидного UTF-8 CSV."""
    parser = CSVParser()
    raw_doc = parser.parse(sample_csv_utf8)

    assert isinstance(raw_doc, RawDocument)
    assert raw_doc.document_type == "csv"

    flat_cells = raw_doc.pages[0]
    values = [c.normalized_value for c in flat_cells]

    assert "А123ВС77" in values
    assert "20000" in values
    assert all(c.confidence == 1.0 for c in flat_cells)


def test_parse_valid_csv_cp1251(sample_csv_cp1251: Path) -> None:
    """Тест фолбэка на кодировку CP1251 при ошибке UTF-8."""
    parser = CSVParser()
    raw_doc = parser.parse(sample_csv_cp1251)

    assert isinstance(raw_doc, RawDocument)
    flat_cells = raw_doc.pages[0]
    values = [c.normalized_value for c in flat_cells]

    # Проверяем, что кириллица корректно декодировалась
    assert "А123ВС77" in values


def test_parse_csv_not_found() -> None:
    """Тест обработки несуществующего файла."""
    parser = CSVParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("missing.csv"))


def test_parse_empty_csv(empty_csv: Path) -> None:
    """Тест обработки пустого файла."""
    parser = CSVParser()
    raw_doc = parser.parse(empty_csv)

    assert isinstance(raw_doc, RawDocument)
    assert len(raw_doc.pages[0]) == 0
