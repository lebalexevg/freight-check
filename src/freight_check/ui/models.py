"""Модели данных таблицы валидации в архитектуре Qt MVC (Model-View-Controller).

Обеспечивают строгую типизацию, приглушение совпадений (Visual Silencing),
посимвольное вычисление diff-токенов и приоритетную сортировку по критичности.
"""

import difflib
from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import QColor

from freight_check.contracts import ValidationRow, ValidationStatus

# Пользовательские роли Qt для кастомных делегатов и сортировки
STATUS_ROLE: int = int(Qt.ItemDataRole.UserRole) + 1
RAW_VALUE_ROLE: int = int(Qt.ItemDataRole.UserRole) + 2
IS_MONOSPACE_ROLE: int = int(Qt.ItemDataRole.UserRole) + 3
DIFF_HIGHLIGHTS_ROLE: int = int(Qt.ItemDataRole.UserRole) + 4
ROW_INDEX_ROLE: int = int(Qt.ItemDataRole.UserRole) + 5

# Заголовки 4 колонок рабочей таблицы (вместо прежних 5)
COLUMN_HEADERS: tuple[str, ...] = (
    "Параметр рейса",
    "Заявка (Эталон)",
    "Черновик ЭТрН / Накладная",
    "Пояснение / Разница",
)

# Перечень параметров, требующих моноширинного шрифта для мгновенного контроля разрядов
MONOSPACE_PARAMETERS: frozenset[str] = frozenset(
    {
        "Госномер тягача",
        "Госномер прицепа",
        "Паспорт водителя",
        "Телефон водителя",
        "Масса груза",
        "Масса груза (нетто)",
        "Объем груза",
        "Грузоподъемность ТС",
    }
)

# Естественный порядок следования параметров из DocumentPackage
CANONICAL_PARAM_ORDER: dict[str, int] = {
    "Госномер тягача": 0,
    "Госномер прицепа": 1,
    "Грузоподъемность ТС": 2,
    "ФИО водителя": 3,
    "Паспорт водителя": 4,
    "Телефон водителя": 5,
    "Масса груза": 6,
    "Масса груза (нетто)": 6,
    "Объем груза": 7,
    "Количество мест": 8,
    "Адрес погрузки": 9,
    "Адрес выгрузки": 10,
    "Грузополучатель": 11,
    "Температурный режим": 12,
    "Особые отметки / инструкции": 13,
}

# Приоритет сортировки: наиболее критичные расхождения всегда вверху
STATUS_PRIORITY: dict[ValidationStatus, int] = {
    ValidationStatus.CRITICAL: 0,
    ValidationStatus.WARNING: 1,
    ValidationStatus.UNCERTAIN: 2,
    ValidationStatus.MATCH: 3,
}

# Приглушенные фоновые оттенки строк для мгновенного считывания диспетчером
STATUS_ROW_BACKGROUNDS: dict[ValidationStatus, QColor] = {
    ValidationStatus.CRITICAL: QColor("#FEF2F2"),
    ValidationStatus.WARNING: QColor("#FFFBEB"),
    ValidationStatus.UNCERTAIN: QColor("#F1F5F9"),
    ValidationStatus.MATCH: QColor("#FFFFFF"),
}


