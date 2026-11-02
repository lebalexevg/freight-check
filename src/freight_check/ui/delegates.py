"""Кастомные делегаты PySide6 для отрисовки статусов, diff-токенов и моноширинных реквизитов."""

from PySide6.QtCore import (
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    QRect,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
)
from PySide6.QtWidgets import (
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from freight_check.contracts import ValidationStatus
from freight_check.ui.icons import (
    GLYPH_CHECK,
    GLYPH_ERROR,
    GLYPH_HELP,
    GLYPH_WARNING,
    get_segoe_font,
)
from freight_check.ui.models import (
    DIFF_HIGHLIGHTS_ROLE,
    IS_MONOSPACE_ROLE,
    STATUS_ROLE,
)

# Цветовые константы статусов в дизайн-системе Slate/Zinc
COLOR_CRITICAL_MARKER = QColor("#EF4444")
COLOR_CRITICAL_TEXT = QColor("#B91C1C")
COLOR_CRITICAL_BG = QColor("#FEE2E2")

COLOR_WARNING_MARKER = QColor("#F59E0B")
COLOR_WARNING_TEXT = QColor("#B45309")
COLOR_WARNING_BG = QColor("#FEF3C7")

COLOR_UNCERTAIN_MARKER = QColor("#94A3B8")
COLOR_UNCERTAIN_TEXT = QColor("#475569")
COLOR_UNCERTAIN_BG = QColor("#F1F5F9")

COLOR_MATCH_MARKER = QColor("#10B981")
COLOR_MATCH_TEXT = QColor("#64748B")

COLOR_TEXT_PRIMARY = QColor("#0F172A")
COLOR_SELECTION_BG = QColor("#E0E7FF")

# Векторные иконки Segoe Fluent Icons для каждого статуса
STATUS_GLYPHS: dict[ValidationStatus, str] = {
    ValidationStatus.CRITICAL: GLYPH_ERROR,
    ValidationStatus.WARNING: GLYPH_WARNING,
    ValidationStatus.UNCERTAIN: GLYPH_HELP,
    ValidationStatus.MATCH: GLYPH_CHECK,
}


def get_monospace_font(base_font: QFont) -> QFont:
    """Создает моноширинный шрифт для кодифицированных параметров рейса."""
    font = QFont(base_font)
    font.setFamilies(["Cascadia Mono", "Consolas", "Courier New", "monospace"])
    font.setPointSize(base_font.pointSize())
    return font


class ParameterColumnDelegate(QStyledItemDelegate):
    """Делегат первой колонки («Параметр рейса»): левый 4px маркер и иконка статуса Segoe."""

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QSize:
        """Определяет компактную высоту строки 34px."""
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(size.height(), 34))

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        """Отрисовывает статус-маркер, векторную иконку Segoe и название параметра."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        status = index.data(STATUS_ROLE) or ValidationStatus.MATCH
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")

        rect = option.rect

        # 1. Фоновая заливка ячейки (с учетом селекшена)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, COLOR_SELECTION_BG)
        else:
            bg_color = index.data(Qt.ItemDataRole.BackgroundRole)
            if isinstance(bg_color, QColor):
                painter.fillRect(rect, bg_color)

        # 2. Левый цветной акцентный маркер (4px)
        marker_color = COLOR_MATCH_MARKER
        if status == ValidationStatus.CRITICAL:
            marker_color = COLOR_CRITICAL_MARKER
        elif status == ValidationStatus.WARNING:
            marker_color = COLOR_WARNING_MARKER
        elif status == ValidationStatus.UNCERTAIN:
            marker_color = COLOR_UNCERTAIN_MARKER

        marker_rect = QRect(rect.left(), rect.top(), 4, rect.height())
        painter.fillRect(marker_rect, marker_color)

        # 3. Иконка / глиф статуса (Segoe Fluent Icons с TextAntialiasing)
        glyph = STATUS_GLYPHS.get(status, GLYPH_CHECK)
        glyph_font = get_segoe_font(10)
        painter.setFont(glyph_font)
        painter.setPen(marker_color)

        glyph_rect = QRect(rect.left() + 9, rect.top(), 18, rect.height())
        painter.drawText(glyph_rect, int(Qt.AlignmentFlag.AlignCenter), glyph)

        # 4. Текст названия параметра
        text_font = QFont(option.font)
        text_font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "sans-serif"])
        if status in (ValidationStatus.CRITICAL, ValidationStatus.WARNING):
            text_font.setWeight(QFont.Weight.DemiBold)
            painter.setPen(COLOR_TEXT_PRIMARY)
        elif status == ValidationStatus.MATCH:
            text_font.setWeight(QFont.Weight.Normal)
            painter.setPen(COLOR_MATCH_TEXT)
        else:
            text_font.setWeight(QFont.Weight.Normal)
            painter.setPen(COLOR_UNCERTAIN_TEXT)

        painter.setFont(text_font)
        text_rect = QRect(
            rect.left() + 32,
            rect.top(),
            rect.width() - 36,
            rect.height(),
        )
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            text,
        )

        painter.restore()


class DiffHighlightDelegate(QStyledItemDelegate):
    """Делегат для колонок «Заявка» и «Черновик ЭТрН» с посимвольной diff-подсветкой."""

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QSize:
        """Определяет компактную высоту ячейки."""
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(size.height(), 34))

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        """Отрисовывает значения с акцентным diff-выделением отличающихся токенов."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = option.rect

        # 1. Фон ячейки
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, COLOR_SELECTION_BG)
        else:
            bg_color = index.data(Qt.ItemDataRole.BackgroundRole)
            if isinstance(bg_color, QColor):
                painter.fillRect(rect, bg_color)

        status = index.data(STATUS_ROLE) or ValidationStatus.MATCH
        is_mono = bool(index.data(IS_MONOSPACE_ROLE))
        diff_spans: list[tuple[str, bool]] = index.data(DIFF_HIGHLIGHTS_ROLE) or []
        full_text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")

        # 2. Выбор базового шрифта
        base_font = QFont(option.font)
        if is_mono:
            base_font = get_monospace_font(base_font)
        else:
            base_font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "sans-serif"])

        # Если статус MATCH или UNCERTAIN, или нет diff-срезов — рисуем единым текстом
        if status not in (ValidationStatus.CRITICAL, ValidationStatus.WARNING) or not diff_spans:
            if status == ValidationStatus.MATCH:
                painter.setPen(COLOR_MATCH_TEXT)
            elif status == ValidationStatus.UNCERTAIN:
                painter.setPen(COLOR_UNCERTAIN_TEXT)
            else:
                painter.setPen(COLOR_TEXT_PRIMARY)

            painter.setFont(base_font)
            content_rect = QRect(
                rect.left() + 10,
                rect.top(),
                rect.width() - 20,
                rect.height(),
            )
            painter.drawText(
                content_rect,
                int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                full_text,
            )
            painter.restore()
            return

        # 3. Посимвольный / токенный diff-рендеринг для CRITICAL / WARNING
        diff_bg = COLOR_CRITICAL_BG if status == ValidationStatus.CRITICAL else COLOR_WARNING_BG
        diff_text_color = (
            COLOR_CRITICAL_TEXT if status == ValidationStatus.CRITICAL else COLOR_WARNING_TEXT
        )

        bold_font = QFont(base_font)
        bold_font.setBold(True)

        fm_normal = QFontMetrics(base_font)
        fm_bold = QFontMetrics(bold_font)

        x_cursor = float(rect.left() + 10)
        y_center = rect.top() + rect.height() / 2.0
        max_x = float(rect.right() - 10)

        for chunk, is_diff in diff_spans:
            if not chunk or x_cursor >= max_x:
                continue

            current_fm = fm_bold if is_diff else fm_normal
            chunk_width = float(current_fm.horizontalAdvance(chunk))

            # Если фрагмент не помещается полностью — обрезаем
            if x_cursor + chunk_width > max_x:
                available_width = max_x - x_cursor
                chunk = current_fm.elidedText(
                    chunk, Qt.TextElideMode.ElideRight, int(available_width)
                )
                chunk_width = float(current_fm.horizontalAdvance(chunk))

            # Отрисовка подложки-плашки для отличающихся символов
            if is_diff:
                pill_height = float(current_fm.height() + 2)
                pill_rect = QRectF(
                    x_cursor - 1.0,
                    y_center - (pill_height / 2.0),
                    chunk_width + 2.0,
                    pill_height,
                )
                painter.setBrush(diff_bg)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(pill_rect, 3.0, 3.0)

                painter.setFont(bold_font)
                painter.setPen(diff_text_color)
            else:
                painter.setFont(base_font)
                painter.setPen(COLOR_TEXT_PRIMARY)

            # Отрисовка символов
            text_baseline = y_center + (current_fm.ascent() - current_fm.descent()) / 2.0
            painter.drawText(QPoint(int(x_cursor), int(text_baseline)), chunk)

            x_cursor += chunk_width

        painter.restore()


