"""Виджет командной строки сводки и управления проверкой (SummaryBarWidget).

Высота 36px. Плоская системная панель прямо над таблицей:
Слева: прямой текстовый индикатор статуса («✓ Рейс согласован» / «✕ Найдены расхождения»)
По центру: числовые счетчики строк через тонкие разделители
Справа: чекбокс «Только расхождения», меню «Демо-сценарии» и кнопка «Очистить всё»
"""

from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
)

from freight_check.contracts import SessionReport, ValidationStatus
from freight_check.ui.icons import (
    GLYPH_CHECK,
    GLYPH_ERROR,
    GLYPH_HELP,
    GLYPH_PLAY,
    GLYPH_TRASH,
    GLYPH_WARNING,
    create_segoe_icon,
)

# Прямые статусы рейса с векторными иконками Segoe Fluent
STATUS_CONFIG: dict[ValidationStatus, tuple[str, str, str]] = {
    ValidationStatus.MATCH: ("Рейс согласован", "#059669", GLYPH_CHECK),
    ValidationStatus.CRITICAL: ("Найдены расхождения", "#DC2626", GLYPH_ERROR),
    ValidationStatus.WARNING: ("Требуется проверка", "#D97706", GLYPH_WARNING),
    ValidationStatus.UNCERTAIN: ("Сомнительные данные (OCR)", "#64748B", GLYPH_HELP),
}


