"""Виджет таблицы расхождений реквизитов (Diff Table)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from freight_check.contracts import ValidationRow, ValidationStatus

STATUS_LABELS: dict[ValidationStatus, str] = {
    ValidationStatus.MATCH: "Совпадение",
    ValidationStatus.CRITICAL: "Критично",
    ValidationStatus.WARNING: "Внимание",
    ValidationStatus.UNCERTAIN: "Сомнительно",
}


class DiffTableWidget(QWidget):
    """Таблица сравнения реквизитов с поддержкой фильтрации и бейджей статусов."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_rows: list[ValidationRow] = []
        self._active_filter: ValidationStatus | None = None
        self._search_query: str = ""

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Панель фильтров и поиска
        filter_bar = QHBoxLayout()
        filter_bar.setContentsMargins(0, 4, 0, 8)
        filter_bar.setSpacing(10)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        self._btn_all = QPushButton("Все (0)")
        self._btn_all.setObjectName("filterButton")
        self._btn_all.setCheckable(True)
        self._btn_all.setChecked(True)
        self._btn_all.clicked.connect(lambda: self._set_status_filter(None))
        self._btn_group.addButton(self._btn_all)
        filter_bar.addWidget(self._btn_all)

        self._btn_critical = QPushButton("Критические (0)")
        self._btn_critical.setObjectName("filterButton")
        self._btn_critical.setCheckable(True)
        self._btn_critical.clicked.connect(
            lambda: self._set_status_filter(ValidationStatus.CRITICAL)
        )
        self._btn_group.addButton(self._btn_critical)
        filter_bar.addWidget(self._btn_critical)

        self._btn_warning = QPushButton("Предупреждения (0)")
        self._btn_warning.setObjectName("filterButton")
        self._btn_warning.setCheckable(True)
        self._btn_warning.clicked.connect(lambda: self._set_status_filter(ValidationStatus.WARNING))
        self._btn_group.addButton(self._btn_warning)
        filter_bar.addWidget(self._btn_warning)

        self._btn_uncertain = QPushButton("Сомнительные (0)")
        self._btn_uncertain.setObjectName("filterButton")
        self._btn_uncertain.setCheckable(True)
        self._btn_uncertain.clicked.connect(
            lambda: self._set_status_filter(ValidationStatus.UNCERTAIN)
        )
        self._btn_group.addButton(self._btn_uncertain)
        filter_bar.addWidget(self._btn_uncertain)

        self._btn_match = QPushButton("Совпадения (0)")
        self._btn_match.setObjectName("filterButton")
        self._btn_match.setCheckable(True)
        self._btn_match.clicked.connect(lambda: self._set_status_filter(ValidationStatus.MATCH))
        self._btn_group.addButton(self._btn_match)
        filter_bar.addWidget(self._btn_match)

        filter_bar.addStretch(1)

        # Быстрый поиск
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск по таблице...")
        self._search_input.setFixedWidth(240)
        self._search_input.setFixedHeight(34)
        self._search_input.textChanged.connect(self._on_search_changed)
        filter_bar.addWidget(self._search_input)

        main_layout.addLayout(filter_bar)

        # Контейнер для переключения между таблицей и заглушкой пустого состояния
        self._stacked_layout = QStackedLayout()

        # 1. Заглушка пустого состояния
        self._empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_state_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        empty_title = QLabel("Документы еще не проверены")
        empty_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #334155;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel(
            "Загрузите заявку и накладную в поля выше и нажмите «Сверить документы»,\n"
            "либо выберите один из эталонных сценариев в верхней панели."
        )
        empty_desc.setStyleSheet("font-size: 13px; color: #64748B; text-align: center;")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_desc)

        self._stacked_layout.addWidget(self._empty_state_widget)

        # 2. Таблица сопоставления
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            [
                "Параметр рейса",
                "Заявка на перевозку",
                "Черновик ЭТрН / Накладная",
                "Статус",
                "Пояснение / Расхождение",
            ]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)

        # Высота строк и заголовка для просторного отображения элементов
        self._table.verticalHeader().setDefaultSectionSize(48)
        self._table.horizontalHeader().setFixedHeight(42)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self._table.setColumnWidth(0, 190)
        self._table.setColumnWidth(1, 210)
        self._table.setColumnWidth(2, 210)
        self._table.setColumnWidth(3, 160)

        self._stacked_layout.addWidget(self._table)
        main_layout.addLayout(self._stacked_layout, stretch=1)

    def set_rows(self, rows: list[ValidationRow]) -> None:
        """Заполняет таблицу списком строк и обновляет счетчики фильтров."""
        self._current_rows = list(rows)
        self._update_filter_counts()

        if not rows:
            self._stacked_layout.setCurrentWidget(self._empty_state_widget)
            return

        self._stacked_layout.setCurrentWidget(self._table)
        self._apply_filters()

    def clear(self) -> None:
        """Очищает данные таблицы."""
        self._current_rows.clear()
        self._table.setRowCount(0)
        self._update_filter_counts()
        self._stacked_layout.setCurrentWidget(self._empty_state_widget)

    def _update_filter_counts(self) -> None:
        """Обновляет цифры на кнопках фильтров."""
        total = len(self._current_rows)
        critical = sum(1 for r in self._current_rows if r.status == ValidationStatus.CRITICAL)
        warning = sum(1 for r in self._current_rows if r.status == ValidationStatus.WARNING)
        uncertain = sum(1 for r in self._current_rows if r.status == ValidationStatus.UNCERTAIN)
        match = sum(1 for r in self._current_rows if r.status == ValidationStatus.MATCH)

        self._btn_all.setText(f"Все ({total})")
        self._btn_critical.setText(f"Критические ({critical})")
        self._btn_warning.setText(f"Предупреждения ({warning})")
        self._btn_uncertain.setText(f"Сомнительные ({uncertain})")
        self._btn_match.setText(f"Совпадения ({match})")

    def _set_status_filter(self, status: ValidationStatus | None) -> None:
        """Устанавливает фильтр по статусу строки."""
        self._active_filter = status
        self._apply_filters()

    def _on_search_changed(self, text: str) -> None:
        """Обработка изменения поисковой строки."""
        self._search_query = text.strip().lower()
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Фильтрует и отображает строки в таблице."""
        filtered_rows = [
            row
            for row in self._current_rows
            if self._matches_filter(row) and self._matches_search(row)
        ]

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(filtered_rows))

        for row_idx, row in enumerate(filtered_rows):
            # 0: Параметр
            item_param = QTableWidgetItem(row.parameter_name)
            item_param.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row_idx, 0, item_param)

            # 1: Заявка
            item_order = QTableWidgetItem(row.order_value)
            item_order.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row_idx, 1, item_order)

            # 2: Накладная
            item_waybill = QTableWidgetItem(row.waybill_value)
            item_waybill.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._table.setItem(row_idx, 2, item_waybill)

            # 3: Статус (Кастомный центрированный бейдж)
            badge_widget = self._create_badge_widget(row.status)
            self._table.setCellWidget(row_idx, 3, badge_widget)

            # 4: Пояснение
            item_exp = QTableWidgetItem(row.explanation)
            item_exp.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item_exp.setToolTip(row.explanation)
            self._table.setItem(row_idx, 4, item_exp)

        self._table.setSortingEnabled(True)

    def _create_badge_widget(self, status: ValidationStatus) -> QWidget:
        """Создает стилизованный плашечный бейдж для статуса валидации."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel(STATUS_LABELS.get(status, str(status)))
        label.setObjectName(f"badge_{status.value}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedHeight(28)
        layout.addWidget(label)

        return container

    def _matches_filter(self, row: ValidationRow) -> bool:
        """Проверяет совпадение строки с текущим фильтром по статусу."""
        if self._active_filter is None:
            return True
        return row.status == self._active_filter

    def _matches_search(self, row: ValidationRow) -> bool:
        """Проверяет совпадение строки с поисковым запросом."""
        if not self._search_query:
            return True
        searchable_text = (
            f"{row.parameter_name} {row.order_value} {row.waybill_value} {row.explanation}".lower()
        )
        return self._search_query in searchable_text
