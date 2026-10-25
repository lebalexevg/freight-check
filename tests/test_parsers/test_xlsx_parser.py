import pytest
from pathlib import Path
import openpyxl

from freight_check.parsers.xlsx_parser import XLSXParser
from freight_check.parsers.models import RawDocument


@pytest.fixture
def sample_xlsx(tmp_path: Path) -> Path:
    """Создает тестовый xlsx файл с известными данными."""
    file_path = tmp_path / "test_order.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active

    # Заполняем ячейки
    ws["A1"] = "Госномер ТС"
    ws["B1"] = "А123ВС77"
    ws["A2"] = "Вес груза"
    ws["B2"] = 20000  # Число, чтобы проверить парсинг разных типов

    wb.save(file_path)
    return file_path


@pytest.fixture
def empty_xlsx(tmp_path: Path) -> Path:
    """Создает пустой xlsx файл."""
    file_path = tmp_path / "empty.xlsx"
    wb = openpyxl.Workbook()
    wb.save(file_path)
    return file_path


def test_parse_valid_file(sample_xlsx: Path) -> None:
    """Тест успешного парсинга валидного файла."""
    parser = XLSXParser()
    raw_doc = parser.parse(sample_xlsx)

    assert isinstance(raw_doc, RawDocument)
    assert raw_doc.file_path == sample_xlsx
    assert raw_doc.document_type == "xlsx"
    assert raw_doc.metadata["sheets_count"] == 1
    assert len(raw_doc.pages) == 1

    page = raw_doc.pages[0]
    values = [cell.normalized_value for cell in page]

    assert "А123ВС77" in values
    assert "20000" in values
    assert "Госномер ТС" in values

    target_cell = next(c for c in page if c.normalized_value == "А123ВС77")
    assert target_cell.confidence == 1.0
    assert target_cell.source_box is not None
    assert target_cell.raw_value == "А123ВС77"


def test_parse_file_not_found() -> None:
    """Тест обработки несуществующего файла."""
    parser = XLSXParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("nonexistent_file.xlsx"))


def test_parse_empty_file(empty_xlsx: Path) -> None:
    """Тест обработки пустого файла (не должен падать)."""
    parser = XLSXParser()
    raw_doc = parser.parse(empty_xlsx)

    assert isinstance(raw_doc, RawDocument)

    # В пустом файле по умолчанию есть 1 пустой лист
    assert len(raw_doc.pages) == 1
    assert raw_doc.metadata["sheets_count"] == 1

    assert len(raw_doc.pages[0]) == 0