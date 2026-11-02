"""Главный модуль пакета freight-check."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from freight_check.ui.main_window import MainWindow


def main() -> None:
    """Точка входа запуска приложения «Рейс-Проверка»."""
    app = QApplication.instance()
    is_new_app = False
    if not isinstance(app, QApplication):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)
        is_new_app = True

    app.setApplicationName("freight-check")
    app.setApplicationDisplayName("")
    app.setOrganizationName("FreightCheck")

    window = MainWindow()
    window.show()

    if is_new_app:
        sys.exit(app.exec())
