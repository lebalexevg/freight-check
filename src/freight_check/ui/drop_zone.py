"""Зоны загрузки и выбора документов."""

from pathlib import Path

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
    QEnterEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from freight_check.ui.icons import (
    GLYPH_CHECK,
    GLYPH_CLOSE,
    GLYPH_DOCUMENT,
    GLYPH_FOLDER,
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
        self.setProperty("compact", "false")
        self.setProperty("hasFile", "false")
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._stacked_layout = QStackedLayout(self)
        self._stacked_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Полноразмерный вид (Empty State — файл не выбран)
        self._empty_widget = QWidget(self)
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(32, 24, 32, 24)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)

        # Иконка документа
        self._doc_icon_label = QLabel(self._empty_widget)
        self._doc_icon_label.setObjectName("docIconLabel")
        doc_icon = create_segoe_icon(GLYPH_DOCUMENT, QColor("#3B82F6"), base_size=76)
        self._doc_icon_label.setPixmap(doc_icon.pixmap(QSize(76, 76)))
        self._doc_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._doc_icon_label)

        empty_layout.addSpacing(4)

        # Заголовок шага
        self._title_label = QLabel(self._title, self._empty_widget)
        self._title_label.setObjectName("dropZoneTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._title_label)

        # Описание / подзаголовок роли
        self._hint_label = QLabel(self._subtitle, self._empty_widget)
        self._hint_label.setObjectName("dropZoneSubtitle")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setWordWrap(True)
        empty_layout.addWidget(self._hint_label)

        empty_layout.addSpacing(8)

        # Кнопка выбора файла
        self._browse_button = QPushButton("  Выбрать файл...", self._empty_widget)
        self._browse_button.setObjectName("dropZoneBrowseBtn")
        self._browse_button.setIcon(
            create_segoe_icon(GLYPH_FOLDER, QColor("#0F172A"), base_size=16, y_offset=0.5)
        )
        self._browse_button.setIconSize(QSize(16, 16))
        self._browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_button.setFixedHeight(36)
        self._browse_button.clicked.connect(self._on_browse_clicked)
        empty_layout.addWidget(self._browse_button, alignment=Qt.AlignmentFlag.AlignCenter)

        empty_layout.addSpacing(6)

        # Подсказка Drag-and-Drop
        dnd_hint = QLabel("Перетащите файл сюда или нажмите кнопку выше", self._empty_widget)
        dnd_hint.setObjectName("dropZoneDndHint")
        dnd_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(dnd_hint)

        # Форматы
        formats_label = QLabel(
            "Поддерживаются: PDF, XML, XLSX, DOCX, скан (до 50 МБ)", self._empty_widget
        )
        formats_label.setObjectName("dropZoneFormats")
        formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(formats_label)

        self._stacked_layout.addWidget(self._empty_widget)

        # Вид с выбранным файлом
        self._loaded_expanded_widget = QWidget(self)
        loaded_layout = QVBoxLayout(self._loaded_expanded_widget)
        loaded_layout.setContentsMargins(32, 24, 32, 24)
        loaded_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loaded_layout.setSpacing(10)

        self._ready_icon_label = QLabel(self._loaded_expanded_widget)
        self._ready_icon_label.setObjectName("readyIconLabel")
        ready_icon = create_segoe_icon(GLYPH_CHECK, QColor("#059669"), base_size=76)
        self._ready_icon_label.setPixmap(ready_icon.pixmap(QSize(76, 76)))
        self._ready_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loaded_layout.addWidget(self._ready_icon_label)

        loaded_layout.addSpacing(4)

        ready_status = QLabel("Документ прикреплен и готов", self._loaded_expanded_widget)
        ready_status.setObjectName("readyStatus")
        ready_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loaded_layout.addWidget(ready_status)

        self._loaded_filename_label = QLabel("", self._loaded_expanded_widget)
        self._loaded_filename_label.setObjectName("loadedFilenameLabel")
        self._loaded_filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loaded_layout.addWidget(self._loaded_filename_label)

        self._loaded_filesize_label = QLabel("", self._loaded_expanded_widget)
        self._loaded_filesize_label.setObjectName("loadedFilesizeLabel")
        self._loaded_filesize_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loaded_layout.addWidget(self._loaded_filesize_label)

        loaded_layout.addSpacing(8)

        # Кнопки действий
        action_col = QVBoxLayout()
        action_col.setSpacing(8)
        action_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        replace_btn = QPushButton("  Заменить файл", self._loaded_expanded_widget)
        replace_btn.setObjectName("expandedActionBtn")
        replace_btn.setIcon(
            create_segoe_icon(GLYPH_REFRESH, QColor("#334155"), base_size=14, y_offset=0.5)
        )
        replace_btn.setIconSize(QSize(14, 14))
        replace_btn.setFixedHeight(32)
        replace_btn.setFixedWidth(160)
        replace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replace_btn.clicked.connect(self._on_browse_clicked)
        action_col.addWidget(replace_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        clear_btn = QPushButton("  Удалить", self._loaded_expanded_widget)
        clear_btn.setObjectName("expandedActionBtn")
        clear_btn.setIcon(
            create_segoe_icon(GLYPH_CLOSE, QColor("#475569"), base_size=14, glyph_scale=1.0)
        )
        clear_btn.setIconSize(QSize(14, 14))
        clear_btn.setFixedHeight(32)
        clear_btn.setFixedWidth(160)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_file)
        action_col.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        loaded_layout.addLayout(action_col)
        self._stacked_layout.addWidget(self._loaded_expanded_widget)

        # Компактный вид
        self._compact_widget = QWidget(self)
        compact_layout = QHBoxLayout(self._compact_widget)
        compact_layout.setContentsMargins(16, 8, 16, 8)
        compact_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        compact_layout.setSpacing(10)

        # Префикс роли
        self._role_label = QLabel(self._role_prefix, self._compact_widget)
        self._role_label.setObjectName("slotRoleLabel")
        compact_layout.addWidget(self._role_label)

        # Имя файла и размер
        self._compact_name_label = QLabel("", self._compact_widget)
        self._compact_name_label.setObjectName("compactNameLabel")
        compact_layout.addWidget(self._compact_name_label, stretch=1)

        # Кнопка замены
        self._replace_button = QPushButton("  Заменить", self._compact_widget)
        self._replace_button.setObjectName("compactActionBtn")
        self._replace_button.setIcon(
            create_segoe_icon(GLYPH_REFRESH, QColor("#475569"), 13, y_offset=0.5)
        )
        self._replace_button.setIconSize(QSize(13, 13))
        self._replace_button.setFixedHeight(30)
        self._replace_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._replace_button.clicked.connect(self._on_browse_clicked)
        compact_layout.addWidget(self._replace_button)

        # Кнопка удаления
        self._clear_button = QPushButton(self._compact_widget)
        self._clear_button.setObjectName("compactClearBtn")
        self._clear_button.setIcon(
            create_segoe_icon(GLYPH_CLOSE, QColor("#475569"), 12, glyph_scale=1.0)
        )
        self._clear_button.setIconSize(QSize(12, 12))
        self._clear_button.setToolTip("Удалить файл")
        self._clear_button.setFixedSize(30, 30)
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self.clear_file)
        compact_layout.addWidget(self._clear_button)

        # Сохраняем скрытую ссылку для обратной совместимости
        self._compact_badge = QLabel(self._compact_widget)
        self._compact_badge.setVisible(False)

        self._stacked_layout.addWidget(self._compact_widget)

    def set_compact_mode(self, compact: bool) -> None:
        """Переключает режим отображения слота."""
        self._is_compact = compact
        self.setProperty("compact", "true" if compact else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if compact:
            self._stacked_layout.setCurrentWidget(self._compact_widget)
            self.setFixedHeight(48)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        else:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            if self.has_file():
                self._stacked_layout.setCurrentWidget(self._loaded_expanded_widget)
            else:
                self._stacked_layout.setCurrentWidget(self._empty_widget)

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
        self.update()

    def enterEvent(self, event: QEnterEvent) -> None:
        """Обработка наведения курсора для перерисовки интерактивного пунктира."""
        super().enterEvent(event)
        if not self._is_compact and not self.has_file():
            self.update()

    def leaveEvent(self, event: QEvent) -> None:
        """Обработка ухода курсора для возврата исходного цвета пунктира."""
        super().leaveEvent(event)
        if not self._is_compact and not self.has_file():
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Отрисовывает пунктирную границу для пустого слота."""
        super().paintEvent(event)
        if not self._is_compact and not self.has_file():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            is_drag = self.property("dragOver") == "true"
            is_hover = self.underMouse()

            if is_drag:
                color = QColor("#1D4ED8")
                pen_style = Qt.PenStyle.SolidLine
                pen_width = 2.0
            elif is_hover:
                color = QColor("#2563EB")
                pen_style = Qt.PenStyle.DashLine
                pen_width = 2.0
            else:
                color = QColor("#94A3B8")
                pen_style = Qt.PenStyle.DashLine
                pen_width = 1.0

            pen = QPen(color)
            pen.setWidthF(pen_width)
            pen.setStyle(pen_style)
            if pen_style == Qt.PenStyle.DashLine:
                pen.setDashPattern([4, 4])

            painter.setPen(pen)
            half = pen_width / 2.0
            rect = QRectF(half, half, self.width() - pen_width, self.height() - pen_width)
            painter.drawRoundedRect(rect, 2.0, 2.0)
            painter.end()

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
        self._compact_name_label.setToolTip(self._file_path)

        self._loaded_filename_label.setText(path.name)
        self._loaded_filesize_label.setText(size_str.strip(" ()") or "Файл готов к сверке")

        self.setProperty("hasFile", "true")
        self.style().unpolish(self)
        self.style().polish(self)

        if self._is_compact:
            self._stacked_layout.setCurrentWidget(self._compact_widget)
        else:
            self._stacked_layout.setCurrentWidget(self._loaded_expanded_widget)

        self.file_selected.emit(self._file_path)

    def clear_file(self) -> None:
        """Очищает выбранный файл и возвращает слот в развернутое пустое состояние."""
        self._file_path = None
        self._compact_name_label.setText("")
        self._compact_name_label.setToolTip("")
        self._loaded_filename_label.setText("")
        self._loaded_filesize_label.setText("")
        self._compact_badge.setText("")

        self.setProperty("hasFile", "false")
        self.style().unpolish(self)
        self.style().polish(self)

        if self._is_compact:
            self._stacked_layout.setCurrentWidget(self._compact_widget)
        else:
            self._stacked_layout.setCurrentWidget(self._empty_widget)

        self.file_cleared.emit()

    def get_file_path(self) -> str | None:
        """Возвращает текущий путь к файлу в слоте."""
        return self._file_path

    def has_file(self) -> bool:
        """Проверяет наличие файла в слоте."""
        return self._file_path is not None


class DocumentSlotsWidget(QWidget):
    """Контейнер для слотов заявки и накладной."""

    files_ready = Signal(str, str)
    files_changed = Signal()

    @property
    def order_slot(self) -> DropZoneWidget:
        """Слот входящей заявки на перевозку."""
        return self._order_slot

    @property
    def waybill_slot(self) -> DropZoneWidget:
        """Слот черновика ЭТрН / накладной."""
        return self._waybill_slot

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._order_slot = DropZoneWidget(
            title="1. Заявка на перевозку",
            subtitle="Входящая заявка заказчика",
            role_prefix="Заявка:",
            parent=self,
        )
        self._order_slot.file_selected.connect(self._on_slot_changed)
        self._order_slot.file_cleared.connect(self._on_slot_changed)
        layout.addWidget(self._order_slot)

        self._waybill_slot = DropZoneWidget(
            title="2. Черновик ЭТрН / Накладная",
            subtitle="Проект накладной",
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
        self._order_slot.set_compact_mode(has_both)
        self._waybill_slot.set_compact_mode(has_both)
        if has_both:
            self.setFixedHeight(48)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        else:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

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
