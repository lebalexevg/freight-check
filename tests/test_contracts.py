from freight_check.contracts import (
    DocumentPackage,
    ExtractedField,
    SessionReport,
    ValidationRow,
    ValidationStatus,
)


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
