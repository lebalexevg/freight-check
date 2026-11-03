"""Главное окно приложения «Рейс-Проверка» (PySide6) в концепции «Инженерный минимализм».

Организовано в плоскую компоновку системного уровня:
1. Заголовок окна ОС: «Рейс-Проверка — Кросс-валидация документов».
2. Адаптивная сплит-панель документов (Empty State vs Loaded State 36px):
   префиксы «Заявка:» / «ЭТрН:», плоские компактные кнопки управления.
3. Командная строка сводки (36px): текстовый индикатор согласованности,
   числовые метрики через «|», чекбокс «Только расхождения», меню «Демо-сценарии» и «Очистить всё».
4. Таблица сопоставления QTableView: динамическое растягивание колонок документов (50/50),
   посимвольная diff-подсветка, double-click copy, elided-текст и тултипы.
5. Системный статус-бар: уведомления копирования, тонкий прогресс-бар и метрики производительности.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from freight_check.contracts import SessionReport
from freight_check.ui.about_dialog import APP_VERSION, AboutDialog
from freight_check.ui.diff_table import DiffTableWidget
from freight_check.ui.drop_zone import DocumentSlotsWidget, DropZoneWidget
from freight_check.ui.icons import get_app_icon
from freight_check.ui.mock_data import get_all_scenarios
from freight_check.ui.summary_bar import SummaryBarWidget
from freight_check.ui.worker import ValidationWorker


def get_stylesheet_path() -> Path:
    """Определяет абсолютный путь к таблице стилей style.qss."""
    current_file = Path(__file__).resolve()
    # ../../../assets/styles/style.qss
    project_root = current_file.parents[3]
    candidate = project_root / "assets" / "styles" / "style.qss"
    if candidate.exists():
        return candidate
    return Path("assets/styles/style.qss")


class MainWindow(QMainWindow):
    """Главное окно приложения «Рейс-Проверка»."""

    def __init__(self) -> None:
        super().__init__()
        app_icon = get_app_icon()
        self.setWindowIcon(app_icon)
        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            app.setApplicationDisplayName("")
            app.setWindowIcon(app_icon)
        self.setWindowTitle("Рейс-Проверка — Кросс-валидация документов")
        self.resize(1140, 840)
        self.setMinimumSize(960, 640)

        self._scenarios = get_all_scenarios()
        self._worker: ValidationWorker | None = None
        self._current_report: SessionReport | None = None
        self._selected_scenario_key: str | None = None
        self._status_restore_timer = QTimer(self)
        self._status_restore_timer.setSingleShot(True)
        self._status_restore_timer.timeout.connect(self._restore_status_text)
        self._saved_status_text: str | None = None

        self._setup_ui()
        self._apply_styles()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 14)
        root_layout.setSpacing(12)

        # 1. Плоская командная строка сводки и управления (48px, всегда видна вверху)
        self._summary_bar = SummaryBarWidget(self)
        self._summary_bar.setup_scenarios(self._scenarios, self._on_scenario_selected)
        self._summary_bar.reset_requested.connect(self._reset_all)
        self._summary_bar.filter_only_diffs_changed.connect(self._diff_table_filter_changed)
        self._summary_bar.about_requested.connect(self._show_about_dialog)
        root_layout.addWidget(self._summary_bar)

        # 2. Адаптивная сплит-панель документов (Empty State во весь экран vs Loaded State 48px)
        self._doc_slots = DocumentSlotsWidget(self)
        self._doc_slots.files_ready.connect(self._on_files_ready)
        self._doc_slots.files_changed.connect(self._on_files_changed)
        root_layout.addWidget(self._doc_slots, stretch=1)

        # 3. Таблица сопоставления расхождений (~80% высоты окна при загрузке)
        self._diff_table = DiffTableWidget(self)
        self._diff_table.value_copied.connect(self._on_value_copied)
        self._diff_table.setVisible(False)
        root_layout.addWidget(self._diff_table, stretch=0)

        # 4. Системный статус-бар
        self._setup_status_bar()

    def _create_status_sep(self) -> QFrame:
        """Создает тонкий 1px разделитель статус-бара без утолщения шрифта."""
        status_bar = self.statusBar()
        sep = QFrame(status_bar if status_bar is not None else self)
        sep.setObjectName("statusSep")
        sep.setFrameShape(QFrame.Shape.NoFrame)
        sep.setFixedWidth(1)
        sep.setFixedHeight(14)
        sep.setStyleSheet("background-color: #CBD5E1; border: none;")
        return sep

    def _setup_status_bar(self) -> None:
        """Настраивает системный статус-бар с центрированным прогресс-баром и едиными 1px разделителями."""
        status_bar = self.statusBar()
        if status_bar is None:
            return

        status_bar.setSizeGripEnabled(False)
        status_bar.setFixedHeight(30)
        status_bar.setContentsMargins(16, 0, 16, 0)

        # 1. Левый информационный текст с чистым позиционированием
        self._status_text = QLabel(
            "Прикрепите документы или выберите демо-сценарий (Ctrl+D)", status_bar
        )
        self._status_text.setStyleSheet("color: #64748B; font-size: 12px;")
        self._status_text.setContentsMargins(0, 0, 0, 0)
        status_bar.addWidget(self._status_text, stretch=1)

        # 2. Индикатор загрузки строго по центру статус-бара (удлинен до 280px, высота 6px)
        self._progress_bar = QProgressBar(status_bar)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setFixedWidth(280)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)

        # Отслеживание геометрии статус-бара для абсолютного центрирования прогресс-бара
        status_bar.installEventFilter(self)

        # 3. Правый блок метрик с симметричными 1px разделителями
        self._metrics_checked_label = QLabel("Проверено: 0", status_bar)
        self._metrics_checked_label.setObjectName("metricsCheckedLabel")
        self._metrics_checked_label.setStyleSheet(
            "color: #64748B; font-size: 12px; font-weight: 500;"
        )
        self._metrics_checked_label.setContentsMargins(0, 0, 0, 0)
        status_bar.addPermanentWidget(self._metrics_checked_label)

        sep1 = self._create_status_sep()
        status_bar.addPermanentWidget(sep1)

        self._metrics_time_label = QLabel("Время: 0 мс", status_bar)
        self._metrics_time_label.setObjectName("metricsTimeLabel")
        self._metrics_time_label.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        self._metrics_time_label.setContentsMargins(0, 0, 0, 0)
        status_bar.addPermanentWidget(self._metrics_time_label)

        sep2 = self._create_status_sep()
        status_bar.addPermanentWidget(sep2)

        # Кликабельная кнопка версии для вызова окна «О программе»
        self._version_btn = QPushButton(f"v{APP_VERSION}", status_bar)
        self._version_btn.setObjectName("statusVersionBtn")
        self._version_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._version_btn.setToolTip("О программе и справка (F1)")
        self._version_btn.clicked.connect(self._show_about_dialog)
        status_bar.addPermanentWidget(self._version_btn)

    def _setup_shortcuts(self) -> None:
        """Настраивает глобальные горячие клавиши интерфейса."""
        # Ctrl+D: открыть меню демо-сценариев в командной строке сводки
        self._demo_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self._demo_shortcut.activated.connect(self._summary_bar.show_demo_menu)

        # Ctrl+R: сбросить всё
        self._reset_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self._reset_shortcut.activated.connect(self._reset_all)

        # F1: открыть окно «О программе»
        self._about_shortcut = QShortcut(QKeySequence("F1"), self)
        self._about_shortcut.activated.connect(self._show_about_dialog)

    def _apply_styles(self) -> None:
        """Загружает стили из style.qss."""
        style_path = get_stylesheet_path()
        if style_path.exists():
            with open(style_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _update_view_state(self) -> None:
        """Переключает видимость и растягивание виджетов между Empty и Loaded состояниями."""
        has_both = self._doc_slots.has_both_files()
        central = self.centralWidget()
        if central and central.layout():
            layout = central.layout()
            if isinstance(layout, QVBoxLayout):
                if has_both:
                    layout.setStretchFactor(self._doc_slots, 0)
                    layout.setStretchFactor(self._diff_table, 1)
                else:
                    layout.setStretchFactor(self._doc_slots, 1)
                    layout.setStretchFactor(self._diff_table, 0)
        self._diff_table.setVisible(has_both)

    def _on_files_ready(self, order_path: str, waybill_path: str) -> None:
        """Автоматический запуск сверки при наличии обоих документов (Zero-Click)."""
        self._start_validation(order_path, waybill_path)

    def _on_files_changed(self) -> None:
        """Обработка изменения файлов в слотах."""
        self._update_view_state()
        if not self._doc_slots.has_both_files():
            self._summary_bar.reset()
            self._diff_table.clear()
            has_order = self._doc_slots.get_order_path() is not None
            has_waybill = self._doc_slots.get_waybill_path() is not None
            if has_order and not has_waybill:
                self._status_text.setText(
                    "Прикрепите черновик ЭТрН / накладную для запуска валидации"
                )
            elif has_waybill and not has_order:
                self._status_text.setText("Прикрепите заявку на перевозку для запуска валидации")
            else:
                self._status_text.setText(
                    "Прикрепите документы или выберите демо-сценарий (Ctrl+D)"
                )

    def _on_scenario_selected(self, scenario_key: str) -> None:
        """Загружает выбранный тестовый сценарий и автоматически запускает сверку."""
        self._selected_scenario_key = scenario_key
        # Подставляем моковые файлы в слоты
        self._doc_slots.set_files(
            "Заявка_на_перевозку_№452.pdf",
            "Черновик_ЭТрН_№452_Титул1.xml",
        )
        self._status_text.setText(f"Загружен тестовый сценарий: {scenario_key}")

    def _start_validation(
        self,
        order_path: str | None = None,
        waybill_path: str | None = None,
    ) -> None:
        """Запускает асинхронную валидацию документов в фоновом QThread."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(1000)

        resolved_order = order_path or self._doc_slots.get_order_path() or "order.pdf"
        resolved_waybill = waybill_path or self._doc_slots.get_waybill_path() or "waybill.xml"

        # Индикация запуска
        self._progress_bar.setVisible(True)
        self._reposition_progress_bar()
        self._progress_bar.setValue(10)
        self._status_text.setText("Сверка документов в фоновом конвейере...")

        self._worker = ValidationWorker(
            order_path=resolved_order,
            waybill_path=resolved_waybill,
            scenario_key=self._selected_scenario_key,
        )
        self._worker.progress_changed.connect(self._on_worker_progress)
        self._worker.validation_finished.connect(self._on_worker_finished)
        self._worker.validation_failed.connect(self._on_worker_failed)
        self._worker.start()

    def _on_worker_progress(self, percent: int, stage_text: str) -> None:
        """Обновление шкалы прогресса и статусной строки."""
        self._progress_bar.setValue(percent)
        self._status_text.setText(stage_text)

    def _on_worker_finished(self, report: SessionReport) -> None:
        """Успешное завершение валидации документов."""
        self._current_report = report
        self._progress_bar.setVisible(False)

        # Обновление 36px инфо-полосы сводки
        self._summary_bar.set_report(report)

        # Обновление таблицы MVC
        self._diff_table.set_rows(report.rows)

        # Обновление статус-бара
        self._metrics_checked_label.setText(f"Проверено: {len(report.rows)}")
        self._metrics_time_label.setText(f"Время: {report.processing_time_ms} мс")
        self._status_text.setText("Валидация успешно завершена")

    def _on_worker_failed(self, error_message: str) -> None:
        """Обработка ошибок конвейера валидации."""
        self._progress_bar.setVisible(False)
        self._status_text.setText("Ошибка при валидации документов")
        QMessageBox.critical(self, "Ошибка сверки", error_message)

    def _diff_table_filter_changed(self, hide_matches: bool) -> None:
        """Переключение фильтрации 'Только расхождения' в таблице."""
        self._diff_table.set_hide_matches(hide_matches)

    def _show_temporary_status(self, message: str, timeout_ms: int = 3000) -> None:
        """Отображает временное уведомление в основном лейбле статус-бара с сохранением отступа."""
        if self._status_restore_timer.isActive():
            self._status_restore_timer.stop()
        elif self._saved_status_text is None:
            self._saved_status_text = self._status_text.text()

        self._status_text.setText(message)
        self._status_restore_timer.start(timeout_ms)

    def _restore_status_text(self) -> None:
        """Восстанавливает исходный текст статус-бара после временного уведомления."""
        if self._saved_status_text is not None:
            self._status_text.setText(self._saved_status_text)
            self._saved_status_text = None

    def _on_value_copied(self, text: str) -> None:
        """Отображает временное уведомление в статус-баре при копировании реквизита с сохранением отступа."""
        self._show_temporary_status(f"Скопировано в буфер: «{text}»", 3000)

    def _reposition_progress_bar(self) -> None:
        """Центрирует прогресс-бар строго по горизонтальной оси окна и статус-бара."""
        status_bar = self.statusBar()
        if status_bar is None or not hasattr(self, "_progress_bar"):
            return
        bar_w = self._progress_bar.width()
        bar_h = self._progress_bar.height()
        x = (status_bar.width() - bar_w) // 2
        y = (status_bar.height() - bar_h) // 2
        self._progress_bar.setGeometry(x, y, bar_w, bar_h)
        self._progress_bar.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_progress_bar()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            hasattr(self, "_progress_bar")
            and watched == self.statusBar()
            and event.type() in (QEvent.Type.Resize, QEvent.Type.Show)
        ):
            self._reposition_progress_bar()
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Безопасное завершение фоновых потоков при закрытии окна."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(2000)
        super().closeEvent(event)

    def _show_about_dialog(self) -> None:
        """Открывает модальное информационное окно «О программе»."""
        dialog = AboutDialog(self)
        dialog.exec()

    def _reset_all(self) -> None:
        """Полный сброс состояния интерфейса."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(1000)

        self._doc_slots.clear_all()
        self._summary_bar.reset()
        self._diff_table.clear()
        self._update_view_state()
        self._progress_bar.setVisible(False)
        self._current_report = None
        self._selected_scenario_key = None
        self._metrics_checked_label.setText("Проверено: 0")
        self._metrics_time_label.setText("Время: 0 мс")
        self._status_text.setText("Прикрепите документы или выберите демо-сценарий (Ctrl+D)")

    @property
    def _metrics_label(self) -> QLabel:
        return self._metrics_checked_label

    # Свойства обратной совместимости
    @property
    def _demo_menu_btn(self) -> QToolButton:
        return self._summary_bar._demo_menu_btn

    @property
    def _reset_btn(self) -> QPushButton:
        return self._summary_bar._reset_btn

    @property
    def _about_btn(self) -> QPushButton:
        return self._summary_bar._about_btn

    @property
    def _only_diffs_cb(self) -> QCheckBox:
        return self._summary_bar._only_diffs_cb

    @property
    def _order_drop_zone(self) -> DropZoneWidget:
        return self._doc_slots._order_slot

    @property
    def _waybill_drop_zone(self) -> DropZoneWidget:
        return self._doc_slots._waybill_slot

    @property
    def _kpi_banner(self) -> QWidget:
        return self._summary_bar
