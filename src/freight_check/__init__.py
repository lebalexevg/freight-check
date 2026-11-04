"""Главный модуль пакета freight-check."""

import contextlib
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

with contextlib.suppress(ImportError):
    import PySide6.QtSvg  # noqa: F401

from freight_check.ui.icons import get_app_icon
from freight_check.ui.main_window import MainWindow
from freight_check.version import __author__, __version__

__all__ = ["APP_USER_MODEL_ID", "__author__", "__version__", "main"]

APP_USER_MODEL_ID: str = "ru.freightcheck.app.v1"


def main() -> None:
    """Точка входа запуска приложения «Рейс-Проверка»."""
    if sys.platform == "win32":
        import ctypes

        with contextlib.suppress(Exception):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)

    if getattr(sys, "frozen", False):
        candidate_bases = [
            Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)),
            Path(sys.executable).resolve().parent,
            Path(sys.executable).resolve().parent / "_internal",
        ]
        for base in candidate_bases:
            plugins_dir = base / "PySide6" / "plugins"
            if plugins_dir.exists():
                QCoreApplication.addLibraryPath(str(plugins_dir))
                break

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
    app.setWindowIcon(get_app_icon())

    window = MainWindow()
    window.show()

    if is_new_app:
        sys.exit(app.exec())
