"""Тесты для компонентов Qt MVC: моделей, прокси-фильтрации и кастомных делегатов."""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem

from freight_check.contracts import SessionReport, ValidationRow, ValidationStatus
from freight_check.ui.delegates import (
    DiffHighlightDelegate,
    ExplanationColumnDelegate,
    ParameterColumnDelegate,
)
from freight_check.ui.drop_zone import DocumentSlotsWidget
from freight_check.ui.models import (
    IS_MONOSPACE_ROLE,
    RAW_VALUE_ROLE,
    STATUS_ROLE,
    ValidationSortFilterProxyModel,
    ValidationTableModel,
    compute_diff_spans,
)
from freight_check.ui.summary_bar import SummaryBarWidget


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


def test_document_slots_widget_state_transitions(qapp: QApplication) -> None:
    """Проверка автоматического сворачивания слотов документов в 38px при наличии обоих файлов."""
    slots = DocumentSlotsWidget()

    # Начальное состояние: файлы не выбраны, слоты развернуты
    assert not slots.has_both_files()
    assert slots._order_slot._is_compact is False
    assert slots._waybill_slot._is_compact is False

    ready_signals: list[tuple[str, str]] = []
    slots.files_ready.connect(lambda o, w: ready_signals.append((o, w)))

    # Выбираем только заявку
    slots._order_slot.set_file("order.pdf")
    assert not slots.has_both_files()
    assert slots._order_slot._is_compact is False
    assert len(ready_signals) == 0

    # Выбираем накладную -> оба файла есть -> автосворачивание в компактный вид (48px)
    slots._waybill_slot.set_file("waybill.xml")
    assert slots.has_both_files()
    assert slots._order_slot._is_compact is True
    assert slots._waybill_slot._is_compact is True
    assert slots._order_slot.height() == 48
    assert len(ready_signals) == 1
    assert ready_signals[0] == (slots.get_order_path(), slots.get_waybill_path())

    # Удаляем один файл -> авторазворачивание обратно в Empty State
    slots._order_slot.clear_file()
    assert not slots.has_both_files()
    assert slots._order_slot._is_compact is False
    assert slots._waybill_slot._is_compact is False

    # Проверка clear_all()
    slots.set_files("order2.pdf", "waybill2.xml")
    assert slots.has_both_files()
    slots.clear_all()
    assert not slots.has_both_files()
    assert slots.get_order_path() is None
    assert slots.get_waybill_path() is None


def test_summary_bar_widget(qapp: QApplication) -> None:
    """Проверка инфо-полосы сводки (48px) и переключателя 'Только расхождения'."""
    bar = SummaryBarWidget()
    assert bar.height() == 48
    assert not bar.is_only_diffs_checked()
    assert "Ожидание документов" in bar._status_badge.text()

    report = SessionReport(
        overall_status=ValidationStatus.CRITICAL,
        critical_errors_count=2,
        warnings_count=1,
        processing_time_ms=120,
        rows=[
            ValidationRow("Параметр 1", "А", "Б", ValidationStatus.CRITICAL, "Ошибка"),
            ValidationRow("Параметр 2", "В", "Г", ValidationStatus.CRITICAL, "Ошибка 2"),
            ValidationRow("Параметр 3", "Д", "Е", ValidationStatus.WARNING, "Внимание"),
            ValidationRow("Параметр 4", "Ж", "Ж", ValidationStatus.MATCH, "Совпадение"),
        ],
    )

    bar.set_report(report)
    assert "Найдены расхождения" in bar._status_badge.text()
    assert not bar._status_icon.isHidden()
    assert "Критических: 2" in bar._critical_label.text()
    assert "Предупреждений: 1" in bar._warning_label.text()
    assert "Совпадений: 1" in bar._match_label.text()

    # Проверка сигнала фильтрации
    diff_filter_events: list[bool] = []
    bar.filter_only_diffs_changed.connect(diff_filter_events.append)

    bar.set_only_diffs_checked(True)
    assert bar.is_only_diffs_checked() is True
    assert diff_filter_events == [True]

    bar.reset()
    assert not bar.is_only_diffs_checked()
    assert bar._status_icon.isHidden()
    assert "Ожидание документов" in bar._status_badge.text()
