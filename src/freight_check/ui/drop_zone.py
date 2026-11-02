"""Виджеты зоны загрузки документов и адаптивная панель слотов (DropZone / DocumentSlots).

Поддерживает два адаптивных состояния:
1. Empty State (файлы не загружены): просторные Drag-and-Drop слоты с подсказками форматов.
2. Loaded State (оба файла выбраны): ультракомпактная однострочная сплит-панель (40px)
   с бейджами форматов, векторными Segoe-иконками замены/удаления и прямым Drag-and-Drop.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from freight_check.ui.icons import (
    GLYPH_CLOSE,
    GLYPH_REFRESH,
    create_segoe_icon,
)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".xml",
        ".xlsx",
        ".xls",
        ".csv",
        ".docx",
        ".png",
        ".jpg",
        ".jpeg",
    }
)


def format_file_size(size_bytes: int) -> str:
    """Форматирует размер файла в удобочитаемый вид."""
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    return f"{size_bytes / (1024 * 1024):.2f} МБ"


def get_format_badge_text(file_path: str) -> str:
    """Возвращает короткий маркер формата для бейджа документа."""
    suffix = Path(file_path).suffix.lower()
    if suffix in (".png", ".jpg", ".jpeg"):
        return "СКАН"
    if suffix.startswith("."):
        return suffix[1:].upper()
    return "ФАЙЛ"


class DropZoneWidget(QFrame):
    """Индивидуальный слот документа с поддержкой Drag-and-Drop и переключением компактного вида."""

    file_selected = Signal(str)
    file_cleared = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        role_prefix: str = "Заявка:",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._role_prefix = role_prefix
        self._file_path: str | None = None
        self._is_compact: bool = False

        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._stacked_layout = QStackedLayout(self)
        self._stacked_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Развернутый вид (Expanded / Empty State)
        self._expanded_widget = QWidget()
        exp_layout = QVBoxLayout(self._expanded_widget)
        exp_layout.setContentsMargins(14, 12, 14, 12)
        exp_layout.setSpacing(6)

        # Заголовок
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #0F172A;")
        exp_layout.addWidget(self._title_label)

        # Подсказка
        self._hint_label = QLabel(self._subtitle)
        self._hint_label.setStyleSheet("color: #64748B; font-size: 11px;")
        self._hint_label.setWordWrap(True)
        exp_layout.addWidget(self._hint_label)

        # Кнопка выбора
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        self._browse_button = QPushButton("Выбрать файл...")
        self._browse_button.setFixedHeight(28)
        self._browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_button.clicked.connect(self._on_browse_clicked)
        btn_row.addWidget(self._browse_button)

        btn_row.addStretch(1)

        formats_label = QLabel("PDF, XML, XLSX, DOCX, скан")
        formats_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        btn_row.addWidget(formats_label)

        exp_layout.addLayout(btn_row)
        self._stacked_layout.addWidget(self._expanded_widget)

        # 2. Компактный однострочный вид (Compact / Loaded State)
        self._compact_widget = QWidget()
        compact_layout = QHBoxLayout(self._compact_widget)
        compact_layout.setContentsMargins(12, 0, 12, 0)
        compact_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        compact_layout.setSpacing(8)

        # Текстовый префикс роли слота («Заявка:» или «ЭТрН:»)
        self._role_label = QLabel(self._role_prefix)
        self._role_label.setObjectName("slotRoleLabel")
        self._role_label.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 500;")
        compact_layout.addWidget(self._role_label)

        # Имя файла и размер
        self._compact_name_label = QLabel()
        self._compact_name_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #0F172A;")
        compact_layout.addWidget(self._compact_name_label, stretch=1)

        # Кнопка замены: плоская и компактная
        self._replace_button = QPushButton("Заменить")
        self._replace_button.setObjectName("compactActionBtn")
        self._replace_button.setIcon(
            create_segoe_icon(GLYPH_REFRESH, QColor("#475569"), 12, y_offset=1.0)
        )
        self._replace_button.setIconSize(QSize(12, 12))
        self._replace_button.setFixedHeight(24)
        self._replace_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._replace_button.clicked.connect(self._on_browse_clicked)
        compact_layout.addWidget(self._replace_button)

        # Кнопка удаления: плоская и компактная
        self._clear_button = QPushButton()
        self._clear_button.setObjectName("compactClearBtn")
        self._clear_button.setIcon(create_segoe_icon(GLYPH_CLOSE, QColor("#64748B"), 12))
        self._clear_button.setIconSize(QSize(12, 12))
        self._clear_button.setToolTip("Удалить файл")
        self._clear_button.setFixedSize(24, 24)
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self.clear_file)
        compact_layout.addWidget(self._clear_button)

        # Сохраняем скрытую ссылку для обратной совместимости
        self._compact_badge = QLabel()
        self._compact_badge.setVisible(False)

        self._stacked_layout.addWidget(self._compact_widget)

    def set_compact_mode(self, compact: bool) -> None:
        """Переключает режим отображения слота."""
        self._is_compact = compact
        self._stacked_layout.setCurrentWidget(
            self._compact_widget if compact else self._expanded_widget
        )
        if compact:
            self.setFixedHeight(36)
        else:
            self.setMinimumHeight(96)
            self.setMaximumHeight(116)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Обработка наведения перетаскиваемых файлов."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and any(
                Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS for url in urls
            ):
                event.acceptProposedAction()
                self._set_drag_state(True)
                return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Сброс состояния подсветки при уходе курсора."""
        self._set_drag_state(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Обработка сброса файла в область."""
        self._set_drag_state(False)
        urls = event.mimeData().urls()
        if not urls:
            return

        for url in urls:
            local_path = url.toLocalFile()
            if Path(local_path).suffix.lower() in SUPPORTED_EXTENSIONS:
                self.set_file(local_path)
                event.acceptProposedAction()
                return

    def _set_drag_state(self, active: bool) -> None:
        """Переключает динамическое QSS свойство dragOver."""
        self.setProperty("dragOver", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_browse_clicked(self) -> None:
        """Открытие системного диалога выбора файла."""
        filter_str = (
            "Все поддерживаемые (*.pdf *.xml *.xlsx *.xls *.csv *.docx *.png *.jpg *.jpeg);;"
            "Электронные накладные (*.xml);;"
            "Документы PDF (*.pdf);;"
            "Таблицы Excel (*.xlsx *.xls *.csv);;"
            "Документы Word (*.docx);;"
            "Изображения (*.png *.jpg *.jpeg)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Выберите файл: {self._title}",
            "",
            filter_str,
        )
        if file_path:
            self.set_file(file_path)

    def set_file(self, file_path: str) -> None:
        """Устанавливает файл в слот."""
        path = Path(file_path)
        self._file_path = str(path)

        size_str = ""
        if path.exists() and path.is_file():
            size_str = f" ({format_file_size(path.stat().st_size)})"

        self._compact_badge.setText(get_format_badge_text(self._file_path))
        self._compact_name_label.setText(f"{path.name}{size_str}")

        self.setProperty("hasFile", "true")
        self.style().unpolish(self)
        self.style().polish(self)

        self.file_selected.emit(self._file_path)

    def clear_file(self) -> None:
        """Очищает выбранный файл."""
        self._file_path = None
        self._compact_name_label.setText("")

        self.setProperty("hasFile", "false")
        self.style().unpolish(self)
        self.style().polish(self)

        self.file_cleared.emit()

    def get_file_path(self) -> str | None:
        """Возвращает путь к текущему файлу или None."""
        return self._file_path

    def has_file(self) -> bool:
        """Проверяет, прикреплен ли файл к слоту."""
        return self._file_path is not None


class DocumentSlotsWidget(QWidget):
    """Адаптивный контейнер для двух слотов документов (Заявка и Накладная).

    Автоматически сворачивается в единую узкую сплит-панель высотой 40px,
    когда выбраны оба документа, освобождая место для таблицы.
    """

    files_ready = Signal(str, str)
    files_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._order_slot = DropZoneWidget(
            title="1. Заявка на перевозку",
            subtitle="Входящая заявка заказчика (PDF, Excel, Word, скан)",
            role_prefix="Заявка:",
            parent=self,
        )
        self._order_slot.file_selected.connect(self._on_slot_changed)
        self._order_slot.file_cleared.connect(self._on_slot_changed)
        layout.addWidget(self._order_slot)

        self._waybill_slot = DropZoneWidget(
            title="2. Черновик ЭТрН / Накладная",
            subtitle="Проект накладной (XML титул ФНС, скан, PDF)",
            role_prefix="ЭТрН:",
            parent=self,
        )
        self._waybill_slot.file_selected.connect(self._on_slot_changed)
        self._waybill_slot.file_cleared.connect(self._on_slot_changed)
        layout.addWidget(self._waybill_slot)

        self._update_presentation_mode()

    def _on_slot_changed(self) -> None:
        """Обработка изменения файлов в любом из слотов."""
        self._update_presentation_mode()
        self.files_changed.emit()

        order_path = self._order_slot.get_file_path()
        waybill_path = self._waybill_slot.get_file_path()
        if order_path and waybill_path:
            self.files_ready.emit(order_path, waybill_path)

    def _update_presentation_mode(self) -> None:
        """Переключает слоты в компактный вид при заполнении обоих файлов."""
        has_both = self.has_both_files()
        layout = self.layout()
        if isinstance(layout, QHBoxLayout):
            layout.setSpacing(10)
        self._order_slot.set_compact_mode(has_both)
        self._waybill_slot.set_compact_mode(has_both)

    def has_both_files(self) -> bool:
        """Возвращает True, если оба документа выбраны."""
        return self._order_slot.has_file() and self._waybill_slot.has_file()

    def get_order_path(self) -> str | None:
        """Возвращает путь к заявке."""
        return self._order_slot.get_file_path()

    def get_waybill_path(self) -> str | None:
        """Возвращает путь к накладной."""
        return self._waybill_slot.get_file_path()

    def set_files(self, order_path: str, waybill_path: str) -> None:
        """Устанавливает пути к обоим документам (например, при загрузке демо)."""
        self._order_slot.set_file(order_path)
        self._waybill_slot.set_file(waybill_path)

    def clear_all(self) -> None:
        """Очищает оба слота документов и разворачивает их в Empty State."""
        self._order_slot.clear_file()
        self._waybill_slot.clear_file()
