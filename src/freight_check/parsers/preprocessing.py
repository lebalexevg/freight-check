import cv2
import numpy as np


class ImagePreprocessor:
    """Предобработка изображений для улучшения качества OCR."""

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """Перевод изображения в оттенки серого."""
        if image.ndim == 2:
            if image.ndim == 3 and image.shape[2] == 1:
                return image[:, :, 0]
            return image
        if image.ndim == 3 and image.shape[2] == 1:
            return image[:, :, 0]
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def denoise(image: np.ndarray) -> np.ndarray:
        """Удаление шумов (алгоритм Non-Local Means)."""
        return cv2.fastNlMeansDenoising(
            image, None, h=10, templateWindowSize=7, searchWindowSize=21
        )

    @staticmethod
    def deskew(image: np.ndarray, max_angle: float = 5.0) -> np.ndarray:
        """Устранение перекоса страницы (deskew).

        Определяет угол наклона через minAreaRect на бинаризованном
        изображении и поворачивает исходное.
        """
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(binary > 0))
        if coords.shape[0] < 50:
            return image

        rect = cv2.minAreaRect(coords)
        angle = rect[-1]

        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle

        if abs(angle) < 0.5 or abs(angle) > max_angle:
            return image

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
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
        aligned = cls.deskew(denoised)
        return cls.binarize(aligned)
