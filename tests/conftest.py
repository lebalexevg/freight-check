"""Общие фикстуры для тестирования PySide6 UI в headless-режиме."""

import os

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Сессионная фикстура для инициализации QApplication в headless-режиме."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    return app
