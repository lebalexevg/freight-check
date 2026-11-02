from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from freight_check.contracts import RawDocument
from freight_check.parsers.pdf_text_parser import PDFTextParser

# Регистрируем системный шрифт Arial для генерации тестовых PDF
# (Это нужно только для тестов, чтобы reportlab умел рисовать кириллицу)
try:
    pdfmetrics.registerFont(TTFont("Arial", "C:\\Windows\\Fonts\\arial.ttf"))
    TEST_FONT = "Arial"
except Exception:
    # Фолбэк, если вдруг шрифт не найден (например, на Linux в CI)
    TEST_FONT = "Helvetica"


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Создает тестовый PDF файл с кириллическим текстом."""
    file_path = tmp_path / "test_order.pdf"
    c = canvas.Canvas(str(file_path), pagesize=A4)

    # --- Страница 1 ---
    c.setFont(TEST_FONT, 12)
    c.drawString(100, 750, "Заявка на перевозку")
    c.drawString(100, 730, "Госномер: А123ВС77")
    c.drawString(100, 710, "Вес груза: 20000 кг")

    c.showPage()

    # --- Страница 2 ---
    c.setFont(TEST_FONT, 12)
    c.drawString(100, 750, "Водитель: Иванов И.И.")
    c.drawString(100, 730, "Телефон: +7 900 123 45 67")

    c.save()
    return file_path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Создает пустой PDF файл."""
    file_path = tmp_path / "empty.pdf"
    c = canvas.Canvas(str(file_path), pagesize=A4)
    c.save()
    return file_path


def test_parse_valid_pdf(sample_pdf: Path) -> None:
    """Тест успешного парсинга валидного PDF с кириллицей."""
    parser = PDFTextParser()
    raw_doc = parser.parse(sample_pdf)

    assert isinstance(raw_doc, RawDocument)
    assert raw_doc.document_type == "pdf"
    assert raw_doc.metadata["pages_count"] == 2
    assert len(raw_doc.pages) == 2

    page1_fields = raw_doc.pages[0]
    page1_values = [f.normalized_value for f in page1_fields]

    assert any("Заявка" in v for v in page1_values)
    assert any("А123ВС77" in v for v in page1_values)
    assert any("20000" in v for v in page1_values)

    page2_fields = raw_doc.pages[1]
    page2_values = [f.normalized_value for f in page2_fields]

    assert any("Иванов" in v for v in page2_values)
    assert any("+7" in v or "900" in v for v in page2_values)

    assert all(f.source_box is not None for f in page1_fields)
    assert all(f.confidence == 1.0 for f in page1_fields)


def test_parse_pdf_not_found() -> None:
    """Тест обработки несуществующего файла."""
    parser = PDFTextParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("missing.pdf"))


def test_parse_invalid_pdf(tmp_path: Path) -> None:
    """Тест обработки файла, который не является валидным PDF."""
    file_path = tmp_path / "fake.pdf"
    file_path.write_text("Это просто текст, а не PDF", encoding="utf-8")

    parser = PDFTextParser()
    with pytest.raises(ValueError, match="Ошибка чтения PDF"):
        parser.parse(file_path)


def test_parse_empty_pdf(empty_pdf: Path) -> None:
    """Тест обработки пустого PDF файла."""
    parser = PDFTextParser()
    raw_doc = parser.parse(empty_pdf)

    assert isinstance(raw_doc, RawDocument)
    assert raw_doc.metadata["pages_count"] == 0
    assert len(raw_doc.pages) == 0