class ExplanationColumnDelegate(QStyledItemDelegate):
    """Делегат последней колонки («Пояснение / Разница»): Visual Silencing для совпадений."""

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QSize:
        """Определяет компактную высоту ячейки."""
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(size.height(), 34))

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        """Отрисовывает пояснение: для MATCH лаконичный приглушенный прочерк '—'."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = option.rect

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, COLOR_SELECTION_BG)
        else:
            bg_color = index.data(Qt.ItemDataRole.BackgroundRole)
            if isinstance(bg_color, QColor):
                painter.fillRect(rect, bg_color)

        status = index.data(STATUS_ROLE) or ValidationStatus.MATCH
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")

        font = QFont(option.font)
        font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "sans-serif"])
        if status == ValidationStatus.MATCH:
            painter.setPen(COLOR_MATCH_TEXT)
        elif status == ValidationStatus.CRITICAL:
            font.setWeight(QFont.Weight.Medium)
            painter.setPen(COLOR_CRITICAL_TEXT)
        elif status == ValidationStatus.WARNING:
            font.setWeight(QFont.Weight.Medium)
            painter.setPen(COLOR_WARNING_TEXT)
        else:
            painter.setPen(COLOR_UNCERTAIN_TEXT)

        painter.setFont(font)
        text_rect = QRect(rect.left() + 10, rect.top(), rect.width() - 20, rect.height())
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            text,
        )

        painter.restore()
