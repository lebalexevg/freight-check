"""Фоновый вычислительный воркер для асинхронного сопоставления документов."""

import time

from PySide6.QtCore import QObject, QThread, Signal

from freight_check.contracts import SessionReport
from freight_check.ui.mock_data import (
    get_all_scenarios,
    get_mock_scenario_1_match,
)


class ValidationWorker(QThread):
    """Фоновый поток выполнения валидации документов."""

    progress_changed = Signal(int, str)
    validation_finished = Signal(SessionReport)
    validation_failed = Signal(str)

    def __init__(
        self,
        order_path: str,
        waybill_path: str,
        scenario_key: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._order_path = order_path
        self._waybill_path = waybill_path
        self._scenario_key = scenario_key

    def run(self) -> None:
        """Основной цикл фонового потока."""
        try:
            # Загрузка и маршрутизация файлов
            self.progress_changed.emit(15, "Анализ форматов и чтение документов...")
            time.sleep(0.08)
            if self.isInterruptionRequested():
                return

            # Извлечение реквизитов
            self.progress_changed.emit(40, "Семантическое извлечение ключевых реквизитов...")
            time.sleep(0.12)
            if self.isInterruptionRequested():
                return

            # Нормализация данных
            self.progress_changed.emit(65, "Нормализация госномеров, массы и адресов...")
            time.sleep(0.10)
            if self.isInterruptionRequested():
                return

            # Сопоставление данных
            self.progress_changed.emit(85, "Кросс-валидация и проверка на перегруз...")
            time.sleep(0.10)
            if self.isInterruptionRequested():
                return

            # Формирование отчета
            self.progress_changed.emit(100, "Формирование итогового отчета сессии...")
            time.sleep(0.05)
            if self.isInterruptionRequested():
                return

            # Получение отчета для выбранного сценария
            all_scenarios = get_all_scenarios()
            if self._scenario_key and self._scenario_key in all_scenarios:
                report = all_scenarios[self._scenario_key]
            else:
                # По умолчанию сценарий 1 (полное совпадение)
                report = get_mock_scenario_1_match()

            self.validation_finished.emit(report)

        except Exception as exc:  # noqa: BLE001
            self.validation_failed.emit(f"Ошибка при обработке документов: {exc}")
