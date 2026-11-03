"""Виджет таблицы сопоставления реквизитов."""

from collections.abc import Sequence

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QStackedLayout,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from freight_check.contracts import ValidationRow
from freight_check.ui.delegates import (
    DiffHighlightDelegate,
    ExplanationColumnDelegate,
    ParameterColumnDelegate,
)
from freight_check.ui.models import (
    RAW_VALUE_ROLE,
    ValidationSortFilterProxyModel,
    ValidationTableModel,
)


class DiffTableView(QTableView):
    """Таблица результатов сопоставления."""

    def mousePressEvent(self, event) -> None:
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        index = self.indexAt(pos)
        if not index.isValid():
            # Клик по пустому пространству ниже строк таблицы -> сброс выделения
            self.clearSelection()
            self.setCurrentIndex(QModelIndex())
            event.accept()
            return

        # Если строка уже выделена, повторный клик снимает выделение
        selection_model = self.selectionModel()
        if selection_model and selection_model.isRowSelected(index.row(), QModelIndex()):
            self.clearSelection()
            self.setCurrentIndex(QModelIndex())
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        # При двойном клике гарантируем выбор строки для копирования
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        index = self.indexAt(pos)
        if index.isValid():
            self.selectRow(index.row())
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.clearSelection()
            self.setCurrentIndex(QModelIndex())
            event.accept()
            return
        super().keyPressEvent(event)


class DiffTableWidget(QWidget):
    """Таблица сопоставления реквизитов с поддержкой MVC и diff-делегатов."""

    value_copied = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._stacked_layout = QStackedLayout()

        # Пустое состояние
        self._empty_state_widget = QWidget(self)
        empty_layout = QVBoxLayout(self._empty_state_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(8)

        empty_title = QLabel("Документы готовы к сверке", self._empty_state_widget)
        empty_title.setObjectName("emptyDiffTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_desc = QLabel(
            "Перетащите заявку и черновик ЭТрН в слоты выше,\n"
            "либо выберите готовый сценарий в меню «Демо-сценарии» (Ctrl+D).",
            self._empty_state_widget,
        )
        empty_desc.setObjectName("emptyDiffDesc")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_desc)

        self._stacked_layout.addWidget(self._empty_state_widget)

        # Таблица результатов
        self._source_model = ValidationTableModel(parent=self)
        self._proxy_model = ValidationSortFilterProxyModel(parent=self)
        self._proxy_model.setSourceModel(self._source_model)

        self._table = DiffTableView(self)
        self._table.setObjectName("diffTableView")
        self._table.setModel(self._proxy_model)

        # Подключение кастомных делегатов колонок
        self._param_delegate = ParameterColumnDelegate(self._table)
        self._diff_delegate = DiffHighlightDelegate(self._table)
        self._exp_delegate = ExplanationColumnDelegate(self._table)

        self._table.setItemDelegateForColumn(0, self._param_delegate)
        self._table.setItemDelegateForColumn(1, self._diff_delegate)
        self._table.setItemDelegateForColumn(2, self._diff_delegate)
        self._table.setItemDelegateForColumn(3, self._exp_delegate)

        # Настройки отображения и выделения
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setWordWrap(False)
        self._table.setTextElideMode(Qt.TextElideMode.ElideRight)

        # Размеры строк и заголовка
        self._table.verticalHeader().setDefaultSectionSize(42)
        header = self._table.horizontalHeader()
        header.setFixedHeight(40)
        header.setSortIndicatorShown(False)
        header.setSectionsClickable(True)

        # Белый фон таблицы и viewport задан централизованно в style.qss (QTableView)

        # Настройка колонок
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        header.setStretchLastSection(True)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._table.setColumnWidth(0, 180)
        self._table.setColumnWidth(1, 260)
        self._table.setColumnWidth(2, 260)
        self._table.setColumnWidth(3, 380)

        # Двойной клик для копирования реквизита в буфер обмена
        self._table.doubleClicked.connect(self._on_cell_double_clicked)

        self._stacked_layout.addWidget(self._table)
        main_layout.addLayout(self._stacked_layout)

    def set_rows(self, rows: Sequence[ValidationRow]) -> None:
        """Заполняет таблицу строками отчета и активирует вид таблицы."""
        self._source_model.set_rows(rows)

        if not rows:
            self._stacked_layout.setCurrentWidget(self._empty_state_widget)
            return

        self._stacked_layout.setCurrentWidget(self._table)

        # Сортировка по умолчанию: приоритет критических расхождений
        self._proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

    def clear(self) -> None:
        """Очищает данные таблицы и возвращает заглушку пустого состояния."""
        self._source_model.clear()
        self._stacked_layout.setCurrentWidget(self._empty_state_widget)

    def set_hide_matches(self, hide: bool) -> None:
        """Скрывает или отображает строки со статусом MATCH."""
        self._proxy_model.set_hide_matches(hide)

    def row_count(self) -> int:
        """Возвращает видимое количество строк с учетом фильтрации."""
        return self._proxy_model.rowCount()

    def _on_cell_double_clicked(self, proxy_index: QModelIndex) -> None:
        """Копирует значение выбранной ячейки в буфер обмена по двойному клику."""
        col = proxy_index.column()
        # Разрешено быстрое копирование для колонок значений и параметров
        if col in (0, 1, 2, 3):
            raw_value = proxy_index.data(RAW_VALUE_ROLE)
            if raw_value is not None:
                text_to_copy = str(raw_value)
                clipboard = QGuiApplication.clipboard()
                if clipboard:
                    clipboard.setText(text_to_copy)
                self.value_copied.emit(text_to_copy)
