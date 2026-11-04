from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from scripts.dataset_generator.builders.common import get_pil_font
from scripts.dataset_generator.models import DocumentFields


def render_waybill_to_pil(
    data: DocumentFields,
    degraded_field_key: str | None = None,
) -> Image.Image:
    """Отрисовывает страницу Транспортной накладной по разделам ПП № 2200."""
    width, height = 1200, 1600
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    font_title = get_pil_font(28)
    font_sub = get_pil_font(18)
    font_sec = get_pil_font(20)
    font_body = get_pil_font(19)

    draw.rectangle([(25, 25), (width - 25, height - 25)], outline="black", width=2)

    draw.text(
        (50, 45),
        f"ТРАНСПОРТНАЯ НАКЛАДНАЯ № {data.doc_number}",
        fill="black",
        font=font_title,
    )
    draw.text(
        (50, 85),
        f"Дата составления: {data.doc_date} г. (Форма по Постановлению Правительства РФ № 2200)",
        fill="gray",
        font=font_sub,
    )
    draw.line([(40, 115), (width - 40, 115)], fill="black", width=2)

    fields_list = [
        ("shipper", "Раздел 1. Грузоотправитель", f"{data.shipper}, ИНН {data.shipper_inn}"),
        ("consignee", "Раздел 2. Грузополучатель", f"{data.consignee}, ИНН {data.consignee_inn}"),
        ("cargo_name", "Раздел 3. Наименование груза", data.cargo_name),
        ("cargo_weight", "Раздел 3. Масса груза (нетто)", data.cargo_weight),
        (
            "cargo_places",
            "Раздел 3. Количество мест / Объем",
            f"{data.cargo_places} / {data.cargo_volume}",
        ),
        ("temperature", "Раздел 5. Температурный режим", data.temperature),
        ("carrier", "Раздел 6. Перевозчик", f"{data.carrier}, ИНН {data.carrier_inn}"),
        ("driver_name", "Раздел 6. Водитель (ФИО)", data.driver_name),
        ("driver_passport", "Раздел 6. Паспорт водителя", data.driver_passport),
        ("driver_phone", "Раздел 6. Телефон водителя", data.driver_phone),
        ("truck_plate", "Раздел 7. Госномер тягача", data.truck_plate),
        ("trailer_plate", "Раздел 7. Госномер прицепа", data.trailer_plate),
        ("truck_capacity", "Раздел 7. Грузоподъемность ТС", data.truck_capacity),
        ("loading_address", "Раздел 8. Прием груза (Адрес)", data.loading_address),
        ("unloading_address", "Раздел 10. Выдача груза (Адрес)", data.unloading_address),
        ("cost", "Раздел 12. Стоимость услуг", data.cost),
    ]

    y = 135
    step = 85

    for key, label, value in fields_list:
        is_target_degraded = degraded_field_key == key
        draw.text((50, y), label, fill="navy", font=font_sec)

        val_y = y + 28
        val_str = str(value)

        if is_target_degraded:
            patch_w, patch_h = 800, 42
            patch = Image.new("RGB", (patch_w, patch_h), "white")
            pdraw = ImageDraw.Draw(patch)
            pdraw.text((5, 2), val_str, fill="black", font=font_body)

            down_w = max(10, int(patch_w * 0.18))
            down_h = max(5, int(patch_h * 0.18))
            small = patch.resize((down_w, down_h), Image.Resampling.BILINEAR)
            degraded_patch = small.resize((patch_w, patch_h), Image.Resampling.BILINEAR)
            degraded_patch = degraded_patch.filter(ImageFilter.GaussianBlur(radius=1.1))

            img.paste(degraded_patch, (50, val_y))
        else:
            draw.text((50, val_y), val_str, fill="black", font=font_body)

        draw.line([(50, y + 75), (width - 50, y + 75)], fill=(220, 220, 220), width=1)
        y += step

    return img


def build_scan_image(
    file_path: Path,
    data: DocumentFields,
    degraded_field_key: str | None = None,
    image_format: str = "PNG",
) -> None:
    """Создает скан-образ накладной (PNG или JPG)."""
    img = render_waybill_to_pil(data, degraded_field_key)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if image_format.upper() in ("JPG", "JPEG"):
        img.convert("RGB").save(file_path, format="JPEG", quality=45)
    else:
        img.save(file_path, format="PNG")


def build_scanned_pdf(
    file_path: Path,
    data: DocumentFields,
    degraded_field_key: str | None = None,
) -> None:
    """Создает растровый PDF без текстового слоя для распознавания через OCR."""
    img = render_waybill_to_pil(data, degraded_field_key)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(str(file_path), format="PDF")
