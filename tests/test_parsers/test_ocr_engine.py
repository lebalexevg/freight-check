import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from freight_check.parsers.ocr_engine import OCREngine
from freight_check.parsers.preprocessing import ImagePreprocessor


@pytest.fixture
def ocr_engine() -> OCREngine:
    """Создает экземпляр OCR-движка."""
    return OCREngine(use_preprocessing=False)


@pytest.fixture
def sample_image_with_text() -> np.ndarray:
    """Генерирует изображение с русским текстом через Pillow."""
    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)

    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    try:
        font = ImageFont.truetype(font_path, 48)
    except OSError:
        font = ImageFont.load_default()

    draw.text((50, 50), "Госномер: А123ВС77", fill="black", font=font)

    img_np = np.array(img)
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


def test_preprocessing_pipeline(sample_image_with_text: np.ndarray) -> None:
    """Тест пайплайна предобработки."""
    processed = ImagePreprocessor.process(sample_image_with_text)

    assert isinstance(processed, np.ndarray)
    assert processed.ndim == 2
    assert set(np.unique(processed)).issubset({0, 255})


def test_ocr_recognition(ocr_engine: OCREngine, sample_image_with_text: np.ndarray) -> None:
    """Тест базового распознавания текста.

    Примечание: OCR может путать кириллические и латинские буквы
    (Г→F, о→o, с→c, н→H, В→B, С→C). Нормализация этих ошибок —
    задача модуля семантического извлечения (Разработчик 3, ТЗ п. 21.a).
    """
    fields = ocr_engine.recognize(sample_image_with_text)

    if fields:
        recognized_text = " ".join(f.normalized_value for f in fields)
        print(f"\nРаспознанный текст: {recognized_text}")
        print(f"Количество полей: {len(fields)}")
        for f in fields:
            print(f"  - '{f.normalized_value}' (confidence: {f.confidence:.2f})")

    # Проверяем, что текст извлечен
    assert len(fields) > 0, "OCR не распознал ни одного текстового блока"

    # Проверяем структуру ExtractedField
    for field in fields:
        assert 0.0 <= field.confidence <= 1.0
        assert field.source_box is not None
        assert len(field.source_box) == 4

    # Проверяем, что OCR извлек текст с высокой уверенностью (> 0.7 по ТЗ)
    assert all(f.confidence > 0.7 for f in fields), (
        f"Уверенность OCR ниже порога 0.7: {[f.confidence for f in fields]}"
    )

    # Проверяем наличие числовой части (она однозначна и не зависит от кириллицы/латиницы)
    all_text = " ".join(f.normalized_value for f in fields)
    assert "123" in all_text, f"Числовая часть '123' не найдена в: {all_text}"
    assert "77" in all_text, f"Числовая часть '77' не найдена в: {all_text}"


def test_ocr_empty_image(ocr_engine: OCREngine) -> None:
    """Тест обработки полностью белой картинки (без текста)."""
    empty_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    fields = ocr_engine.recognize(empty_img)

    assert fields == []
