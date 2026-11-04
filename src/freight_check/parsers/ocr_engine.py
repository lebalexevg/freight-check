from functools import lru_cache

import numpy as np
from rapidocr_onnxruntime import RapidOCR

from freight_check.contracts import ExtractedField
from freight_check.parsers.preprocessing import ImagePreprocessor


@lru_cache(maxsize=1)
def _get_ocr_engine() -> RapidOCR:
    """Создает и кэширует единственный экземпляр RapidOCR."""
    return RapidOCR()


class OCREngine:
    """Обертка над RapidOCR для извлечения текста с координатами."""

    def __init__(self, use_preprocessing: bool = True) -> None:
        """
        Args:
            use_preprocessing: Применять предобработку изображений.
                Для сканов — True, для четких цифровых — False.
        """
        self._engine = _get_ocr_engine()
        self._use_preprocessing = use_preprocessing

    def recognize(self, image: np.ndarray, min_confidence: float = 0.0) -> list[ExtractedField]:
        """Распознает текст на изображении.

        Args:
            image: Изображение в формате numpy array (BGR или grayscale).
            min_confidence: Минимальный порог уверенности для фильтрации мусора.

        Returns:
            Список извлеченных полей с координатами и уверенностью.
        """
        processed_image = ImagePreprocessor.process(image) if self._use_preprocessing else image

        result, _ = self._engine(processed_image)

        if not result:
            return []

        fields: list[ExtractedField] = []

        for box, text, score in result:
            score_float = float(score)

            if score_float < min_confidence:
                continue

            x_coords = [int(point[0]) for point in box]
            y_coords = [int(point[1]) for point in box]

            x = min(x_coords)
            y = min(y_coords)
            width = max(x_coords) - x
            height = max(y_coords) - y

            fields.append(
                ExtractedField(
                    raw_value=str(text),
                    normalized_value=str(text).strip(),
                    confidence=score_float,
                    source_box=(x, y, width, height),
                )
            )

        return fields
