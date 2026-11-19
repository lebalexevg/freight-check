from __future__ import annotations

from pathlib import Path

from PIL import ImageFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def get_pil_font(size: int = 24) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Возвращает системный шрифт Pillow с поддержкой кириллицы."""
    candidates = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path_str in candidates:
        if Path(path_str).exists():
            try:
                return ImageFont.truetype(path_str, size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_reportlab_font() -> str:
    """Регистрирует и возвращает шрифт для ReportLab."""
    candidates = [
        ("Arial", "C:\\Windows\\Fonts\\arial.ttf"),
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for name, path_str in candidates:
        if Path(path_str).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path_str))
                return name
            except Exception:
                continue
    return "Helvetica"


REPORTLAB_FONT = get_reportlab_font()
