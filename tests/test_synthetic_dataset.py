from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.dataset_generator import generate_synthetic_dataset

from freight_check.contracts import RawDocument, ValidationStatus
from freight_check.parsers.ocr_pipeline import OCRPipeline
from freight_check.parsers.router import ParserRouter


@pytest.fixture(scope="session")
def dataset_root() -> Path:
    """Возвращает путь к синтетическому набору, создавая его при необходимости."""
    root = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synthetic_dataset"
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        generate_synthetic_dataset(root)
    return root


@pytest.fixture(scope="session")
def manifest(dataset_root: Path) -> dict:
    """Загружает манифест синтетического набора."""
    manifest_path = dataset_root / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def test_synthetic_dataset_scenarios_and_files(dataset_root: Path, manifest: dict) -> None:
    """Проверка структуры сценариев и физических файлов синтетического набора."""
    scenarios = manifest.get("scenarios", {})
    assert len(scenarios) == 5

    total_pairs = 0
    max_file_size = 50 * 1024 * 1024

    for scen_id, scen_info in scenarios.items():
        pairs = scen_info.get("pairs", [])
        assert len(pairs) == 3, f"В сценарии {scen_id} ожидалось 3 пары, получено {len(pairs)}"
        total_pairs += len(pairs)

        for pair in pairs:
            order_path = dataset_root / pair["order_file"]
            waybill_path = dataset_root / pair["waybill_file"]

            assert order_path.exists(), f"Файл не найден: {order_path}"
            assert waybill_path.exists(), f"Файл не найден: {waybill_path}"

            assert 0 < order_path.stat().st_size <= max_file_size
            assert 0 < waybill_path.stat().st_size <= max_file_size

    assert total_pairs == 15


def test_synthetic_dataset_manifest_statuses(manifest: dict) -> None:
    """Проверка валидности статусов сопоставления в манифесте."""
    valid_statuses = {s.value for s in ValidationStatus}

    for _scen_id, scen_info in manifest.get("scenarios", {}).items():
        for pair in scen_info.get("pairs", []):
            overall_status = pair.get("expected_overall_status")
            assert overall_status in valid_statuses

            for row in pair.get("expected_rows", []):
                assert row.get("status") in valid_statuses


def test_synthetic_dataset_router_parsing(dataset_root: Path, manifest: dict) -> None:
    """Проверка успешного парсинга всех 30 файлов через ParserRouter."""
    for _scen_id, scen_info in manifest.get("scenarios", {}).items():
        for pair in scen_info.get("pairs", []):
            order_path = dataset_root / pair["order_file"]
            waybill_path = dataset_root / pair["waybill_file"]

            raw_order = ParserRouter.parse(order_path)
            assert isinstance(raw_order, RawDocument)
            assert len(raw_order.pages) > 0
            assert len(raw_order.pages[0]) > 0

            raw_waybill = ParserRouter.parse(waybill_path)
            assert isinstance(raw_waybill, RawDocument)
            assert len(raw_waybill.pages) > 0
            assert len(raw_waybill.pages[0]) > 0


def test_synthetic_dataset_ocr_pipeline(dataset_root: Path) -> None:
    """Проверка оптического распознавания скан-образов сценария 5."""
    scen_5_dir = dataset_root / "scenario_5_uncertain"

    scan_files = [
        scen_5_dir / "pair_5_1_waybill.png",
        scen_5_dir / "pair_5_2_waybill.pdf",
        scen_5_dir / "pair_5_3_waybill.jpg",
    ]

    for scan_file in scan_files:
        assert scan_file.exists()
        parser = ParserRouter.get_parser(scan_file)
        assert isinstance(parser, OCRPipeline)

        raw_doc = parser.parse(scan_file)
        assert isinstance(raw_doc, RawDocument)
        flat_fields = [f for page in raw_doc.pages for f in page]
        assert len(flat_fields) > 0
