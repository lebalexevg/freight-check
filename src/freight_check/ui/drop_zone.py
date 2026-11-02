"""Виджет зоны Drag-and-Drop для загрузки входных документов."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
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


class DropZoneWidget(QFrame):
    """Виджет зоны загрузки документа с поддержкой Drag-and-Drop."""

    file_selected = Signal(str)
    file_cleared = Signal()

    def __init__(self, title: str, subtitle: str, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._file_path: str | None = None

        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Заголовок роли документа
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A;")
        layout.addWidget(self._title_label)

        # Описание / Инструкция
        self._hint_label = QLabel(self._subtitle)
        self._hint_label.setStyleSheet("color: #64748B; font-size: 12px;")
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        # Карточка выбранного файла (скрыта по умолчанию)
        self._file_card = QFrame()
        self._file_card.setStyleSheet(
            "background-color: #F1F5F9; border: 1px solid #CBD5E1; "
            "border-radius: 6px; padding: 8px;"
        )
        file_card_layout = QHBoxLayout(self._file_card)
        file_card_layout.setContentsMargins(8, 4, 8, 4)

        self._file_info_label = QLabel()
        self._file_info_label.setStyleSheet("font-weight: 600; color: #1E293B;")
        file_card_layout.addWidget(self._file_info_label, stretch=1)

        self._remove_button = QPushButton("Удалить")
        self._remove_button.setToolTip("Удалить выбранный файл")
        self._remove_button.setStyleSheet(
            "QPushButton { border: none; background: transparent; "
            "color: #64748B; font-size: 12px; font-weight: 600; padding: 2px 8px; } "
            "QPushButton:hover { color: #DC2626; text-decoration: underline; }"
        )
        self._remove_button.clicked.connect(self.clear_file)
        file_card_layout.addWidget(self._remove_button)

        layout.addWidget(self._file_card)
        self._file_card.setVisible(False)

        # Блок с кнопкой выбора файла
        buttons_layout = QHBoxLayout()
        self._browse_button = QPushButton("Выбрать файл...")
        self._browse_button.setFixedHeight(34)
        self._browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_button.clicked.connect(self._on_browse_clicked)
        buttons_layout.addWidget(self._browse_button)
        buttons_layout.addStretch(1)

        # Подсказка по поддерживаемым форматам
        self._formats_label = QLabel("PDF, XML, XLSX, XLS, DOCX, CSV, PNG, JPG")
        self._formats_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        buttons_layout.addWidget(self._formats_label)

        layout.addLayout(buttons_layout)

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
        """Устанавливает файл в зону загрузки."""
        path = Path(file_path)
        self._file_path = str(path)

        # Вычисление размера
        size_str = ""
        if path.exists() and path.is_file():
            size_str = f" ({format_file_size(path.stat().st_size)})"

        self._file_info_label.setText(f"{path.name}{size_str}")
        self._file_card.setVisible(True)
        self._hint_label.setVisible(False)
        self._browse_button.setText("Заменить файл...")

        self.setProperty("hasFile", "true")
        self.style().unpolish(self)
        self.style().polish(self)

        self.file_selected.emit(self._file_path)

    def clear_file(self) -> None:
        """Очищает выбранный файл."""
        self._file_path = None
        self._file_info_label.setText("")
        self._file_card.setVisible(False)
        self._hint_label.setVisible(True)
        self._browse_button.setText("Выбрать файл...")

        self.setProperty("hasFile", "false")
        self.style().unpolish(self)
        self.style().polish(self)

        self.file_cleared.emit()

    def get_file_path(self) -> str | None:
        """Возвращает путь к текущему файлу или None."""
        return self._file_path

    def has_file(self) -> bool:
        """Проверяет, прикреплен ли файл к зоне."""
        return self._file_path is not None
