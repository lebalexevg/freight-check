import numpy as np
from rapidocr_onnxruntime import RapidOCR

from freight_check.contracts import ExtractedField
from freight_check.parsers.preprocessing import ImagePreprocessor


class OCREngine:
    """Обертка над RapidOCR для извлечения текста с координатами."""

    def __init__(self) -> None:
        self._engine = RapidOCR()

    def recognize(
        self, image: np.ndarray, min_confidence: float = 0.0
    ) -> list[ExtractedField]:
        """Распознает текст на изображении.

        Args:
            image: Изображение в формате numpy array (BGR или grayscale).
            min_confidence: Минимальный порог уверенности для фильтрации мусора.

        Returns:
            Список извлеченных полей с координатами и уверенностью.
        """
        processed_image = ImagePreprocessor.process(image)

        result, _ = self._engine(processed_image)

        if not result:
            return []

        fields: list[ExtractedField] = []

        for box, text, score in result:
            if score < min_confidence:
                continue

            x_coords = [int(point[0]) for point in box]
            y_coords = [int(point[1]) for point in box]

            x = min(x_coords)
            y = min(y_coords)
            width = max(x_coords) - x
            height = max(y_coords) - y

            fields.append(
                ExtractedField(
                    raw_value=text,
                    normalized_value=text.strip(),
                    confidence=float(score),
                    source_box=(x, y, width, height),
                )
            )

        return fields
