"""Модальное окно «О программе» (AboutDialog)."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from freight_check.ui.icons import get_app_icon

APP_VERSION: str = "0.1.0-beta"
APP_NAME: str = "Рейс-Проверка"
APP_SUBTITLE: str = "Кросс-валидация транспортных документов"


class AboutDialog(QDialog):
    """Информационное окно сведений о приложении, версии и поддерживаемых форматах."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutDialog")
        self.setWindowTitle(f"О программе — {APP_NAME}")
        self.setModal(True)
        self.setFixedSize(480, 380)
        self.setWindowIcon(get_app_icon())
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        # 1. Шапка: официальная иконка приложения, название, версия и подзаголовок
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        icon_label = QLabel(self)
        icon_pixmap = get_app_icon().pixmap(QSize(42, 42))
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(42, 42)
        header_layout.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.setAlignment(Qt.AlignmentFlag.AlignBaseline)

        title_label = QLabel(APP_NAME, self)
        title_label.setObjectName("aboutTitleLabel")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_row.addWidget(title_label)

        version_label = QLabel(f"v{APP_VERSION}", self)
        version_label.setObjectName("aboutVersionLabel")
        title_row.addWidget(version_label)
        title_row.addStretch(1)
        title_col.addLayout(title_row)

        subtitle_label = QLabel(APP_SUBTITLE, self)
        subtitle_label.setObjectName("aboutSubtitleLabel")
        title_col.addWidget(subtitle_label)

        header_layout.addLayout(title_col, stretch=1)
        layout.addLayout(header_layout)

        # Тонкий 1px разделитель
        sep1 = QFrame(self)
        sep1.setObjectName("aboutSep")
        sep1.setFixedHeight(1)
        layout.addWidget(sep1)

        # 2. Описание назначения утилиты
        desc_label = QLabel(
            "Автономная локальная утилита для сверки входящих заявок заказчика "
            "с черновиками электронных транспортных накладных (ЭТрН) до выпуска машины в рейс.",
            self,
        )
        desc_label.setWordWrap(True)
        desc_label.setObjectName("aboutDescLabel")
        layout.addWidget(desc_label)

        # 3. Поддерживаемые форматы документов (двухколоночный текстовый список без pills)
        formats_col = QVBoxLayout()
        formats_col.setSpacing(6)

        formats_title = QLabel("Поддерживаемые форматы файлов:", self)
        formats_title.setObjectName("aboutFormatsTitle")
        formats_col.addWidget(formats_title)

        formats_grid = QHBoxLayout()
        formats_grid.setSpacing(24)

        col1 = QVBoxLayout()
        col1.setSpacing(4)
        for item in [
            "• PDF (векторный и текстовый)",
            "• XML (титулы ЭТрН ФНС)",
            "• Excel (.xlsx, .xls)",
        ]:
            lbl = QLabel(item, self)
            lbl.setObjectName("aboutFormatItem")
            col1.addWidget(lbl)

        col2 = QVBoxLayout()
        col2.setSpacing(4)
        for item in [
            "• Word (.docx)",
            "• Текстовый формат (.csv)",
            "• Сканы и фото (OCR)",
        ]:
            lbl = QLabel(item, self)
            lbl.setObjectName("aboutFormatItem")
            col2.addWidget(lbl)

        formats_grid.addLayout(col1)
        formats_grid.addLayout(col2)
        formats_grid.addStretch(1)
        formats_col.addLayout(formats_grid)

        layout.addLayout(formats_col)

        # 4. Технические сведения (без указания разработчиков)
        tech_col = QVBoxLayout()
        tech_col.setSpacing(4)

        engine_label = QLabel(
            "Движок: RapidOCR (ONNX Runtime, CPU) • PySide6 • Python 3.13",
            self,
        )
        engine_label.setObjectName("aboutTechLabel")
        tech_col.addWidget(engine_label)

        layout.addLayout(tech_col)

        # Распорка
        layout.addStretch(1)

        # Тонкий 1px разделитель перед кнопкой
        sep2 = QFrame(self)
        sep2.setObjectName("aboutSep")
        sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        # 5. Стандартная кнопка закрытия
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        close_btn = QPushButton("Понятно", self)
        close_btn.setObjectName("aboutCloseBtn")
        close_btn.setFixedHeight(30)
        close_btn.setFixedWidth(100)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)
