from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.shared import Pt
from scripts.dataset_generator.models import DocumentFields


def build_docx_waybill(file_path: Path, data: DocumentFields) -> None:
    """Создает Транспортную накладную DOCX по структуре Постановления № 2200."""
    doc = Document()

    h = doc.add_heading(f"ТРАНСПОРТНАЯ НАКЛАДНАЯ № {data.doc_number}", level=1)
    h.alignment = 1
    sub = doc.add_paragraph(
        f"Дата составления: {data.doc_date} г.\n"
        "(Форма утверждена Постановлением Правительства РФ от 21.12.2020 № 2200 в ред. ПП РФ от 30.11.2021 № 2116)"
    )
    sub.alignment = 1
    if sub.runs:
        sub.runs[0].font.size = Pt(9)
        sub.runs[0].font.italic = True

    sections = [
        (
            "1. Грузоотправитель",
            [
                ("Наименование организации", data.shipper),
                ("ИНН / КПП", f"{data.shipper_inn} / 770101001"),
                ("Адрес места нахождения", data.loading_address),
                ("Контактный телефон", "+7 (495) 123-45-67"),
            ],
        ),
        (
            "1а. Заказчик услуг по организации перевозки груза",
            [
                ("Наименование заказчика", data.shipper),
                ("ИНН заказчика", data.shipper_inn),
            ],
        ),
        (
            "2. Грузополучатель",
            [
                ("Наименование организации", data.consignee),
                ("ИНН / КПП", f"{data.consignee_inn} / 780901001"),
                ("Адрес места нахождения", data.unloading_address),
                ("Контактный телефон", "+7 (812) 987-65-43"),
            ],
        ),
        (
            "3. Груз",
            [
                ("Наименование груза", data.cargo_name),
                ("Количество грузовых мест", data.cargo_places),
                ("Масса груза (нетто)", data.cargo_weight),
                ("Масса груза (брутто)", data.cargo_weight),
                ("Объем груза", data.cargo_volume),
            ],
        ),
        (
            "5. Указания грузоотправителя по особым условиям перевозки",
            [
                ("Температурный режим", data.temperature),
                ("Особые условия перевозки", data.special_conditions),
            ],
        ),
        (
            "6. Перевозчик",
            [
                ("Наименование перевозчика", data.carrier),
                ("ИНН перевозчика", data.carrier_inn),
                ("ФИО водителя", data.driver_name),
                ("Паспорт водителя (серия, номер)", data.driver_passport),
                ("Телефон водителя", data.driver_phone),
            ],
        ),
        (
            "7. Транспортное средство",
            [
                ("Тип транспортного средства", "Грузовой автомобиль с полуприцепом"),
                ("Госномер тягача", data.truck_plate),
                ("Госномер прицепа", data.trailer_plate),
                ("Грузоподъемность ТС", data.truck_capacity),
            ],
        ),
        (
            "8. Прием груза",
            [
                ("Адрес места погрузки", data.loading_address),
                ("Дата и время подачи ТС", f"{data.doc_date} 09:00"),
                ("Масса груза при взвешивании", data.cargo_weight),
                ("Подпись водителя о приеме", f"Принял водитель {data.driver_name} _________"),
            ],
        ),
        (
            "10. Выдача груза",
            [
                ("Адрес места выгрузки", data.unloading_address),
                ("Дата и время доставки", f"{data.doc_date} 18:00"),
                ("Масса груза при сдаче", data.cargo_weight),
                ("Подпись грузополучателя", "Груз получен без претензий _________"),
            ],
        ),
        (
            "12. Стоимость услуг перевозки груза",
            [
                ("Стоимость перевозки", data.cost),
            ],
        ),
    ]

    for sec_title, items in sections:
        p = doc.add_paragraph()
        run = p.add_run(sec_title)
        run.bold = True
        run.font.size = Pt(11)

        tbl = doc.add_table(rows=len(items), cols=2)
        tbl.style = "Table Grid"
        for i, (k, v) in enumerate(items):
            row = tbl.rows[i]
            row.cells[0].text = k
            row.cells[1].text = str(v)
            row.cells[0].paragraphs[0].runs[0].font.size = Pt(9.5)
            row.cells[1].paragraphs[0].runs[0].font.size = Pt(9.5)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(file_path))


def build_docx_order(file_path: Path, data: DocumentFields) -> None:
    """Создает Договор-заявку на перевозку груза в формате DOCX."""
    doc = Document()

    h = doc.add_heading(f"ДОГОВОР-ЗАЯВКА НА ПЕРЕВОЗКУ ГРУЗА № {data.doc_number}", level=1)
    h.alignment = 1
    p = doc.add_paragraph(
        f"г. Москва                                                    «{data.doc_date}» г."
    )
    p.runs[0].bold = True

    intro = doc.add_paragraph(
        f"Заказчик: {data.shipper} (ИНН {data.shipper_inn}), с одной стороны, и "
        f"Перевозчик: {data.carrier} (ИНН {data.carrier_inn}), с другой стороны, "
        "заключили настоящий договор-заявку о нижеследующем:"
    )
    intro.runs[0].font.size = Pt(10)

    tbl = doc.add_table(rows=1, cols=2)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    hdr[0].text = "Условие перевозки"
    hdr[1].text = "Параметр"

    rows = [
        ("Пункт погрузки (Адрес погрузки)", data.loading_address),
        ("Пункт выгрузки (Адрес выгрузки)", data.unloading_address),
        ("Госномер тягача", data.truck_plate),
        ("Госномер прицепа", data.trailer_plate),
        ("Грузоподъемность ТС", data.truck_capacity),
        ("ФИО водителя", data.driver_name),
        ("Паспорт водителя (серия, номер)", data.driver_passport),
        ("Телефон водителя", data.driver_phone),
        ("Наименование груза", data.cargo_name),
        ("Масса груза (нетто)", data.cargo_weight),
        ("Объем груза", data.cargo_volume),
        ("Количество мест", data.cargo_places),
        ("Температурный режим", data.temperature),
        ("Особые условия перевозки", data.special_conditions),
        ("Стоимость перевозки", data.cost),
    ]

    for k, v in rows:
        row = tbl.add_row().cells
        row[0].text = k
        row[1].text = str(v)

    sig = doc.add_paragraph(
        "\nПодписи сторон:\nОт Заказчика: ___________ / М.П.        От Перевозчика: ___________ / М.П."
    )
    sig.runs[0].font.size = Pt(10)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(file_path))
