from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from scripts.dataset_generator.builders import (
    build_csv_order,
    build_docx_order,
    build_docx_waybill,
    build_pdf_order,
    build_pdf_waybill,
    build_scan_image,
    build_scanned_pdf,
    build_xlsx_order,
    build_xlsx_waybill,
    build_xml_waybill,
)
from scripts.dataset_generator.scenarios import get_all_specs


def generate_synthetic_dataset(output_dir: Path) -> dict[str, Any]:
    """Генерирует 15 пар документов синтетического набора и manifest.json."""
    specs = get_all_specs()
    manifest_data: dict[str, Any] = {
        "version": "1.0",
        "description": "Синтетический тестовый набор документов (15 пар по 5 сценариям)",
        "scenarios": {},
    }

    scenario_folders = {
        "scenario_1": "scenario_1_match",
        "scenario_2": "scenario_2_overload",
        "scenario_3": "scenario_3_typos",
        "scenario_4_warnings": "scenario_4_warnings",
        "scenario_4": "scenario_4_warnings",
        "scenario_5": "scenario_5_uncertain",
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        folder_name = scenario_folders[spec.scenario_id]
        scenario_dir = output_dir / folder_name
        scenario_dir.mkdir(parents=True, exist_ok=True)

        order_path = scenario_dir / spec.order_filename
        waybill_path = scenario_dir / spec.waybill_filename

        # Генерация заявки (Order)
        if spec.order_format == "docx":
            build_docx_order(order_path, spec.order_data)
        elif spec.order_format == "xlsx":
            build_xlsx_order(order_path, spec.order_data)
        elif spec.order_format == "csv":
            build_csv_order(order_path, spec.order_data)
        elif spec.order_format == "pdf":
            build_pdf_order(order_path, spec.order_data)
        else:
            raise ValueError(f"Неподдерживаемый формат заявки: {spec.order_format}")

        # Генерация накладной (Waybill)
        if spec.waybill_format == "xml":
            build_xml_waybill(waybill_path, spec.waybill_data)
        elif spec.waybill_format == "xlsx":
            build_xlsx_waybill(waybill_path, spec.waybill_data)
        elif spec.waybill_format == "docx":
            build_docx_waybill(waybill_path, spec.waybill_data)
        elif spec.waybill_format == "pdf":
            build_pdf_waybill(waybill_path, spec.waybill_data)
        elif spec.waybill_format == "png":
            build_scan_image(
                waybill_path,
                spec.waybill_data,
                degraded_field_key=spec.degraded_field_key,
                image_format="PNG",
            )
        elif spec.waybill_format == "jpg":
            build_scan_image(
                waybill_path,
                spec.waybill_data,
                degraded_field_key=spec.degraded_field_key,
                image_format="JPG",
            )
        elif spec.waybill_format == "pdf_scan":
            build_scanned_pdf(
                waybill_path,
                spec.waybill_data,
                degraded_field_key=spec.degraded_field_key,
            )
        else:
            raise ValueError(f"Неподдерживаемый формат накладной: {spec.waybill_format}")

        scen_key = spec.scenario_id
        if scen_key not in manifest_data["scenarios"]:
            manifest_data["scenarios"][scen_key] = {
                "scenario_name": spec.scenario_name,
                "pairs": [],
            }

        manifest_data["scenarios"][scen_key]["pairs"].append(
            {
                "pair_id": spec.pair_id,
                "description": spec.description,
                "order_file": f"{folder_name}/{spec.order_filename}",
                "waybill_file": f"{folder_name}/{spec.waybill_filename}",
                "order_format": spec.order_format,
                "waybill_format": spec.waybill_format,
                "expected_overall_status": spec.expected_overall_status,
                "expected_critical_count": spec.expected_critical_count,
                "expected_warnings_count": spec.expected_warnings_count,
                "expected_uncertain_count": spec.expected_uncertain_count,
                "expected_rows": [asdict(r) for r in spec.expected_rows],
            }
        )

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    return manifest_data


__all__ = ["generate_synthetic_dataset"]
