"""Тесты для компонентов графического интерфейса и моковых данных."""

from PySide6.QtWidgets import QApplication

from freight_check.contracts import SessionReport, ValidationStatus
from freight_check.ui.diff_table import DiffTableWidget
from freight_check.ui.drop_zone import DropZoneWidget
from freight_check.ui.main_window import MainWindow, get_stylesheet_path
from freight_check.ui.mock_data import (
    get_all_scenarios,
    get_mock_scenario_1_match,
    get_mock_scenario_2_overload,
    get_mock_scenario_3_typos,
    get_mock_scenario_4_warnings,
    get_mock_scenario_5_uncertain,
)
from freight_check.ui.worker import ValidationWorker


def test_mock_scenarios_structure() -> None:
    """Проверка корректности структуры всех 5 моковых сценариев."""
    scenarios = get_all_scenarios()
    assert len(scenarios) == 5

    # Сценарий 1
    s1 = get_mock_scenario_1_match()
    assert s1.overall_status == ValidationStatus.MATCH
    assert s1.critical_errors_count == 0
    assert s1.warnings_count == 0
    assert len(s1.rows) > 0
    assert all(r.status == ValidationStatus.MATCH for r in s1.rows)

    # Сценарий 2: Перегруз
    s2 = get_mock_scenario_2_overload()
    assert s2.overall_status == ValidationStatus.CRITICAL
    assert s2.critical_errors_count == 1
    assert any("22.5 т" in r.order_value for r in s2.rows)
    assert any("22 500 кг" in r.waybill_value for r in s2.rows)

    # Сценарий 3: Опечатки
    s3 = get_mock_scenario_3_typos()
    assert s3.overall_status == ValidationStatus.CRITICAL
    assert s3.critical_errors_count == 3
    critical_params = [r.parameter_name for r in s3.rows if r.status == ValidationStatus.CRITICAL]
    assert "Госномер тягача" in critical_params
    assert "Паспорт водителя" in critical_params
    assert "Адрес погрузки" in critical_params

    # Сценарий 4: Допустимые расхождения
    s4 = get_mock_scenario_4_warnings()
    assert s4.overall_status == ValidationStatus.WARNING
    assert s4.critical_errors_count == 0
    assert s4.warnings_count == 2

    # Сценарий 5: Сомнительные сканы
    s5 = get_mock_scenario_5_uncertain()
    assert s5.overall_status == ValidationStatus.UNCERTAIN
    assert any(r.status == ValidationStatus.UNCERTAIN for r in s5.rows)


def test_stylesheet_path_exists() -> None:
    """Проверка доступности файла стилей style.qss."""
    path = get_stylesheet_path()
    assert path.exists()
    assert path.stat().st_size > 0


def test_drop_zone_widget(qapp: QApplication) -> None:
    """Проверка логики DropZoneWidget."""
    drop_zone = DropZoneWidget(title="Заявка", subtitle="Перетащите файл")

    assert not drop_zone.has_file()
    assert drop_zone.get_file_path() is None

    # Установка файла
    selected_signals: list[str] = []
    drop_zone.file_selected.connect(selected_signals.append)

    drop_zone.set_file("my_order.pdf")
    assert drop_zone.has_file()
    file_path = drop_zone.get_file_path()
    assert file_path is not None
    assert "my_order.pdf" in file_path
    assert len(selected_signals) == 1

    # Очистка
    cleared_signals: list[bool] = []
    drop_zone.file_cleared.connect(lambda: cleared_signals.append(True))

    drop_zone.clear_file()
    assert not drop_zone.has_file()
    assert drop_zone.get_file_path() is None
    assert len(cleared_signals) == 1


def test_diff_table_widget(qapp: QApplication) -> None:
    """Проверка таблицы расхождений, фильтрации расхождений и копирования по двойному клику."""
    table = DiffTableWidget()

    # Заполнение строками сценария 3 (опечатки: 3 критических + совпадения)
    s3 = get_mock_scenario_3_typos()
    table.set_rows(s3.rows)

    # Проверка отображения строк таблицы через модель
    assert table.row_count() == len(s3.rows)

    # Фильтрация «Только расхождения»
    table.set_hide_matches(True)
    assert table.row_count() == 3

    # Отключение фильтра
    table.set_hide_matches(False)
    assert table.row_count() == len(s3.rows)

    # Проверка двойного клика для копирования
    copied_signals: list[str] = []
    table.value_copied.connect(copied_signals.append)

    first_index = table._proxy_model.index(0, 1)
    table._on_cell_double_clicked(first_index)
    assert len(copied_signals) == 1
    assert len(copied_signals[0]) > 0

    # Очистка таблицы
    table.clear()
    assert table.row_count() == 0


def test_validation_worker_lifecycle(qapp: QApplication) -> None:
    """Проверка фонового воркера и испускания сигналов."""
    worker = ValidationWorker(
        order_path="test_order.pdf",
        waybill_path="test_waybill.xml",
        scenario_key="Сценарий 2: Критический перегруз ТС",
    )

    received_progress: list[int] = []
    received_reports: list[SessionReport] = []

    worker.progress_changed.connect(lambda p, _: received_progress.append(p))
    worker.validation_finished.connect(received_reports.append)

    # Запуск в синхронном режиме через run() для детерминированного теста
    worker.run()

    assert len(received_progress) >= 4
    assert 100 in received_progress
    assert len(received_reports) == 1
    assert received_reports[0].overall_status == ValidationStatus.CRITICAL
    assert received_reports[0].critical_errors_count == 1


def test_main_window_integration(qapp: QApplication) -> None:
    """Проверка инициализации и интеграции компонентов MainWindow."""
    window = MainWindow()

    assert window._summary_bar.isHidden()
    assert not window._doc_slots.has_both_files()

    # Загрузка сценария через выбор демо-сценария
    first_scenario_key = list(window._scenarios.keys())[0]
    window._on_scenario_selected(first_scenario_key)

    # Проверяем, что файлы установились и слоты перешли в компактный вид
    assert window._doc_slots.has_both_files()
    assert window._order_drop_zone.has_file()
    assert window._waybill_drop_zone.has_file()

    # Ждем завершения воркера и обрабатываем события Qt
    if window._worker is not None:
        window._worker.wait(3000)
    qapp.processEvents()

    # Проверяем, что отчет получен и UI обновился
    assert window._current_report is not None
    assert not window._summary_bar.isHidden()
    assert window._diff_table.row_count() > 0

    # Проверяем сброс всех данных
    window._reset_all()
    assert not window._doc_slots.has_both_files()
    assert not window._order_drop_zone.has_file()
    assert not window._waybill_drop_zone.has_file()
    assert window._summary_bar.isHidden()

    window.close()
