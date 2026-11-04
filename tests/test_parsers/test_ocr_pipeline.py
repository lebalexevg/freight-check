from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from freight_check.contracts import RawDocument
from freight_check.parsers.ocr_pipeline import OCRPipeline


@pytest.fixture
def ocr_pipeline() -> OCRPipeline:
    """Создает экземпляр OCR-пайплайна без предобработки для тестов."""
    return OCRPipeline(use_preprocessing=False, min_confidence=0.0)


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Создает тестовое изображение с текстом."""
    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)

    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    try:
        font = ImageFont.truetype(font_path, 48)
    except OSError:
        font = ImageFont.load_default()

    draw.text((50, 50), "TEST DOCUMENT", fill="black", font=font)
    draw.text((50, 120), "Plate: A123BC77", fill="black", font=font)

    file_path = tmp_path / "test.png"
    img.save(str(file_path))
    return file_path


@pytest.fixture
def empty_image(tmp_path: Path) -> Path:
    """Создает пустое белое изображение."""
    img = Image.new("RGB", (400, 400), color="white")
    file_path = tmp_path / "empty.png"
    img.save(str(file_path))
    return file_path


def test_parse_image(ocr_pipeline: OCRPipeline, sample_image: Path) -> None:
    """Тест распознавания изображения."""
    raw_doc = ocr_pipeline.parse(sample_image)

    assert isinstance(raw_doc, RawDocument)
    assert raw_doc.document_type == "image"
    assert len(raw_doc.pages) == 1
    assert len(raw_doc.pages[0]) > 0

    # Проверяем структуру
    for field in raw_doc.pages[0]:
        assert 0.0 <= field.confidence <= 1.0
        assert field.source_box is not None


def test_parse_empty_image(ocr_pipeline: OCRPipeline, empty_image: Path) -> None:
    """Тест обработки пустого изображения."""
    raw_doc = ocr_pipeline.parse(empty_image)

    assert isinstance(raw_doc, RawDocument)
    # Пустое изображение может дать 0 или несколько ложных срабатываний
    assert len(raw_doc.pages) == 1


def test_parse_unsupported_format(ocr_pipeline: OCRPipeline, tmp_path: Path) -> None:
    """Тест обработки неподдерживаемого формата."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("text")

    with pytest.raises(ValueError, match="Неподдерживаемый формат"):
        ocr_pipeline.parse(file_path)


def test_parse_nonexistent_file(ocr_pipeline: OCRPipeline) -> None:
    """Тест обработки несуществующего файла."""
    with pytest.raises(FileNotFoundError):
        ocr_pipeline.parse(Path("nonexistent.png"))
