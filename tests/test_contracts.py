import tomllib
from pathlib import Path

import freight_check
from freight_check.contracts import (
    DocumentPackage,
    ExtractedField,
    SessionReport,
    ValidationRow,
    ValidationStatus,
)
from freight_check.ui.about_dialog import APP_VERSION


def test_extracted_field_creation() -> None:
    field = ExtractedField(
        raw_value="А 123 ВС 77",
        normalized_value="А123ВС77",
        confidence=0.98,
        source_box=(10, 20, 100, 30),
    )

    assert field.normalized_value == "А123ВС77"
    assert field.confidence == 0.98


def test_session_report_structure() -> None:
    row = ValidationRow(
        parameter_name="Масса груза",
        order_value="20 000 кг",
        waybill_value="15 000 кг",
        status=ValidationStatus.CRITICAL,
        explanation="Масса груза превышает грузоподъемность ТС",
    )
    report = SessionReport(
        overall_status=ValidationStatus.CRITICAL,
        critical_errors_count=1,
        warnings_count=0,
        processing_time_ms=120,
        rows=[row],
    )

    assert report.overall_status == ValidationStatus.CRITICAL
    assert len(report.rows) == 1
    assert report.rows[0].status == ValidationStatus.CRITICAL


def test_document_package_defaults() -> None:
    package = DocumentPackage(document_role="order", file_path="test_order.xlsx")

    assert package.truck_number is None
    assert package.parsing_errors == []


def test_version_consistency() -> None:
    """Проверка единого источника правды для версии и издателей приложения."""
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project_version = data["project"]["version"]
    assert freight_check.__version__ == project_version
    assert project_version == APP_VERSION
    assert "Alexander Lebedev" in freight_check.__author__
    assert "Egor Hotenov" in freight_check.__author__

    authors = data["project"].get("authors", [])
    author_names = [a["name"] for a in authors if "name" in a]
    assert "Alexander Lebedev" in author_names
    assert "Egor Hotenov" in author_names
