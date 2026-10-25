from abc import ABC, abstractmethod
from pathlib import Path

from freight_check.contracts import DocumentPackage


class BaseParser(ABC):
    """Абстрактный базовый класс для всех парсеров документов."""

    @abstractmethod
    def parse(self, file_path: Path) -> DocumentPackage:
        """
        Извлекает данные из файла и возвращает DocumentPackage.

        :param file_path: Путь к файлу.
        :return: Заполненный DocumentPackage.
        :raises FileNotFoundError: Если файл не найден.
        :raises ValueError: Если файл поврежден или имеет неверный формат.
        """
        pass

    @staticmethod
    def _validate_file(file_path: Path) -> None:
        """Базовая валидация файла перед парсингом."""
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        # Лимит 50 МБ согласно ТЗ (п. 1.4, п. 3.2.1)
        max_size_bytes = 50 * 1024 * 1024
        if file_path.stat().st_size > max_size_bytes:
            raise ValueError(f"Файл превышает максимальный размер 50 МБ: {file_path.name}")