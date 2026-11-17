from __future__ import annotations

import csv
from pathlib import Path

from scripts.dataset_generator.models import DocumentFields


def build_csv_order(file_path: Path, data: DocumentFields) -> None:
    """Создает файл CSV с параметрами заявки."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Документ", f"Заявка на перевозку груза № {data.doc_number}"])
        writer.writerow(["Дата", data.doc_date])
        writer.writerow(["Заказчик", data.shipper])
        writer.writerow(["Перевозчик", data.carrier])
        writer.writerow([])
        writer.writerow(["Параметр", "Значение"])
        writer.writerow(["Адрес погрузки", data.loading_address])
        writer.writerow(["Адрес выгрузки", data.unloading_address])
        writer.writerow(["Госномер тягача", data.truck_plate])
        writer.writerow(["Госномер прицепа", data.trailer_plate])
        writer.writerow(["Грузоподъемность ТС", data.truck_capacity])
        writer.writerow(["ФИО водителя", data.driver_name])
        writer.writerow(["Паспорт водителя", data.driver_passport])
        writer.writerow(["Телефон водителя", data.driver_phone])
        writer.writerow(["Наименование груза", data.cargo_name])
        writer.writerow(["Масса груза (нетто)", data.cargo_weight])
        writer.writerow(["Объем груза", data.cargo_volume])
        writer.writerow(["Количество мест", data.cargo_places])
        writer.writerow(["Температурный режим", data.temperature])
        writer.writerow(["Особые условия", data.special_conditions])
        writer.writerow(["Стоимость", data.cost])
