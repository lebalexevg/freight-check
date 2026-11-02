"""Тесты для компонентов Qt MVC: моделей, прокси-фильтрации и кастомных делегатов."""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem

from freight_check.contracts import ValidationRow, ValidationStatus
from freight_check.ui.delegates import (
    DiffHighlightDelegate,
    ExplanationColumnDelegate,
    ParameterColumnDelegate,
)
from freight_check.ui.models import (
    IS_MONOSPACE_ROLE,
    RAW_VALUE_ROLE,
    STATUS_ROLE,
    ValidationSortFilterProxyModel,
    ValidationTableModel,
    compute_diff_spans,
)


def test_compute_diff_spans_identical() -> None:
    """Проверка diff-алгоритма для идентичных строк."""
    order_spans, waybill_spans = compute_diff_spans("А123ВС77", "А123ВС77")
    assert len(order_spans) == 1
    assert order_spans[0] == ("А123ВС77", False)
    assert len(waybill_spans) == 1
    assert waybill_spans[0] == ("А123ВС77", False)


def test_compute_diff_spans_typo() -> None:
    """Проверка diff-алгоритма для опечатки в одном символе номера паспорта."""
    order_spans, waybill_spans = compute_diff_spans("4510 123456", "4510 123457")

    # В заявке '6' помечена как diff
    diff_order_tokens = [chunk for chunk, is_diff in order_spans if is_diff]
    assert "6" in diff_order_tokens

    # В накладной '7' помечена как diff
    diff_waybill_tokens = [chunk for chunk, is_diff in waybill_spans if is_diff]
    assert "7" in diff_waybill_tokens


def test_validation_table_model_basic(qapp: QApplication) -> None:
    """Проверка базовой функциональности ValidationTableModel."""
    rows = [
        ValidationRow(
            parameter_name="Госномер тягача",
            order_value="А 123 ВС 77",
            waybill_value="А 128 ВС 77",
            status=ValidationStatus.CRITICAL,
            explanation="Несовпадение номера ТС",
        ),
        ValidationRow(
            parameter_name="ФИО водителя",
            order_value="Иванов И. И.",
            waybill_value="Иванов И. И.",
            status=ValidationStatus.MATCH,
            explanation="Полное совпадение",
        ),
    ]

    model = ValidationTableModel(rows)
    assert model.rowCount() == 2
    assert model.columnCount() == 4

    # Заголовки колонок
    headers = [
        model.headerData(i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        for i in range(4)
    ]
    assert headers == [
        "Параметр рейса",
        "Заявка (Эталон)",
        "Черновик ЭТрН / Накладная",
        "Пояснение / Разница",
    ]

    # Visual Silencing: строка 1 (MATCH) в колонке 3 отображает лаконичный прочерк "—"
    assert model.data(model.index(1, 3), Qt.ItemDataRole.DisplayRole) == "—"
    # Для строки 0 (CRITICAL) колонка 3 отображает полное пояснение
    assert model.data(model.index(0, 3), Qt.ItemDataRole.DisplayRole) == "Несовпадение номера ТС"

    # Проверка моноширинного шрифта для госномера тягача
    assert model.data(model.index(0, 1), IS_MONOSPACE_ROLE) is True
    # Для ФИО моноширинный шрифт не требуется
    assert model.data(model.index(1, 1), IS_MONOSPACE_ROLE) is False

    # Проверка статуса и чистого значения для буфера
    assert model.data(model.index(0, 0), STATUS_ROLE) == ValidationStatus.CRITICAL
    assert model.data(model.index(0, 1), RAW_VALUE_ROLE) == "А 123 ВС 77"


def test_validation_sort_filter_proxy_priority(qapp: QApplication) -> None:
    """Проверка приоритетной сортировки: CRITICAL первыми, затем WARNING, UNCERTAIN, MATCH."""
    rows = [
        ValidationRow(
            parameter_name="Адрес выгрузки",
            order_value="Москва",
            waybill_value="Москва",
            status=ValidationStatus.MATCH,
            explanation="Совпадает",
        ),
        ValidationRow(
            parameter_name="Паспорт водителя",
            order_value="4510 123456",
            waybill_value="4510 123457",
            status=ValidationStatus.CRITICAL,
            explanation="Ошибка паспорта",
        ),
        ValidationRow(
            parameter_name="Адрес погрузки",
            order_value="ул. Ленина",
            waybill_value="Ленина ул.",
            status=ValidationStatus.WARNING,
            explanation="Перестановка слов",
        ),
    ]

    source_model = ValidationTableModel(rows)
    proxy_model = ValidationSortFilterProxyModel()
    proxy_model.setSourceModel(source_model)
    proxy_model.sort(0, Qt.SortOrder.AscendingOrder)

    # Приоритет сортировки: CRITICAL (строка 0 в прокси) -> WARNING (строка 1) -> MATCH (строка 2)
    assert proxy_model.data(proxy_model.index(0, 0), STATUS_ROLE) == ValidationStatus.CRITICAL
    assert proxy_model.data(proxy_model.index(1, 0), STATUS_ROLE) == ValidationStatus.WARNING
    assert proxy_model.data(proxy_model.index(2, 0), STATUS_ROLE) == ValidationStatus.MATCH

    # Проверка фильтрации «Только расхождения»
    proxy_model.set_hide_matches(True)
    assert proxy_model.rowCount() == 2
    assert proxy_model.is_hiding_matches() is True

    # Строки MATCH скрыты, остались только CRITICAL и WARNING
    statuses = [
        proxy_model.data(proxy_model.index(i, 0), STATUS_ROLE)
        for i in range(proxy_model.rowCount())
    ]
    assert ValidationStatus.MATCH not in statuses


def test_delegates_rendering(qapp: QApplication) -> None:
    """Проверка корректности отрисовки кастомных делегатов без исключений."""
    rows = [
        ValidationRow(
            parameter_name="Госномер тягача",
            order_value="А 123 ВС 77",
            waybill_value="А 128 ВС 77",
            status=ValidationStatus.CRITICAL,
            explanation="Несовпадение номера",
        ),
        ValidationRow(
            parameter_name="ФИО водителя",
            order_value="Иванов И. И.",
            waybill_value="Иванов И. И.",
            status=ValidationStatus.MATCH,
            explanation="Совпадает",
        ),
    ]

    model = ValidationTableModel(rows)
    param_delegate = ParameterColumnDelegate()
    diff_delegate = DiffHighlightDelegate()
    exp_delegate = ExplanationColumnDelegate()

    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 200, 36)

    # Создаем фиктивное растровое изображение для QPainter
    image = QImage(200, 36, QImage.Format.Format_ARGB32)
    painter = QPainter(image)

    try:
        # Проверяем отрисовку колонки 0 (Параметр)
        param_delegate.paint(painter, option, model.index(0, 0))
        param_delegate.paint(painter, option, model.index(1, 0))

        # Проверяем отрисовку diff-колонок (Заявка и Накладная)
        diff_delegate.paint(painter, option, model.index(0, 1))
        diff_delegate.paint(painter, option, model.index(0, 2))
        diff_delegate.paint(painter, option, model.index(1, 1))

        # Проверяем отрисовку колонки пояснения
        exp_delegate.paint(painter, option, model.index(0, 3))
        exp_delegate.paint(painter, option, model.index(1, 3))
    finally:
        painter.end()

    # Проверка размерности
    size = param_delegate.sizeHint(option, model.index(0, 0))
    assert size.height() >= 34
