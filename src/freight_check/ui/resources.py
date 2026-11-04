"""Локализация статических ресурсов (иконки, стили) с поддержкой PyInstaller."""

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Определяет абсолютный путь к ресурсу с поддержкой PyInstaller onedir и dev-режима."""
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is not None:
            candidates.append(Path(meipass) / relative_path)
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / relative_path)
        candidates.append(exe_dir / "_internal" / relative_path)
    else:
        repo_root = Path(__file__).resolve().parents[3]
        candidates.append(repo_root / relative_path)

    fallback = Path(relative_path)
    candidates.append(fallback.resolve())

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]
