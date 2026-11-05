from pathlib import Path

import openpyxl

from freight_check.contracts import ValidationStatus
from freight_check.core.extractor import extract_package_from_file
from freight_check.core.matcher import ValidationEngine


def test_end_to_end_pipeline_xlsx(tmp_path: Path) -> None:
    """Сквозной тест без запуска графического интерфейса: XLSX -> Extractor -> Matcher."""
    # 1. Создаем тестовую заявку (XLSX)
    order_file = tmp_path / "order.xlsx"
    wb1 = openpyxl.Workbook()
    ws1 = wb1.active
    assert ws1 is not None
    ws1["A1"] = "Госномер тягача:"
    ws1["B1"] = "А 123 ВС 77"
    ws1["A2"] = "Масса груза:"
    ws1["B2"] = "20 т"
    ws1["A3"] = "Грузоподъемность:"
    ws1["B3"] = "20 000 кг"
    wb1.save(order_file)

    # 2. Создаем тестовую накладную (XLSX)
    waybill_file = tmp_path / "waybill.xlsx"
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    assert ws2 is not None
    ws2["A1"] = "Транспорт:"
    ws2["B1"] = "A123BC77"  # на латинице
    ws2["A2"] = "Масса нетто:"
    ws2["B2"] = "20000 кг"
    wb2.save(waybill_file)

    # 3. Извлекаем пакеты документов
    order_pkg = extract_package_from_file(order_file, role="order")
    waybill_pkg = extract_package_from_file(waybill_file, role="waybill")

    assert order_pkg.truck_number is not None
    assert waybill_pkg.truck_number is not None

    # 4. Выполняем кросс-валидацию
    engine = ValidationEngine()
    report = engine.validate(order_pkg, waybill_pkg)

    # Латиница транслитерирована, масса 20 т совпала с 20 000 кг
    assert report.overall_status == ValidationStatus.MATCH
    assert report.critical_errors_count == 0
