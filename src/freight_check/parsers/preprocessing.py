import cv2
import numpy as np


class ImagePreprocessor:
    """Предобработка изображений для улучшения качества OCR."""

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """Перевод изображения в оттенки серого."""
        if image.ndim == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def denoise(image: np.ndarray) -> np.ndarray:
        """Удаление шумов (алгоритм Non-Local Means)."""
        return cv2.fastNlMeansDenoising(
            image, None, h=10, templateWindowSize=7, searchWindowSize=21
        )

    @staticmethod
    def binarize(image: np.ndarray) -> np.ndarray:
        """Бинаризация изображения (метод Оцу)."""
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    @classmethod
    def process(cls, image: np.ndarray) -> np.ndarray:
        """Применяет полный пайплайн предобработки."""
        gray = cls.to_grayscale(image)
        denoised = cls.denoise(gray)
        binary = cls.binarize(denoised)
        return binary
