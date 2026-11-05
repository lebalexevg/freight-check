from freight_check.contracts import DocumentPackage, ExtractedField, ValidationStatus
from freight_check.core.matcher import ValidationEngine


def test_scenario_1_full_match() -> None:
    """Сценарий 1: Корректный рейс — все поля совпадают."""
    order = DocumentPackage(
        document_role="order",
        file_path="order.pdf",
        truck_number=ExtractedField(
            raw_value="А 123 ВС 77", normalized_value="А123ВС77", confidence=1.0
        ),
        driver_name=ExtractedField(
            raw_value="Иванов Иван Иванович",
            normalized_value="Иванов Иван Иванович",
            confidence=1.0,
        ),
        driver_passport=ExtractedField(
            raw_value="4510 123456", normalized_value="4510 123456", confidence=1.0
        ),
        cargo_weight_kg=ExtractedField(
            raw_value="18.5 т", normalized_value="18500", confidence=1.0
        ),
        truck_capacity_kg=ExtractedField(
            raw_value="20 000 кг", normalized_value="20000", confidence=1.0
        ),
        unloading_point=ExtractedField(
            raw_value="г. Санкт-Петербург, Московский пр-кт, д. 100",
            normalized_value="г. Санкт-Петербург, Московский пр-кт, д. 100",
            confidence=1.0,
        ),
    )

    waybill = DocumentPackage(
        document_role="waybill",
        file_path="waybill.xml",
        truck_number=ExtractedField(
            raw_value="А123ВС77", normalized_value="А123ВС77", confidence=1.0
        ),
        driver_name=ExtractedField(
            raw_value="Иванов Иван Иванович",
            normalized_value="Иванов Иван Иванович",
            confidence=1.0,
        ),
        driver_passport=ExtractedField(
            raw_value="45 10 123456", normalized_value="4510 123456", confidence=1.0
        ),
        cargo_weight_kg=ExtractedField(
            raw_value="18 500 кг", normalized_value="18500", confidence=1.0
        ),
        unloading_point=ExtractedField(
            raw_value="Санкт-Петербург, Московский пр-т, д. 100",
            normalized_value="Санкт-Петербург, Московский пр-т, д. 100",
            confidence=1.0,
        ),
    )

    engine = ValidationEngine()
    report = engine.validate(order, waybill)

    assert report.overall_status == ValidationStatus.MATCH
    assert report.critical_errors_count == 0
    assert report.warnings_count == 0
    assert all(r.status == ValidationStatus.MATCH for r in report.rows)


def test_scenario_2_overload() -> None:
    """Сценарий 2: Критический перегруз — масса превышает грузоподъемность ТС."""
    order = DocumentPackage(
        document_role="order",
        file_path="order.pdf",
        truck_number=ExtractedField(
            raw_value="О 777 ОО 77", normalized_value="О777ОО77", confidence=1.0
        ),
        truck_capacity_kg=ExtractedField(
            raw_value="20 000 кг", normalized_value="20000", confidence=1.0
        ),
        cargo_weight_kg=ExtractedField(
            raw_value="22.5 т", normalized_value="22500", confidence=1.0
        ),
    )

    waybill = DocumentPackage(
        document_role="waybill",
        file_path="waybill.xml",
        truck_number=ExtractedField(
            raw_value="О777ОО77", normalized_value="О777ОО77", confidence=1.0
        ),
        cargo_weight_kg=ExtractedField(
            raw_value="22 500 кг", normalized_value="22500", confidence=1.0
        ),
    )

    engine = ValidationEngine()
    report = engine.validate(order, waybill)

    assert report.overall_status == ValidationStatus.CRITICAL
    assert report.critical_errors_count >= 1

    capacity_row = next(r for r in report.rows if r.parameter_name == "Грузоподъемность ТС")
    assert capacity_row.status == ValidationStatus.CRITICAL
    assert "превышает грузоподъемность" in capacity_row.explanation
    assert "2 500 кг" in capacity_row.explanation