class SummaryBarWidget(QFrame):
    """Плоская командная строка сводки результатов и управления (36px)."""

    scenario_selected = Signal(str)
    reset_requested = Signal()
    filter_only_diffs_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryBar")
        self.setFixedHeight(48)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.setSpacing(10)

        # 1. Индикатор статуса: векторная иконка Segoe Fluent + чистый текст
        self._status_icon = QLabel(self)
        self._status_icon.setObjectName("summaryStatusIcon")
        self._status_icon.setFixedSize(22, 22)
        self._status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_icon.setStyleSheet("border: none; background: transparent;")
        self._status_icon.setVisible(False)
        layout.addWidget(self._status_icon)

        self._status_badge = QLabel("Ожидание документов", self)
        self._status_badge.setObjectName("summaryStatusText")
        self._status_badge.setStyleSheet(
            "color: #94A3B8; font-size: 12px; font-weight: 600; border: none; background: transparent;"
        )
        layout.addWidget(self._status_badge)

        # Тонкий вертикальный разделитель |
        sep1 = QFrame()
        sep1.setFixedWidth(1)
        sep1.setFixedHeight(18)
        sep1.setStyleSheet("background-color: #CBD5E1;")
        layout.addWidget(sep1)

        # 2. Строгие текстовые метрики через разделитель
        self._critical_label = QLabel("Критических: 0")
        self._critical_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        layout.addWidget(self._critical_label)

        self._warning_label = QLabel("Предупреждений: 0")
        self._warning_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        layout.addWidget(self._warning_label)

        self._match_label = QLabel("Совпадений: 0")
        self._match_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        layout.addWidget(self._match_label)

        layout.addStretch(1)

        # 3. Правая группа контролов: Чекбокс | Меню демо | Очистить всё
        self._only_diffs_cb = QCheckBox("Только расхождения")
        self._only_diffs_cb.setObjectName("onlyDiffsCheckBox")
        self._only_diffs_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self._only_diffs_cb.toggled.connect(self.filter_only_diffs_changed.emit)
        layout.addWidget(self._only_diffs_cb)

        sep2 = QFrame()
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(18)
        sep2.setStyleSheet("background-color: #CBD5E1;")
        layout.addWidget(sep2)

        # Кнопка меню тестовых демо-сценариев
        self._demo_menu_btn = QToolButton(self)
        self._demo_menu_btn.setObjectName("demoMenuBtn")
        self._demo_menu_btn.setText("  Демо-сценарии")
        self._demo_menu_btn.setIcon(
            create_segoe_icon(GLYPH_PLAY, QColor("#334155"), 12, y_offset=0.5)
        )
        self._demo_menu_btn.setIconSize(QSize(12, 12))
        self._demo_menu_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._demo_menu_btn.setToolTip("Выбрать эталонный тестовый сценарий (Ctrl+D)")
        self._demo_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._demo_menu_btn.setFixedHeight(30)
        self._demo_menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._demo_menu_btn)

        # Кнопка сброса сессии
        self._reset_btn = QPushButton("  Очистить всё")
        self._reset_btn.setObjectName("toolbarResetBtn")
        self._reset_btn.setIcon(create_segoe_icon(GLYPH_TRASH, QColor("#64748B"), 12, y_offset=0.5))
        self._reset_btn.setIconSize(QSize(12, 12))
        self._reset_btn.setToolTip("Сбросить сессию и очистить файлы (Ctrl+R)")
        self._reset_btn.setFixedHeight(30)
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self.reset_requested.emit)
        layout.addWidget(self._reset_btn)

    def setup_scenarios(self, scenarios: Iterable[str], callback: Any) -> None:
        """Настраивает выпадающее меню эталонных сценариев."""
        menu = QMenu(self._demo_menu_btn)
        for key in scenarios:
            action = QAction(key, self)
            action.triggered.connect(lambda checked=False, k=key: callback(k))
            menu.addAction(action)
        self._demo_menu_btn.setMenu(menu)

    def show_demo_menu(self) -> None:
        """Открывает меню сценариев по горячей клавише (Ctrl+D)."""
        self._demo_menu_btn.showMenu()

    def set_report(self, report: SessionReport) -> None:
        """Обновляет статус и счетчики по отчету проверки."""
        status = report.overall_status
        if status in STATUS_CONFIG:
            text, color, glyph = STATUS_CONFIG[status]
            icon = create_segoe_icon(glyph, QColor(color), base_size=20)
            self._status_icon.setPixmap(icon.pixmap(QSize(20, 20)))
            self._status_icon.setVisible(True)
            self._status_badge.setText(text)
            self._status_badge.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: 600; border: none; background: transparent;"
            )
        else:
            self._status_icon.clear()
            self._status_icon.setVisible(False)
            self._status_badge.setText("Неизвестный статус")
            self._status_badge.setStyleSheet(
                "color: #64748B; font-size: 12px; font-weight: 600; border: none; background: transparent;"
            )

        critical_count = sum(1 for r in report.rows if r.status == ValidationStatus.CRITICAL)
        warning_count = sum(1 for r in report.rows if r.status == ValidationStatus.WARNING)
        match_count = sum(1 for r in report.rows if r.status == ValidationStatus.MATCH)

        self._critical_label.setText(f"Критических: {critical_count}")
        self._warning_label.setText(f"Предупреждений: {warning_count}")
        self._match_label.setText(f"Совпадений: {match_count}")

        # Подсвечиваем цветным текстом только ненулевые значения
        crit_style = (
            "color: #DC2626; font-size: 12px; font-weight: 600;"
            if critical_count > 0
            else "color: #94A3B8; font-size: 12px; font-weight: 500;"
        )
        warn_style = (
            "color: #D97706; font-size: 12px; font-weight: 600;"
            if warning_count > 0
            else "color: #94A3B8; font-size: 12px; font-weight: 500;"
        )
        match_style = (
            "color: #059669; font-size: 12px; font-weight: 600;"
            if match_count > 0
            else "color: #94A3B8; font-size: 12px; font-weight: 500;"
        )

        self._critical_label.setStyleSheet(crit_style)
        self._warning_label.setStyleSheet(warn_style)
        self._match_label.setStyleSheet(match_style)

        layout = self.layout()
        if layout is not None:
            layout.invalidate()
            layout.activate()

    def reset(self) -> None:
        """Сбрасывает сводку в начальное нейтральное состояние."""
        self._status_icon.clear()
        self._status_icon.setVisible(False)
        self._status_badge.setText("Ожидание документов")
        self._status_badge.setStyleSheet(
            "color: #94A3B8; font-size: 12px; font-weight: 500; border: none; background: transparent;"
        )
        self._critical_label.setText("Критических: 0")
        self._warning_label.setText("Предупреждений: 0")
        self._match_label.setText("Совпадений: 0")

        self._critical_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        self._warning_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        self._match_label.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")

        self._only_diffs_cb.setChecked(False)

        layout = self.layout()
        if layout is not None:
            layout.invalidate()
            layout.activate()

    def is_only_diffs_checked(self) -> bool:
        """Возвращает статус чекбокса 'Только расхождения'."""
        return self._only_diffs_cb.isChecked()

    def set_only_diffs_checked(self, checked: bool) -> None:
        """Устанавливает статус чекбокса 'Только расхождения'."""
        self._only_diffs_cb.setChecked(checked)
