from pathlib import Path

import pytest
from docx import Document

from freight_check.contracts import RawDocument
from freight_check.parsers.docx_parser import DOCXParser


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    """Создает тестовый docx файл с абзацами и таблицей."""
    file_path = tmp_path / "test_order.docx"
    doc = Document()

    doc.add_paragraph("Заявка на перевозку №123")
    doc.add_paragraph("Госномер ТС: А123ВС77")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Параметр"
    table.cell(0, 1).text = "Значение"
    table.cell(1, 0).text = "Вес груза"
    table.cell(1, 1).text = "20000 кг"

    doc.save(str(file_path))
    return file_path


@pytest.fixture
def empty_docx(tmp_path: Path) -> Path:
    """Создает пустой docx файл."""
    file_path = tmp_path / "empty.docx"
    doc = Document()
    doc.save(str(file_path))
    return file_path


def test_parse_valid_docx(sample_docx: Path) -> None:
    """Тест успешного парсинга валидного DOCX."""
    parser = DOCXParser()
    raw_doc = parser.parse(sample_docx)

    assert isinstance(raw_doc, RawDocument)
    assert raw_doc.document_type == "docx"
    assert raw_doc.metadata["paragraphs_count"] == 2
    assert raw_doc.metadata["tables_count"] == 1

    flat_cells = raw_doc.pages[0]
    values = [c.normalized_value for c in flat_cells]

    assert "Заявка на перевозку №123" in values
    assert "Госномер ТС: А123ВС77" in values
    assert "20000 кг" in values
    assert all(c.confidence == 1.0 for c in flat_cells)


def test_parse_docx_not_found() -> None:
    """Тест обработки несуществующего файла."""
    parser = DOCXParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("missing.docx"))


def test_parse_invalid_docx(tmp_path: Path) -> None:
    """Тест обработки файла, который не является валидным DOCX."""
    file_path = tmp_path / "fake.docx"
    file_path.write_text("Это просто текст, а не бинарный DOCX", encoding="utf-8")

    parser = DOCXParser()
    with pytest.raises(ValueError, match="Ошибка чтения DOCX"):
        parser.parse(file_path)


def test_parse_empty_docx(empty_docx: Path) -> None:
    """Тест обработки пустого файла."""
    parser = DOCXParser()
    raw_doc = parser.parse(empty_docx)

    assert isinstance(raw_doc, RawDocument)
    assert len(raw_doc.pages[0]) == 0
    assert raw_doc.metadata["paragraphs_count"] == 0