def test_scenario_3_typos_in_identifiers() -> None:
    """Сценарий 3: Опечатки в номерах, паспорте и номере дома."""
    order = DocumentPackage(
        document_role="order",
        file_path="order.pdf",
        truck_number=ExtractedField(
            raw_value="А 123 ВС 77", normalized_value="А123ВС77", confidence=1.0
        ),
        driver_passport=ExtractedField(
            raw_value="4510 123456", normalized_value="4510 123456", confidence=1.0
        ),
        unloading_point=ExtractedField(
            raw_value="г. Москва, ул. Ленина, д. 15",
            normalized_value="г. Москва, ул. Ленина, д. 15",
            confidence=1.0,
        ),
    )

    waybill = DocumentPackage(
        document_role="waybill",
        file_path="waybill.xml",
        # Ошибка в госномере: 128 вместо 123
        truck_number=ExtractedField(
            raw_value="А 128 ВС 77", normalized_value="А128ВС77", confidence=1.0
        ),
        # Ошибка в паспорте: последняя цифра 7 вместо 6
        driver_passport=ExtractedField(
            raw_value="4510 123457", normalized_value="4510 123457", confidence=1.0
        ),
        # Ошибка в номере дома: 51 вместо 15
        unloading_point=ExtractedField(
            raw_value="г. Москва, ул. Ленина, д. 51",
            normalized_value="г. Москва, ул. Ленина, д. 51",
            confidence=1.0,
        ),
    )

    engine = ValidationEngine()
    report = engine.validate(order, waybill)

    assert report.overall_status == ValidationStatus.CRITICAL
    assert report.critical_errors_count == 3


def test_scenario_4_acceptable_warnings() -> None:
    """Сценарий 4: Допустимые расхождения (перестановка слов, допустимые сокращения)."""
    order = DocumentPackage(
        document_role="order",
        file_path="order.pdf",
        truck_number=ExtractedField(
            raw_value="А 123 ВС 77", normalized_value="А123ВС77", confidence=1.0
        ),
        driver_name=ExtractedField(
            raw_value="Козлов Дмитрий Сергеевич",
            normalized_value="Козлов Дмитрий Сергеевич",
            confidence=1.0,
        ),
        unloading_point=ExtractedField(
            raw_value="г. Екатеринбург, ул. 8 Марта, д. 210, литер А",
            normalized_value="г. Екатеринбург, ул. 8 Марта, д. 210, литер А",
            confidence=1.0,
        ),
    )

    waybill = DocumentPackage(
        document_role="waybill",
        file_path="waybill.xml",
        truck_number=ExtractedField(
            raw_value="А123ВС77", normalized_value="А123ВС77", confidence=1.0
        ),
        # Незначительная опечатка в имени: Дмитрии вместо Дмитрий (fuzz ratio в пределах 60..85%)
        driver_name=ExtractedField(
            raw_value="Козлов Дмитрии Сергеевич",
            normalized_value="Козлов Дмитрии Сергеевич",
            confidence=1.0,
        ),
        # Дом 210 совпал, но в накладной не указан литер А
        unloading_point=ExtractedField(
            raw_value="Екатеринбург, 8 Марта ул., дом 210",
            normalized_value="Екатеринбург, 8 Марта ул., дом 210",
            confidence=1.0,
        ),
    )

    engine = ValidationEngine()
    report = engine.validate(order, waybill)

    assert report.overall_status == ValidationStatus.WARNING
    assert report.critical_errors_count == 0
    assert report.warnings_count >= 1


def test_scenario_5_low_confidence_ocr() -> None:
    """Сценарий 5: Сомнительное считывание скан-образа (confidence < 0.70)."""
    order = DocumentPackage(
        document_role="order",
        file_path="order.pdf",
        truck_number=ExtractedField(
            raw_value="М 345 ТР 77", normalized_value="М345ТР77", confidence=0.95
        ),
        trailer_number=ExtractedField(
            raw_value="РВ 1234 77", normalized_value="РВ123477", confidence=0.95
        ),
    )

    waybill = DocumentPackage(
        document_role="waybill",
        file_path="waybill.jpg",
        truck_number=ExtractedField(
            raw_value="М345ТР77", normalized_value="М345ТР77", confidence=0.91
        ),
        # Распознано сомнительно (зашумленный скан, confidence = 0.61)
        trailer_number=ExtractedField(
            raw_value="РВ12347?", normalized_value="РВ123470", confidence=0.61
        ),
    )

    engine = ValidationEngine()
    report = engine.validate(order, waybill)

    assert report.overall_status == ValidationStatus.UNCERTAIN
    trailer_row = next(r for r in report.rows if r.parameter_name == "Госномер прицепа")
    assert trailer_row.status == ValidationStatus.UNCERTAIN
    assert "OCR" in trailer_row.explanation
