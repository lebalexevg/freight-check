from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from scripts.dataset_generator.builders.common import REPORTLAB_FONT
from scripts.dataset_generator.models import DocumentFields


def build_pdf_waybill(file_path: Path, data: DocumentFields) -> None:
    """Создает цифровой PDF Транспортной накладной по структуре Постановления № 2200."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(file_path), pagesize=A4)

    c.setFont(REPORTLAB_FONT, 13)
    c.drawString(50, 805, f"ТРАНСПОРТНАЯ НАКЛАДНАЯ № {data.doc_number}")
    c.setFont(REPORTLAB_FONT, 8)
    c.drawString(
        50,
        792,
        f"Дата составления: {data.doc_date} г. (Форма по Постановлению Правительства РФ № 2200)",
    )

    c.setLineWidth(0.5)
    c.line(50, 785, 545, 785)

    y = 770
    step = 17

    lines = [
        ("Раздел 1. Грузоотправитель", f"{data.shipper}, ИНН {data.shipper_inn}"),
        ("Раздел 2. Грузополучатель", f"{data.consignee}, ИНН {data.consignee_inn}"),
        ("Раздел 3. Наименование груза", data.cargo_name),
        ("Раздел 3. Масса груза (нетто)", data.cargo_weight),
        ("Раздел 3. Количество мест / Объем", f"{data.cargo_places} / {data.cargo_volume}"),
        ("Раздел 5. Температурный режим", data.temperature),
        ("Раздел 5. Особые условия", data.special_conditions),
        ("Раздел 6. Перевозчик", f"{data.carrier}, ИНН {data.carrier_inn}"),
        ("Раздел 6. Водитель (ФИО)", data.driver_name),
        ("Раздел 6. Паспорт водителя", data.driver_passport),
        ("Раздел 6. Телефон водителя", data.driver_phone),
        ("Раздел 7. Госномер тягача", data.truck_plate),
        ("Раздел 7. Госномер прицепа", data.trailer_plate),
        ("Раздел 7. Грузоподъемность ТС", data.truck_capacity),
        ("Раздел 8. Прием (Адрес погрузки)", data.loading_address),
        ("Раздел 10. Выдача (Адрес выгрузки)", data.unloading_address),
        ("Раздел 12. Стоимость перевозки", data.cost),
    ]

    for label, val in lines:
        c.setFont(REPORTLAB_FONT, 9)
        c.drawString(50, y, f"{label}:")
        c.drawString(240, y, str(val))
        y -= step

    c.showPage()
    c.save()


def build_pdf_order(file_path: Path, data: DocumentFields) -> None:
    """Создает цифровой PDF Договор-заявки на перевозку груза."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(file_path), pagesize=A4)

    c.setFont(REPORTLAB_FONT, 13)
    c.drawString(50, 805, f"ДОГОВОР-ЗАЯВКА НА ПЕРЕВОЗКУ ГРУЗА № {data.doc_number}")
    c.setFont(REPORTLAB_FONT, 9)
    c.drawString(
        50,
        790,
        f"Дата: {data.doc_date} г.  Заказчик: {data.shipper} | Перевозчик: {data.carrier}",
    )

    c.setLineWidth(0.5)
    c.line(50, 780, 545, 780)

    y = 760
    step = 18

    fields = [
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
        ("Особые условия перевозки", data.special_conditions),
        ("Стоимость перевозки", data.cost),
    ]

    for label, val in fields:
        c.setFont(REPORTLAB_FONT, 9)
        c.drawString(50, y, f"{label}:")
        c.drawString(230, y, str(val))
        y -= step

    c.drawString(
        50,
        y - 20,
        "Подписи сторон:  Заказчик: __________ / М.П.     Перевозчик: __________ / М.П.",
    )

    c.showPage()
    c.save()
