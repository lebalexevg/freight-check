"""Виджет компактной инфо-полосы сводки результатов (SummaryBarWidget).

Высота 36px. Заменяет гигантский баннер и ряд кнопок-таблеток.
Слева отображает лаконичный бейдж статуса и цветные индикаторы-точки счетчиков.
Справа содержит компактный переключатель [☐ Только расхождения].
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from freight_check.contracts import SessionReport, ValidationStatus

# Стили для бейджа итогового статуса рейса
STATUS_BADGE_STYLES: dict[ValidationStatus, str] = {
    ValidationStatus.MATCH: (
        "background-color: #DCFCE7; color: #166534; border: 1px solid #86EFAC; "
        "border-radius: 4px; padding: 0px 8px; font-weight: 700; font-size: 11px;"
    ),
    ValidationStatus.CRITICAL: (
        "background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; "
        "border-radius: 4px; padding: 0px 8px; font-weight: 700; font-size: 11px;"
    ),
    ValidationStatus.WARNING: (
        "background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; "
        "border-radius: 4px; padding: 0px 8px; font-weight: 700; font-size: 11px;"
    ),
    ValidationStatus.UNCERTAIN: (
        "background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; "
        "border-radius: 4px; padding: 0px 8px; font-weight: 700; font-size: 11px;"
    ),
}

STATUS_BADGE_TEXT: dict[ValidationStatus, str] = {
    ValidationStatus.MATCH: "● РЕЙС СОГЛАСОВАН",
    ValidationStatus.CRITICAL: "● КРИТИЧЕСКИЕ РАСХОЖДЕНИЯ",
    ValidationStatus.WARNING: "● ТРЕБУЕТСЯ ПРОВЕРКА",
    ValidationStatus.UNCERTAIN: "● СОМНИТЕЛЬНЫЕ ДАННЫЕ (OCR)",
}


class SummaryBarWidget(QFrame):
    """Компактная гармоничная полоса сводки статуса проверки (40px)."""

    filter_only_diffs_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryBar")
        self.setFixedHeight(40)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(14)

        # 1. Бейдж итогового статуса (24px pill, идеально отцентрированный)
        self._status_badge = QLabel("● ОЖИДАНИЕ ДОКУМЕНТОВ")
        self._status_badge.setFixedHeight(24)
        self._status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_badge.setStyleSheet(
            "background-color: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; "
            "border-radius: 4px; padding: 0px 8px; font-weight: 700; font-size: 11px;"
        )
        layout.addWidget(self._status_badge)

        # Тонкий центрированный разделитель-волосок (16px)
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(16)
        sep.setStyleSheet("background-color: #E2E8F0;")
        layout.addWidget(sep)

        # 2. Компактные индикаторы-точки со счетчиками
        self._critical_label = QLabel("● 0 критических")
        self._critical_label.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 600;")
        layout.addWidget(self._critical_label)

        self._warning_label = QLabel("● 0 предупреждений")
        self._warning_label.setStyleSheet("color: #D97706; font-size: 12px; font-weight: 600;")
        layout.addWidget(self._warning_label)

        self._match_label = QLabel("● 0 совпадений")
        self._match_label.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
        layout.addWidget(self._match_label)

        layout.addStretch(1)

        # 3. Переключатель «Только расхождения»
        self._only_diffs_cb = QCheckBox("Только расхождения")
        self._only_diffs_cb.setObjectName("onlyDiffsCheckBox")
        self._only_diffs_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self._only_diffs_cb.toggled.connect(self.filter_only_diffs_changed.emit)
        layout.addWidget(self._only_diffs_cb)

    def set_report(self, report: SessionReport) -> None:
        """Обновляет итоговый статус и индикаторы-счетчики по отчету сессии."""
        status = report.overall_status
        badge_style = STATUS_BADGE_STYLES.get(
            status, STATUS_BADGE_STYLES[ValidationStatus.UNCERTAIN]
        )
        badge_text = STATUS_BADGE_TEXT.get(status, "● ПРОВЕРЕНО")

        self._status_badge.setText(badge_text)
        self._status_badge.setStyleSheet(badge_style)

        # Точный подсчет строк
        critical_count = sum(1 for r in report.rows if r.status == ValidationStatus.CRITICAL)
        warning_count = sum(1 for r in report.rows if r.status == ValidationStatus.WARNING)
        match_count = sum(1 for r in report.rows if r.status == ValidationStatus.MATCH)

        self._critical_label.setText(f"● {critical_count} критических")
        self._warning_label.setText(f"● {warning_count} предупреждений")
        self._match_label.setText(f"● {match_count} совпадений")

        # Если критических или предупреждений 0 — делаем их приглушенными
        crit_color = "#DC2626" if critical_count > 0 else "#94A3B8"
        warn_color = "#D97706" if warning_count > 0 else "#94A3B8"
        match_color = "#10B981" if match_count > 0 else "#94A3B8"

        self._critical_label.setStyleSheet(
            f"color: {crit_color}; font-size: 12px; font-weight: 600;"
        )
        self._warning_label.setStyleSheet(
            f"color: {warn_color}; font-size: 12px; font-weight: 600;"
        )
        self._match_label.setStyleSheet(f"color: {match_color}; font-size: 12px; font-weight: 600;")

        self.setVisible(True)

    def reset(self) -> None:
        """Сбрасывает сводку в начальное нейтральное состояние."""
        self._status_badge.setText("● ОЖИДАНИЕ ДОКУМЕНТОВ")
        self._status_badge.setStyleSheet(
            "background-color: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; "
            "border-radius: 4px; padding: 0px 8px; font-weight: 700; font-size: 11px;"
        )
        self._critical_label.setText("● 0 критических")
        self._warning_label.setText("● 0 предупреждений")
        self._match_label.setText("● 0 совпадений")

        self._critical_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        self._warning_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        self._match_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")

        self._only_diffs_cb.setChecked(False)

    def is_only_diffs_checked(self) -> bool:
        """Возвращает статус чекбокса 'Только расхождения'."""
        return self._only_diffs_cb.isChecked()

    def set_only_diffs_checked(self, checked: bool) -> None:
        """Устанавливает статус чекбокса 'Только расхождения'."""
        self._only_diffs_cb.setChecked(checked)
