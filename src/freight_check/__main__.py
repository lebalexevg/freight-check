"""Чистая точка входа для запуска приложения «Рейс-Проверка»."""

import sys
from pathlib import Path

# Гарантируем корректное разрешение пакета freight_check в dev- и frozen-режиме
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from freight_check import main  # noqa: E402

if __name__ == "__main__":
    main()
