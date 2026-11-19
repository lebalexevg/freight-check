from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Border, Font, PatternFill, Side
from scripts.dataset_generator.models import DocumentFields


def build_xlsx_waybill(file_path: Path, data: DocumentFields) -> None:
    """Создает Транспортную накладную XLSX по структуре Постановления № 2200."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Транспортная накладная"

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    sec_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    ws["A1"] = f"ТРАНСПОРТНАЯ НАКЛАДНАЯ № {data.doc_number}"
    ws["A1"].font = Font(name="Arial", size=13, bold=True)
    ws["A2"] = (
        f"Дата составления: {data.doc_date} г. (Форма по Постановлению Правительства РФ № 2200)"
    )
    ws["A2"].font = Font(name="Arial", size=9, italic=True)

    row_idx = 4
    sections = [
        (
            "Раздел 1. Грузоотправитель",
            [
                ("Наименование организации", data.shipper),
                ("ИНН", data.shipper_inn),
                ("Адрес места нахождения", data.loading_address),
            ],
        ),
        (
            "Раздел 2. Грузополучатель",
            [
                ("Наименование организации", data.consignee),
                ("ИНН", data.consignee_inn),
                ("Адрес места нахождения", data.unloading_address),
            ],
        ),
        (
            "Раздел 3. Груз",
            [
                ("Наименование груза", data.cargo_name),
                ("Масса груза (нетто)", data.cargo_weight),
                ("Объем груза", data.cargo_volume),
                ("Количество мест", data.cargo_places),
            ],
        ),
        (
            "Раздел 5. Указания грузоотправителя",
            [
                ("Температурный режим", data.temperature),
                ("Особые условия", data.special_conditions),
            ],
        ),
        (
            "Раздел 6. Перевозчик",
            [
                ("Наименование перевозчика", data.carrier),
                ("ИНН перевозчика", data.carrier_inn),
                ("ФИО водителя", data.driver_name),
                ("Паспорт водителя", data.driver_passport),
                ("Телефон водителя", data.driver_phone),
            ],
        ),
        (
            "Раздел 7. Транспортное средство",
            [
                ("Госномер тягача", data.truck_plate),
                ("Госномер прицепа", data.trailer_plate),
                ("Грузоподъемность ТС", data.truck_capacity),
            ],
        ),
        (
            "Раздел 8. Прием груза",
            [
                ("Адрес места погрузки", data.loading_address),
                ("Масса груза при взвешивании", data.cargo_weight),
            ],
        ),
        (
            "Раздел 10. Выдача груза",
            [
                ("Адрес места выгрузки", data.unloading_address),
                ("Масса груза при сдаче", data.cargo_weight),
            ],
        ),
        (
            "Раздел 12. Стоимость перевозки",
            [
                ("Стоимость", data.cost),
            ],
        ),
    ]

    for sec_header, items in sections:
        ws.cell(row=row_idx, column=1, value=sec_header).font = Font(
            name="Arial", size=10, bold=True
        )
        ws.cell(row=row_idx, column=1).fill = sec_fill
        ws.cell(row=row_idx, column=2).fill = sec_fill
        row_idx += 1

        for k, v in items:
            c1 = ws.cell(row=row_idx, column=1, value=k)
            c2 = ws.cell(row=row_idx, column=2, value=str(v))
            c1.font = Font(name="Arial", size=9)
            c2.font = Font(name="Arial", size=9)
            c1.border = thin_border
            c2.border = thin_border
            row_idx += 1
        row_idx += 1

    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 54

    file_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(file_path)


def build_xlsx_order(file_path: Path, data: DocumentFields) -> None:
    """Создает Заказ на перевозку груза в формате XLSX."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Заказ на перевозку"

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    ws["A1"] = f"ДОГОВОР-ЗАЯВКА НА ПЕРЕВОЗКУ № {data.doc_number}"
    ws["A1"].font = Font(name="Arial", size=13, bold=True)
    ws["A2"] = f"Дата: {data.doc_date} г.  Заказчик: {data.shipper} | Перевозчик: {data.carrier}"
    ws["A2"].font = Font(name="Arial", size=9)

    ws["A4"] = "Параметр перевозки"
    ws["B4"] = "Значение"
    ws["A4"].fill = header_fill
    ws["B4"].fill = header_fill
    ws["A4"].font = Font(name="Arial", size=10, bold=True)
    ws["B4"].font = Font(name="Arial", size=10, bold=True)

    rows = [
        ("Адрес погрузки", data.loading_address),
        ("Адрес выгрузки", data.unloading_address),
        ("Госномер тягача", data.truck_plate),
        ("Госномер прицепа", data.trailer_plate),
        ("Грузоподъемность ТС", data.truck_capacity),
        ("ФИО водителя", data.driver_name),
        ("Паспорт водителя", data.driver_passport),
        ("Телефон водителя", data.driver_phone),
        ("Наименование груза", data.cargo_name),
        ("Масса груза (нетто)", data.cargo_weight),
        ("Объем груза", data.cargo_volume),
        ("Количество мест", data.cargo_places),
        ("Температурный режим", data.temperature),
        ("Особые условия", data.special_conditions),
        ("Стоимость перевозки", data.cost),
    ]

    for idx, (k, v) in enumerate(rows, start=5):
        c1 = ws.cell(row=idx, column=1, value=k)
        c2 = ws.cell(row=idx, column=2, value=str(v))
        c1.font = Font(name="Arial", size=9.5)
        c2.font = Font(name="Arial", size=9.5)
        c1.border = thin_border
        c2.border = thin_border

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 54

    file_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(file_path)
