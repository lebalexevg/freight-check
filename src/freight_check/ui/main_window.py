"""Главное окно приложения «Рейс-Проверка» (PySide6)."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from freight_check.contracts import SessionReport, ValidationStatus
from freight_check.ui.diff_table import DiffTableWidget
from freight_check.ui.drop_zone import DropZoneWidget
from freight_check.ui.mock_data import get_all_scenarios
from freight_check.ui.worker import ValidationWorker


def get_stylesheet_path() -> Path:
    """Определяет абсолютный путь к таблице стилей style.qss."""
    # Поиск относительно пакета или корня проекта
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
        self.setWindowTitle("Рейс-Проверка — Автономная кросс-валидация документов")
        self.resize(1140, 840)
        self.setMinimumSize(960, 680)

        self._scenarios = get_all_scenarios()
        self._worker: ValidationWorker | None = None
        self._current_report: SessionReport | None = None

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(20, 16, 20, 20)
        root_layout.setSpacing(16)

        # 1. Шапка (Header) с логотипом и выбором демо-сценариев
        header_frame = self._create_header_frame()
        root_layout.addWidget(header_frame)

        # 2. Область Drag-and-Drop для двух документов
        docs_layout = QHBoxLayout()
        docs_layout.setSpacing(14)

        self._order_drop_zone = DropZoneWidget(
            title="1. Заявка на перевозку",
            subtitle="Перетащите входящую заявку клиента (PDF, Excel, Word, скан)",
        )
        self._order_drop_zone.file_selected.connect(self._on_files_changed)
        self._order_drop_zone.file_cleared.connect(self._on_files_changed)
        docs_layout.addWidget(self._order_drop_zone)

        self._waybill_drop_zone = DropZoneWidget(
            title="2. Черновик ЭТрН / Накладная",
            subtitle="Перетащите проект накладной (XML титул ФНС, скан, PDF)",
        )
        self._waybill_drop_zone.file_selected.connect(self._on_files_changed)
        self._waybill_drop_zone.file_cleared.connect(self._on_files_changed)
        docs_layout.addWidget(self._waybill_drop_zone)

        root_layout.addLayout(docs_layout)

        # 3. Панель действий и статус
        actions_frame = self._create_actions_frame()
        root_layout.addWidget(actions_frame)

        # 4. Карточка сводки (KPI Banner)
        self._kpi_banner = self._create_kpi_banner()
        root_layout.addWidget(self._kpi_banner)
        self._kpi_banner.setVisible(False)

        # 5. Таблица сопоставления расхождений
        self._diff_table = DiffTableWidget()
        root_layout.addWidget(self._diff_table, stretch=1)

    def _create_header_frame(self) -> QFrame:
        """Создает верхнюю панель с заголовком и демо-сценариями."""
        frame = QFrame()
        frame.setObjectName("headerFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # Логотип и подзаголовок
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title_label = QLabel("Рейс-Проверка")
        title_label.setStyleSheet("font-size: 19px; font-weight: 800; color: #0F172A;")
        title_box.addWidget(title_label)

        sub_label = QLabel("Локальный диффчекер: Заявка ↔ Черновик ЭТрН (152-ФЗ Offline)")
        sub_label.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(sub_label)

        layout.addLayout(title_box)
        layout.addStretch(1)

        # Переключатель демо-сценариев
        demo_box = QHBoxLayout()
        demo_box.setSpacing(10)

        demo_label = QLabel("Тестовый сценарий:")
        demo_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        demo_box.addWidget(demo_label)

        self._scenario_combo = QComboBox()
        self._scenario_combo.setMinimumWidth(380)
        self._scenario_combo.setFixedHeight(36)
        for name in self._scenarios:
            self._scenario_combo.addItem(name)
        demo_box.addWidget(self._scenario_combo)

        self._load_demo_button = QPushButton("Загрузить демо")
        self._load_demo_button.setToolTip("Загрузить выбранный сценарий и файлы примеров")
        self._load_demo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_demo_button.setFixedHeight(36)
        self._load_demo_button.clicked.connect(self._on_load_demo_clicked)
        demo_box.addWidget(self._load_demo_button)

        layout.addLayout(demo_box)
        return frame

    def _create_actions_frame(self) -> QFrame:
        """Создает панель управления и индикации прогресса."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        self._start_button = QPushButton("Сверить документы")
        self._start_button.setObjectName("primaryButton")
        self._start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_button.setFixedHeight(38)
        self._start_button.setEnabled(False)
        self._start_button.clicked.connect(self._start_validation)
        button_row.addWidget(self._start_button)

        self._clear_button = QPushButton("Очистить все")
        self._clear_button.setObjectName("secondaryButton")
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.setFixedHeight(38)
        self._clear_button.clicked.connect(self._reset_all)
        button_row.addWidget(self._clear_button)

        button_row.addStretch(1)

        self._status_label = QLabel("Прикрепите документы или выберите демо-сценарий")
        self._status_label.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 500;")
        button_row.addWidget(self._status_label)

        layout.addLayout(button_row)

        # Тонкий прогресс-бар
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        return frame

    def _create_kpi_banner(self) -> QFrame:
        """Создает карточку сводки результатов валидации."""
        self._banner_frame = QFrame()
        self._banner_frame.setObjectName("statusBanner_MATCH")
        layout = QHBoxLayout(self._banner_frame)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(24)

        # Итоговый статус (крупная надпись)
        self._kpi_title_label = QLabel("РЕЙС СОГЛАСОВАН")
        self._kpi_title_label.setStyleSheet("font-size: 16px; font-weight: 800;")
        layout.addWidget(self._kpi_title_label, stretch=1)

        # Блоки метрик
        self._kpi_critical_label = QLabel("Ошибок: 0")
        self._kpi_critical_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #B91C1C;")
        layout.addWidget(self._kpi_critical_label)

        self._kpi_warning_label = QLabel("Предупреждений: 0")
        self._kpi_warning_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #B45309;")
        layout.addWidget(self._kpi_warning_label)

        self._kpi_time_label = QLabel("Время: 0 мс")
        self._kpi_time_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")
        layout.addWidget(self._kpi_time_label)

        return self._banner_frame

    def _apply_styles(self) -> None:
        """Загружает стили из style.qss."""
        style_path = get_stylesheet_path()
        if style_path.exists():
            with open(style_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _on_files_changed(self) -> None:
        """Проверяет наличие файлов и активирует кнопку проверки."""
        has_order = self._order_drop_zone.has_file()
        has_waybill = self._waybill_drop_zone.has_file()

        if has_order and has_waybill:
            self._start_button.setEnabled(True)
            self._status_label.setText("Документы готовы к сверке")
        elif has_order or has_waybill:
            self._start_button.setEnabled(False)
            self._status_label.setText("Загрузите второй документ для запуска валидации")
        else:
            self._start_button.setEnabled(False)
            self._status_label.setText("Прикрепите документы или выберите демо-сценарий")

    def _on_load_demo_clicked(self) -> None:
        """Загружает выбранный тестовый сценарий."""
        selected_scenario = self._scenario_combo.currentText()

        # Имитируем подстановку файлов
        self._order_drop_zone.set_file("Заявка_на_перевозку_№452.pdf")
        self._waybill_drop_zone.set_file("Черновик_ЭТрН_№452_Титул1.xml")

        self._status_label.setText(f"Загружен тестовый набор: {selected_scenario}")
        self._start_button.setEnabled(True)

        # Автоматический запуск проверки сценария
        self._start_validation()

    def _start_validation(self) -> None:
        """Запускает асинхронный процесс валидации в фоновом QThread."""
        order_path = self._order_drop_zone.get_file_path() or "mock_order.pdf"
        waybill_path = self._waybill_drop_zone.get_file_path() or "mock_waybill.xml"
        selected_scenario = self._scenario_combo.currentText()

        # Блокировка интерфейса на время проверки
        self._start_button.setEnabled(False)
        self._load_demo_button.setEnabled(False)
        self._clear_button.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(5)
        self._status_label.setText("Запуск конвейера проверки...")

        # Инициализация и старт воркера
        self._worker = ValidationWorker(
            order_path=order_path,
            waybill_path=waybill_path,
            scenario_key=selected_scenario,
        )
        self._worker.progress_changed.connect(self._on_worker_progress)
        self._worker.validation_finished.connect(self._on_worker_finished)
        self._worker.validation_failed.connect(self._on_worker_failed)
        self._worker.start()

    def _on_worker_progress(self, percent: int, stage_text: str) -> None:
        """Обновление прогресс-бара и текстового статуса."""
        self._progress_bar.setValue(percent)
        self._status_label.setText(stage_text)

    def _on_worker_finished(self, report: SessionReport) -> None:
        """Обработка успешного завершения валидации."""
        self._current_report = report
        self._progress_bar.setVisible(False)
        self._start_button.setEnabled(True)
        self._load_demo_button.setEnabled(True)
        self._clear_button.setEnabled(True)

        # Обновление баннера сводки
        self._update_kpi_banner(report)

        # Заполнение таблицы расхождений
        self._diff_table.set_rows(report.rows)

        self._status_label.setText(
            f"Валидация завершена за {report.processing_time_ms} мс. "
            f"Проверено реквизитов: {len(report.rows)}"
        )

    def _on_worker_failed(self, error_message: str) -> None:
        """Обработка ошибок воркера."""
        self._progress_bar.setVisible(False)
        self._start_button.setEnabled(True)
        self._load_demo_button.setEnabled(True)
        self._clear_button.setEnabled(True)
        self._status_label.setText("Ошибка при проверке документов")

        QMessageBox.critical(self, "Ошибка валидации", error_message)

    def _update_kpi_banner(self, report: SessionReport) -> None:
        """Обновляет внешний вид и данные карточки сводки."""
        self._banner_frame.setObjectName(f"statusBanner_{report.overall_status.value}")
        self._banner_frame.style().unpolish(self._banner_frame)
        self._banner_frame.style().polish(self._banner_frame)

        if report.overall_status == ValidationStatus.MATCH:
            self._kpi_title_label.setText("РЕЙС СОГЛАСОВАН: Все реквизиты совпадают")
            self._kpi_title_label.setStyleSheet(
                "font-size: 15px; font-weight: 800; color: #166534;"
            )
        elif report.overall_status == ValidationStatus.CRITICAL:
            self._kpi_title_label.setText("ВНИМАНИЕ: Обнаружены критические расхождения!")
            self._kpi_title_label.setStyleSheet(
                "font-size: 15px; font-weight: 800; color: #991B1B;"
            )
        elif report.overall_status == ValidationStatus.WARNING:
            self._kpi_title_label.setText("ТРЕБУЕТСЯ ПРОВЕРКА: Имеются некритические расхождения")
            self._kpi_title_label.setStyleSheet(
                "font-size: 15px; font-weight: 800; color: #92400E;"
            )
        else:
            self._kpi_title_label.setText(
                "СОМНИТЕЛЬНЫЕ ДАННЫЕ: Низкая уверенность распознавания OCR"
            )
            self._kpi_title_label.setStyleSheet(
                "font-size: 15px; font-weight: 800; color: #334155;"
            )

        self._kpi_critical_label.setText(f"Критических: {report.critical_errors_count}")
        self._kpi_warning_label.setText(f"Предупреждений: {report.warnings_count}")
        self._kpi_time_label.setText(f"Время: {report.processing_time_ms} мс")

        self._kpi_banner.setVisible(True)

    def _reset_all(self) -> None:
        """Полный сброс состояния интерфейса."""
        self._order_drop_zone.clear_file()
        self._waybill_drop_zone.clear_file()
        self._diff_table.clear()
        self._kpi_banner.setVisible(False)
        self._progress_bar.setVisible(False)
        self._start_button.setEnabled(False)
        self._current_report = None
        self._status_label.setText("Прикрепите документы или выберите демо-сценарий")