def compute_diff_spans(
    order_val: str, waybill_val: str
) -> tuple[list[tuple[str, bool]], list[tuple[str, bool]]]:
    """Вычисляет посимвольные или токенные срезы различий между значениями.

    Возвращает два списка кортежей (подстрока, is_diff: bool) для Заявки и Накладной.
    """
    if not order_val and not waybill_val:
        return ([], [])

    if order_val == waybill_val:
        return ([(order_val, False)], [(waybill_val, False)])

    matcher = difflib.SequenceMatcher(None, order_val, waybill_val)
    order_spans: list[tuple[str, bool]] = []
    waybill_spans: list[tuple[str, bool]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            if i1 != i2:
                order_spans.append((order_val[i1:i2], False))
            if j1 != j2:
                waybill_spans.append((waybill_val[j1:j2], False))
        elif tag == "replace":
            if i1 != i2:
                order_spans.append((order_val[i1:i2], True))
            if j1 != j2:
                waybill_spans.append((waybill_val[j1:j2], True))
        elif tag == "delete":
            if i1 != i2:
                order_spans.append((order_val[i1:i2], True))
        elif tag == "insert":
            if j1 != j2:
                waybill_spans.append((waybill_val[j1:j2], True))

    return (order_spans, waybill_spans)


class ValidationTableModel(QAbstractTableModel):
    """Каноническая модель QAbstractTableModel для отчета сопоставления ValidationRow."""

    def __init__(
        self,
        rows: Sequence[ValidationRow] | None = None,
        parent: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self._rows: list[ValidationRow] = list(rows) if rows else []
        self._diff_cache: dict[int, tuple[list[tuple[str, bool]], list[tuple[str, bool]]]] = {}
        self._rebuild_diff_cache()

    def set_rows(self, rows: Sequence[ValidationRow]) -> None:
        """Обновляет набор строк модели с полным оповещением представлений."""
        self.beginResetModel()
        self._rows = list(rows)
        self._rebuild_diff_cache()
        self.endResetModel()

    def clear(self) -> None:
        """Очищает данные модели."""
        self.beginResetModel()
        self._rows.clear()
        self._diff_cache.clear()
        self.endResetModel()

    def get_row(self, row_idx: int) -> ValidationRow | None:
        """Возвращает строку по индексу модели."""
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        """Количество строк в модели."""
        if parent is not None and parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        """Количество колонок (4 колонки)."""
        if parent is not None and parent.isValid():
            return 0
        return len(COLUMN_HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Заголовки таблицы."""
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(COLUMN_HEADERS)
        ):
            return COLUMN_HEADERS[section]
        return None

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Поставляет типизированные данные для ячеек таблицы."""
        if not index.isValid():
            return None

        row_idx = index.row()
        col_idx = index.column()
        if not (0 <= row_idx < len(self._rows)):
            return None

        row = self._rows[row_idx]

        # 1. Текстовое отображение
        if role == Qt.ItemDataRole.DisplayRole:
            if col_idx == 0:
                return row.parameter_name
            if col_idx == 1:
                return row.order_value
            if col_idx == 2:
                return row.waybill_value
            if col_idx == 3:
                # Visual Silencing: для совпадений заменяем шаблонные фразы на лаконичный прочерк
                if row.status == ValidationStatus.MATCH:
                    return "—"
                return row.explanation
            return None

        # 2. Всплывающие подсказки (ToolTip)
        if role == Qt.ItemDataRole.ToolTipRole:
            if col_idx in (1, 2):
                val = row.order_value if col_idx == 1 else row.waybill_value
                return f"{val}\n(Двойной клик для копирования в буфер)"
            if col_idx == 3:
                return row.explanation
            return row.parameter_name

        # 3. Статус проверки
        if role == STATUS_ROLE:
            return row.status

        # 4. Чистое значение для копирования в буфер обмена
        if role == RAW_VALUE_ROLE:
            if col_idx == 1:
                return row.order_value
            if col_idx == 2:
                return row.waybill_value
            if col_idx == 0:
                return row.parameter_name
            if col_idx == 3:
                return row.explanation
            return None

        # 5. Признак моноширинного шрифта
        if role == IS_MONOSPACE_ROLE:
            return col_idx in (1, 2) and row.parameter_name in MONOSPACE_PARAMETERS

        # 6. Подсветка diff-токенов
        if role == DIFF_HIGHLIGHTS_ROLE:
            if row.status in (ValidationStatus.CRITICAL, ValidationStatus.WARNING):
                order_spans, waybill_spans = self._diff_cache.get(row_idx, ([], []))
                return order_spans if col_idx == 1 else waybill_spans
            return []

        # 7. Исходный индекс строки для естественной сортировки
        if role == ROW_INDEX_ROLE:
            return row_idx

        # 8. Фоновый оттенок строки
        if role == Qt.ItemDataRole.BackgroundRole:
            return STATUS_ROW_BACKGROUNDS.get(row.status, QColor("#FFFFFF"))

        # 9. Цвет шрифта (приглушение совпадений)
        if role == Qt.ItemDataRole.ForegroundRole:
            if row.status == ValidationStatus.MATCH:
                return QColor("#64748B")
            return QColor("#0F172A")

        return None

    def _rebuild_diff_cache(self) -> None:
        """Пересчитывает diff-срезы для строк с расхождениями."""
        self._diff_cache.clear()
        for idx, row in enumerate(self._rows):
            if row.status in (ValidationStatus.CRITICAL, ValidationStatus.WARNING):
                self._diff_cache[idx] = compute_diff_spans(row.order_value, row.waybill_value)


class ValidationSortFilterProxyModel(QSortFilterProxyModel):
    """Прокси-модель с приоритетной сортировкой по критичности и фильтрацией расхождений."""

    def __init__(self, parent: Any | None = None) -> None:
        super().__init__(parent)
        self._hide_matches: bool = False

    def set_hide_matches(self, hide: bool) -> None:
        """Переключает фильтрацию: скрывать ли строки со статусом MATCH."""
        if self._hide_matches != hide:
            self._hide_matches = hide
            self.invalidate()

    def is_hiding_matches(self) -> bool:
        """Возвращает текущее состояние фильтра скрытия совпадений."""
        return self._hide_matches

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex
    ) -> bool:
        """Фильтрует строки модели: скрывает MATCH, если активирован соответствующий тоггл."""
        if not self._hide_matches:
            return True

        source_model = self.sourceModel()
        if source_model is None:
            return True

        index = source_model.index(source_row, 0, source_parent)
        status = source_model.data(index, STATUS_ROLE)
        return status != ValidationStatus.MATCH

    def lessThan(
        self,
        source_left: QModelIndex | QPersistentModelIndex,
        source_right: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        """Приоритетная сортировка: CRITICAL -> WARNING -> UNCERTAIN -> MATCH.

        Внутри одной группы статусов строки упорядочиваются по естественному порядку
        реквизитов перевозки.
        """
        source_model = self.sourceModel()
        if source_model is None:
            return super().lessThan(source_left, source_right)

        status_left = source_model.data(source_left, STATUS_ROLE)
        status_right = source_model.data(source_right, STATUS_ROLE)

        p_left = STATUS_PRIORITY.get(status_left, 99)
        p_right = STATUS_PRIORITY.get(status_right, 99)

        if p_left != p_right:
            return p_left < p_right

        # Если приоритет статуса одинаков — сортируем по каноническому порядку параметров
        left_col0 = source_model.index(source_left.row(), 0, source_left.parent())
        right_col0 = source_model.index(source_right.row(), 0, source_right.parent())
        param_left = str(source_model.data(left_col0, Qt.ItemDataRole.DisplayRole) or "")
        param_right = str(source_model.data(right_col0, Qt.ItemDataRole.DisplayRole) or "")

        order_left = CANONICAL_PARAM_ORDER.get(param_left, 999)
        order_right = CANONICAL_PARAM_ORDER.get(param_right, 999)

        if order_left != order_right:
            return order_left < order_right

        # Финальный fallback: исходный индекс добавления строки
        orig_row_left = int(source_model.data(source_left, ROW_INDEX_ROLE) or 0)
        orig_row_right = int(source_model.data(source_right, ROW_INDEX_ROLE) or 0)
        return orig_row_left < orig_row_right
