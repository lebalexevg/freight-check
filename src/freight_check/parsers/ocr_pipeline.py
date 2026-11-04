from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium

from freight_check.contracts import ExtractedField, RawDocument
from freight_check.parsers.base import BaseParser
from freight_check.parsers.ocr_engine import OCREngine


class OCRPipeline(BaseParser):
    """Парсер для PDF-сканов и изображений через OCR."""

    SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

    # DPI для растеризации PDF (оптимально для OCR)
    _DPI = 200

    def __init__(
        self,
        use_preprocessing: bool = True,
        min_confidence: float = 0.3,
        engine: OCREngine | None = None,
    ) -> None:
        """
        Args:
            use_preprocessing: Применять предобработку изображений.
            min_confidence: Минимальный порог уверенности OCR.
            engine: Готовый экземпляр OCREngine (для переиспользования).
        """
        self._engine = engine or OCREngine(use_preprocessing=use_preprocessing)
        self._min_confidence = min_confidence

    def parse(self, file_path: Path) -> RawDocument:
        """Парсит PDF-скан или изображение через OCR."""
        self._validate_file(file_path)

        ext = file_path.suffix.lower()

        if ext == ".pdf":
            return self._parse_pdf(file_path)
        if ext in self.SUPPORTED_IMAGE_EXTENSIONS:
            return self._parse_image(file_path)

        raise ValueError(f"Неподдерживаемый формат для OCR: {ext}")

    def _parse_pdf(self, file_path: Path) -> RawDocument:
        """Растеризует PDF и распознает каждую страницу."""
        pages: list[list[ExtractedField]] = []

        with pdfium.PdfDocument(str(file_path)) as pdf:
            pages_count = len(pdf)

            for page_idx in range(pages_count):
                page = pdf[page_idx]

                # pypdfium2 принимает float для scale, но типы могут быть неточными.
                # Используем float и type: ignore, чтобы сохранить точный DPI (200/72 ≈ 2.77)
                bitmap = page.render(scale=self._DPI / 72.0)  # type: ignore[arg-type]

                pil_image = bitmap.to_pil()
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

                fields = self._engine.recognize(image, min_confidence=self._min_confidence)
                pages.append(fields)

        return RawDocument(
            file_path=file_path,
            pages=pages,
            document_type="pdf_scan",
            metadata={"pages_count": len(pages)},
        )

    def _parse_image(self, file_path: Path) -> RawDocument:
        """Распознает текст на изображении.

        Читает байты через Python, чтобы корректно работать
        с кириллическими путями в Windows.
        """
        raw_bytes = file_path.read_bytes()
        image_array = np.frombuffer(raw_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError(f"Не удалось декодировать изображение: {file_path}")

        fields = self._engine.recognize(image, min_confidence=self._min_confidence)

        return RawDocument(
            file_path=file_path,
            pages=[fields],
            document_type="image",
            metadata={"format": file_path.suffix.lower()},
        )
