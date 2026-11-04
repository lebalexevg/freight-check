"""Панель сводки результатов и управления проверкой."""

import contextlib
from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
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

# Конфигурация отображения статусов
STATUS_CONFIG: dict[ValidationStatus, tuple[str, str, str]] = {
    ValidationStatus.MATCH: ("Рейс согласован", "#059669", GLYPH_CHECK),
    ValidationStatus.CRITICAL: ("Найдены расхождения", "#DC2626", GLYPH_ERROR),
    ValidationStatus.WARNING: ("Требуется проверка", "#D97706", GLYPH_WARNING),
    ValidationStatus.UNCERTAIN: ("Сомнительные данные (OCR)", "#64748B", GLYPH_HELP),
}


class SummaryBarWidget(QFrame):
    """Панель сводки результатов и управления проверкой."""

    scenario_selected = Signal(str)
    reset_requested = Signal()
    filter_only_diffs_changed = Signal(bool)
    about_requested = Signal()

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

        # Индикатор статуса
        self._status_icon = QLabel(self)
        self._status_icon.setObjectName("summaryStatusIcon")
        self._status_icon.setFixedSize(22, 22)
        self._status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_icon.setVisible(False)
        layout.addWidget(self._status_icon)

        self._status_badge = QLabel("Ожидание документов", self)
        self._status_badge.setObjectName("summaryStatusText")
        self._status_badge.setProperty("status", "idle")
        layout.addWidget(self._status_badge)

        # Разделитель
        sep1 = QFrame(self)
        sep1.setObjectName("summarySep")
        sep1.setFixedWidth(1)
        sep1.setFixedHeight(18)
        layout.addWidget(sep1)

        # Счетчики результатов
        self._critical_label = QLabel("Критических: 0", self)
        self._critical_label.setObjectName("critCountLabel")
        self._critical_label.setProperty("hasValue", "false")
        layout.addWidget(self._critical_label)

        self._warning_label = QLabel("Предупреждений: 0", self)
        self._warning_label.setObjectName("warnCountLabel")
        self._warning_label.setProperty("hasValue", "false")
        layout.addWidget(self._warning_label)

        self._match_label = QLabel("Совпадений: 0", self)
        self._match_label.setObjectName("matchCountLabel")
        self._match_label.setProperty("hasValue", "false")
        layout.addWidget(self._match_label)

        layout.addStretch(1)

        # Кнопки управления
        self._only_diffs_cb = QCheckBox("Только расхождения", self)
        self._only_diffs_cb.setObjectName("onlyDiffsCheckBox")
        self._only_diffs_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self._only_diffs_cb.toggled.connect(self.filter_only_diffs_changed.emit)
        layout.addWidget(self._only_diffs_cb)

        sep2 = QFrame(self)
        sep2.setObjectName("summarySep")
        sep2.setFixedWidth(1)
        sep2.setFixedHeight(18)
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
        self._reset_btn = QPushButton("  Очистить всё", self)
        self._reset_btn.setObjectName("toolbarResetBtn")
        self._reset_btn.setIcon(create_segoe_icon(GLYPH_TRASH, QColor("#64748B"), 12, y_offset=0.5))
        self._reset_btn.setIconSize(QSize(12, 12))
        self._reset_btn.setToolTip("Сбросить сессию и очистить файлы (Ctrl+R)")
        self._reset_btn.setFixedHeight(30)
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self.reset_requested.emit)
        layout.addWidget(self._reset_btn)

        # Кнопка сведений о программе
        self._about_btn = QPushButton(self)
        self._about_btn.setObjectName("toolbarHelpBtn")
        self._about_btn.setIcon(create_segoe_icon(GLYPH_HELP, QColor("#475569"), 13, y_offset=0.5))
        self._about_btn.setIconSize(QSize(13, 13))
        self._about_btn.setToolTip("О программе и справка (F1)")
        self._about_btn.setFixedHeight(30)
        self._about_btn.setFixedWidth(30)
        self._about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._about_btn.clicked.connect(self.about_requested.emit)
        layout.addWidget(self._about_btn)

    @property
    def reset_button(self) -> QPushButton:
        """Кнопка сброса сессии."""
        return self._reset_btn

    @property
    def demo_button(self) -> QToolButton:
        """Кнопка меню демо-сценариев."""
        return self._demo_menu_btn

    @property
    def about_button(self) -> QPushButton:
        """Кнопка вызова окна «О программе»."""
        return self._about_btn

    @property
    def only_diffs_checkbox(self) -> QCheckBox:
        """Чекбокс фильтрации только расхождений."""
        return self._only_diffs_cb

    def setup_scenarios(self, scenarios: Iterable[str], callback: Any) -> None:
        """Настраивает выпадающее меню эталонных сценариев без накопления QAction."""
        menu = self._demo_menu_btn.menu()
        if menu is None:
            menu = QMenu(self._demo_menu_btn)
            self._demo_menu_btn.setMenu(menu)
        else:
            menu.clear()
            with contextlib.suppress(RuntimeError, TypeError):
                menu.triggered.disconnect()

        for key in scenarios:
            action = menu.addAction(key)
            action.setData(key)

        menu.triggered.connect(lambda action: callback(str(action.data())))

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
            status_val = status.value.lower()
            self._status_badge.setProperty("status", status_val)
        else:
            self._status_icon.clear()
            self._status_icon.setVisible(False)
            self._status_badge.setText("Неизвестный статус")
            self._status_badge.setProperty("status", "idle")

        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)

        critical_count = sum(1 for r in report.rows if r.status == ValidationStatus.CRITICAL)
        warning_count = sum(1 for r in report.rows if r.status == ValidationStatus.WARNING)
        match_count = sum(1 for r in report.rows if r.status == ValidationStatus.MATCH)

        self._critical_label.setText(f"Критических: {critical_count}")
        self._warning_label.setText(f"Предупреждений: {warning_count}")
        self._match_label.setText(f"Совпадений: {match_count}")

        # Обновление динамических свойств
        self._critical_label.setProperty("hasValue", "true" if critical_count > 0 else "false")
        self._critical_label.style().unpolish(self._critical_label)
        self._critical_label.style().polish(self._critical_label)

        self._warning_label.setProperty("hasValue", "true" if warning_count > 0 else "false")
        self._warning_label.style().unpolish(self._warning_label)
        self._warning_label.style().polish(self._warning_label)

        self._match_label.setProperty("hasValue", "true" if match_count > 0 else "false")
        self._match_label.style().unpolish(self._match_label)
        self._match_label.style().polish(self._match_label)

        layout = self.layout()
        if layout is not None:
            layout.invalidate()
            layout.activate()

    def reset(self) -> None:
        """Сбрасывает сводку в начальное нейтральное состояние."""
        self._status_icon.clear()
        self._status_icon.setVisible(False)
        self._status_badge.setText("Ожидание документов")
        self._status_badge.setProperty("status", "idle")
        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)

        self._critical_label.setText("Критических: 0")
        self._warning_label.setText("Предупреждений: 0")
        self._match_label.setText("Совпадений: 0")

        self._critical_label.setProperty("hasValue", "false")
        self._critical_label.style().unpolish(self._critical_label)
        self._critical_label.style().polish(self._critical_label)

        self._warning_label.setProperty("hasValue", "false")
        self._warning_label.style().unpolish(self._warning_label)
        self._warning_label.style().polish(self._warning_label)

        self._match_label.setProperty("hasValue", "false")
        self._match_label.style().unpolish(self._match_label)
        self._match_label.style().polish(self._match_label)

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
