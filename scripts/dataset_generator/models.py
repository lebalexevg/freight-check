from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DocumentFields:
    """Реквизиты рейса для генерации документов."""

    doc_number: str
    doc_date: str
    shipper: str
    consignee: str
    carrier: str
    truck_plate: str
    trailer_plate: str
    truck_capacity: str
    driver_name: str
    driver_passport: str
    driver_phone: str
    cargo_name: str
    cargo_weight: str
    cargo_volume: str
    cargo_places: str
    loading_address: str
    unloading_address: str
    temperature: str = "Не требуется"
    special_conditions: str = "Стандартные условия"
    shipper_inn: str = "7701234567"
    consignee_inn: str = "7809876543"
    carrier_inn: str = "1655112233"
    cost: str = "85 000 руб."


@dataclass(slots=True)
class ExpectedValidationRow:
    """Ожидаемая строка сопоставления параметра."""

    parameter_name: str
    order_value: str
    waybill_value: str
    status: str
    explanation: str


@dataclass(slots=True)
class SyntheticPairSpec:
    """Спецификация пары документов синтетического набора."""

    pair_id: str
    scenario_id: str
    scenario_name: str
    description: str
    order_filename: str
    waybill_filename: str
    order_format: str
    waybill_format: str
    order_data: DocumentFields
    waybill_data: DocumentFields
    expected_overall_status: str
    expected_critical_count: int
    expected_warnings_count: int
    expected_uncertain_count: int
    expected_rows: list[ExpectedValidationRow] = field(default_factory=list)
    degraded_field_key: str | None = None
