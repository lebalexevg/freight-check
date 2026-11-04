"""Генерация иконки приложения и шрифтовых иконок интерфейса."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
)

from freight_check.ui.resources import get_resource_path

SEGOE_FONT_FAMILY: str = "Segoe Fluent Icons"
SEGOE_FALLBACK_FAMILY: str = "Segoe MDL2 Assets"

# Глифы иконок интерфейса
GLYPH_REFRESH: str = "\ue72c"  # Замена / Синхронизация
GLYPH_CLOSE: str = "\ue711"  # Удаление / Крестик
GLYPH_CHECK: str = "\ue73e"  # Галочка совпадения
GLYPH_WARNING: str = "\ue7ba"  # Треугольник предупреждения
GLYPH_ERROR: str = "\uea39"  # Ошибка расхождения
GLYPH_HELP: str = "\ue897"  # Вопрос / Неопределенность
GLYPH_PLAY: str = "\ue768"  # Демо-сценарии
GLYPH_TRASH: str = "\ue74d"  # Очистить всё
GLYPH_DOCUMENT: str = "\ue8a5"  # Страница документа с загнутым уголком
GLYPH_FOLDER: str = "\ue838"  # Папка / Обзор файлов


DEFAULT_ICON_COLOR: QColor = QColor("#334155")


def get_segoe_font(point_size: int = 11) -> QFont:
    """Возвращает системный шрифт Segoe для иконок с фоллбэком на MDL2 и UI Symbol."""
    font = QFont(SEGOE_FONT_FAMILY, point_size)
    font.setFamilies([SEGOE_FONT_FAMILY, SEGOE_FALLBACK_FAMILY, "Segoe UI Symbol"])
    return font


def create_segoe_icon(
    glyph: str,
    color: QColor | None = None,
    base_size: int = 16,
    y_offset: float = 0.0,
    weight: QFont.Weight | None = None,
    glyph_scale: float = 0.88,
) -> QIcon:
    """Генерирует мульти-масштабный QIcon из шрифтового глифа."""
    resolved_color = color or DEFAULT_ICON_COLOR
    resolved_weight = (
        weight
        if weight is not None
        else (QFont.Weight.Bold if base_size < 32 else QFont.Weight.Normal)
    )
    icon = QIcon()

    for scale in (1, 2, 3):
        dim = base_size * scale
        img = QImage(dim, dim, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        font = get_segoe_font()
        font.setPixelSize(int(round(dim * glyph_scale)))
        font.setWeight(resolved_weight)

        path = QPainterPath()
        path.addText(0, 0, font, glyph)
        br = path.boundingRect()

        target_cx = dim / 2.0
        target_cy = (dim / 2.0) + (y_offset * scale)
        dx = target_cx - br.center().x()
        dy = target_cy - br.center().y()
        path.translate(dx, dy)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillPath(path, resolved_color)
        painter.end()

        pix = QPixmap.fromImage(img)
        pix.setDevicePixelRatio(scale)
        icon.addPixmap(pix)

    return icon


_APP_ICON_CACHE: QIcon | None = None


def get_app_icon_path() -> Path:
    """Определяет путь к файлу иконки приложения (.ico или .png) с поддержкой PyInstaller."""
    candidate_ico = get_resource_path("assets/icons/app_icon.ico")
    if candidate_ico.exists():
        return candidate_ico
    candidate_png = get_resource_path("assets/icons/app_icon.png")
    if candidate_png.exists():
        return candidate_png
    candidate_svg = get_resource_path("assets/icons/app_icon.svg")
    if candidate_svg.exists():
        return candidate_svg
    return candidate_ico


def get_app_icon() -> QIcon:
    """Возвращает иконку приложения."""
    global _APP_ICON_CACHE
    if _APP_ICON_CACHE is None or _APP_ICON_CACHE.isNull():
        path = get_app_icon_path()
        _APP_ICON_CACHE = QIcon(str(path)) if path.exists() else QIcon()
    return _APP_ICON_CACHE
