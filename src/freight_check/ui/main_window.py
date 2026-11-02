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

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
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
from freight_check.ui.diff_table import DiffTableWidget
from freight_check.ui.drop_zone import DocumentSlotsWidget, DropZoneWidget
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
        self.setWindowTitle("Рейс-Проверка — Кросс-валидация документов")
        self.resize(1140, 840)
        self.setMinimumSize(960, 640)

        self._scenarios = get_all_scenarios()
        self._worker: ValidationWorker | None = None
        self._current_report: SessionReport | None = None
        self._selected_scenario_key: str | None = None

        self._setup_ui()
        self._apply_styles()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(10)

        # 1. Адаптивная сплит-панель документов (Empty State vs Loaded State 36px)
        self._doc_slots = DocumentSlotsWidget(self)
        self._doc_slots.files_ready.connect(self._on_files_ready)
        self._doc_slots.files_changed.connect(self._on_files_changed)
        root_layout.addWidget(self._doc_slots)

        # 2. Плоская командная строка сводки и управления (36px, всегда видна)
        self._summary_bar = SummaryBarWidget(self)
        self._summary_bar.setup_scenarios(self._scenarios, self._on_scenario_selected)
        self._summary_bar.reset_requested.connect(self._reset_all)
        self._summary_bar.filter_only_diffs_changed.connect(self._diff_table_filter_changed)
        root_layout.addWidget(self._summary_bar)

        # 3. Таблица сопоставления расхождений (~80% высоты окна)
        self._diff_table = DiffTableWidget(self)
        self._diff_table.value_copied.connect(self._on_value_copied)
        root_layout.addWidget(self._diff_table, stretch=1)

        # 4. Системный статус-бар
        self._setup_status_bar()

    def _setup_status_bar(self) -> None:
        """Настраивает системный статус-бар со строго симметричными отступами."""
        status_bar = self.statusBar()
        if status_bar is None:
            return

        status_bar.setSizeGripEnabled(False)
        status_bar.setFixedHeight(28)
        status_bar.setContentsMargins(14, 0, 14, 0)

        # Левый информационный текст с чистым позиционированием
        self._status_text = QLabel("Прикрепите документы или выберите демо-сценарий (Ctrl+D)")
        self._status_text.setStyleSheet("color: #64748B; font-size: 11px;")
        self._status_text.setContentsMargins(0, 0, 0, 0)
        status_bar.addWidget(self._status_text, stretch=1)

        # Встроенный ультратонкий прогресс-бар
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setFixedWidth(140)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)
        status_bar.addPermanentWidget(self._progress_bar)

        # Правый блок метрик с симметричным 14px отступом от границы окна
        self._metrics_label = QLabel("Проверено: 0  │  Время: 0 мс")
        self._metrics_label.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500;")
        self._metrics_label.setContentsMargins(0, 0, 0, 0)
        status_bar.addPermanentWidget(self._metrics_label)

    def _setup_shortcuts(self) -> None:
        """Настраивает глобальные горячие клавиши интерфейса."""
        # Ctrl+D: открыть меню демо-сценариев в командной строке сводки
        self._demo_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self._demo_shortcut.activated.connect(self._summary_bar.show_demo_menu)

        # Ctrl+R: сбросить всё
        self._reset_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self._reset_shortcut.activated.connect(self._reset_all)

    def _apply_styles(self) -> None:
        """Загружает стили из style.qss."""
        style_path = get_stylesheet_path()
        if style_path.exists():
            with open(style_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _on_files_ready(self, order_path: str, waybill_path: str) -> None:
        """Автоматический запуск сверки при наличии обоих документов (Zero-Click)."""
        self._start_validation(order_path, waybill_path)

    def _on_files_changed(self) -> None:
        """Обработка изменения файлов в слотах."""
        if not self._doc_slots.has_both_files():
            self._summary_bar.reset()
            self._diff_table.clear()
            self._status_text.setText("Прикрепите второй документ для запуска валидации")

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
        self._metrics_label.setText(
            f"Проверено: {len(report.rows)}  │  Время: {report.processing_time_ms} мс"
        )
        self._status_text.setText("Валидация успешно завершена")

    def _on_worker_failed(self, error_message: str) -> None:
        """Обработка ошибок конвейера валидации."""
        self._progress_bar.setVisible(False)
        self._status_text.setText("Ошибка при валидации документов")
        QMessageBox.critical(self, "Ошибка сверки", error_message)

    def _diff_table_filter_changed(self, hide_matches: bool) -> None:
        """Переключение фильтрации 'Только расхождения' в таблице."""
        self._diff_table.set_hide_matches(hide_matches)

    def _on_value_copied(self, text: str) -> None:
        """Отображает временное уведомление в статус-баре при копировании реквизита."""
        status_bar = self.statusBar()
        if status_bar:
            status_bar.showMessage(f"Скопировано в буфер: «{text}»", 3000)

    def _reset_all(self) -> None:
        """Полный сброс состояния интерфейса."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(1000)

        self._doc_slots.clear_all()
        self._summary_bar.reset()
        self._diff_table.clear()
        self._progress_bar.setVisible(False)
        self._current_report = None
        self._selected_scenario_key = None
        self._metrics_label.setText("Проверено: 0  │  Время: 0 мс")
        self._status_text.setText("Прикрепите документы или выберите демо-сценарий (Ctrl+D)")

    # Свойства обратной совместимости
    @property
    def _demo_menu_btn(self) -> QToolButton:
        return self._summary_bar._demo_menu_btn

    @property
    def _reset_btn(self) -> QPushButton:
        return self._summary_bar._reset_btn

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
