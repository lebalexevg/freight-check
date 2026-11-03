"""Локализация статических ресурсов (иконки, стили) с поддержкой PyInstaller."""

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Определяет абсолютный путь к ресурсу с поддержкой PyInstaller и dev-режима."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_path = Path(__file__).resolve().parents[3]

    target = base_path / relative_path
    if target.exists():
        return target

    fallback = Path(relative_path)
    if fallback.exists():
        return fallback.resolve()

    return target
