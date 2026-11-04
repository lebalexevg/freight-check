from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.dataset_generator.models import DocumentFields


def build_xml_waybill(file_path: Path, data: DocumentFields) -> None:
    """Создает XML титул ЭТрН (структура ГИС ЭПД / формат обмена ФНС)."""
    root = ET.Element(
        "Файл",
        ИдФайл=f"ON_TRNAKL_{data.doc_number}_{data.doc_date.replace('.', '')}",
        ВерсФорм="1.01",
        ВерсПрог="FreightCheck_Generator_v1.0",
    )
    doc_el = ET.SubElement(
        root,
        "Документ",
        ТипДок="ЭТрН",
        КНД="1110355",
        НомерНакладной=data.doc_number,
        ДатаНакладной=data.doc_date,
    )

    # 1. Грузоотправитель
    shipper_el = ET.SubElement(
        doc_el,
        "Грузоотправитель",
        НаимОрг=data.shipper,
        ИНН=data.shipper_inn,
        Адрес=data.loading_address,
    )
    ET.SubElement(shipper_el, "НаимОрг").text = data.shipper
    ET.SubElement(shipper_el, "ИНН").text = data.shipper_inn

    # 2. Грузополучатель
    consignee_el = ET.SubElement(
        doc_el,
        "Грузополучатель",
        НаимОрг=data.consignee,
        ИНН=data.consignee_inn,
        Адрес=data.unloading_address,
    )
    ET.SubElement(consignee_el, "НаимОрг").text = data.consignee
    ET.SubElement(consignee_el, "ИНН").text = data.consignee_inn

    # 3. Перевозчик и водитель
    carrier_el = ET.SubElement(
        doc_el,
        "Перевозчик",
        НаимОрг=data.carrier,
        ИНН=data.carrier_inn,
    )
    ET.SubElement(carrier_el, "НаимОрг").text = data.carrier
    ET.SubElement(carrier_el, "ИНН").text = data.carrier_inn

    driver_el = ET.SubElement(
        carrier_el,
        "Водитель",
        ФИО=data.driver_name,
        Паспорт=data.driver_passport,
        Телефон=data.driver_phone,
    )
    ET.SubElement(driver_el, "ФИО").text = data.driver_name
    ET.SubElement(driver_el, "ПаспортСерияНомер").text = data.driver_passport
    ET.SubElement(driver_el, "КонтактныйТелефон").text = data.driver_phone

    # 4. Транспортное средство
    trans_el = ET.SubElement(
        doc_el,
        "ТранспортноеСредство",
        ГосномерТягача=data.truck_plate,
        ГосномерПрицепа=data.trailer_plate,
        Грузоподъемность=data.truck_capacity,
    )
    ET.SubElement(trans_el, "ГосномерТягача").text = data.truck_plate
    ET.SubElement(trans_el, "ГосномерПрицепа").text = data.trailer_plate
    ET.SubElement(trans_el, "Грузоподъемность").text = data.truck_capacity

    # 5. Груз
    cargo_el = ET.SubElement(
        doc_el,
        "Груз",
        Наименование=data.cargo_name,
        Масса=data.cargo_weight,
        Мест=data.cargo_places,
        Объем=data.cargo_volume,
        Температура=data.temperature,
    )
    ET.SubElement(cargo_el, "НаименованиеГруза").text = data.cargo_name
    ET.SubElement(cargo_el, "МассаГруза").text = data.cargo_weight
    ET.SubElement(cargo_el, "КоличествоМест").text = data.cargo_places
    ET.SubElement(cargo_el, "Объем").text = data.cargo_volume
    ET.SubElement(cargo_el, "ТемпературныйРежим").text = data.temperature

    # 6. Прием и сдача груза (маршрут)
    loading_el = ET.SubElement(
        doc_el, "Погрузка", Адрес=data.loading_address, Дата=f"{data.doc_date} 09:00"
    )
    ET.SubElement(loading_el, "АдресПогрузки").text = data.loading_address

    unloading_el = ET.SubElement(
        doc_el, "Выгрузка", Адрес=data.unloading_address, Дата=f"{data.doc_date} 18:00"
    )
    ET.SubElement(unloading_el, "АдресВыгрузки").text = data.unloading_address

    tree = ET.ElementTree(root)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)
