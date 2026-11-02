from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ValidationStatus(StrEnum):
    """Статусы результатов сопоставления реквизитов."""

    # Полное совпадение реквизитов
    MATCH = "MATCH"

    # Критическое несовпадение реквизитов
    CRITICAL = "CRITICAL"

    # Допустимое несовпадение реквизитов
    WARNING = "WARNING"

    # Неопределенный статус сопоставления реквизитов
    UNCERTAIN = "UNCERTAIN"


@dataclass(slots=True, frozen=True)
class ExtractedField:
    """Атомарное значение поля, извлеченное из документа."""

    raw_value: str
    normalized_value: str
    confidence: float
    source_box: tuple[int, int, int, int] | None = None


@dataclass(slots=True)
class DocumentPackage:
    """Пакет реквизитов, извлеченных из одного документа."""

    document_role: str
    file_path: str
    truck_number: ExtractedField | None = None
    trailer_number: ExtractedField | None = None
    truck_capacity_kg: ExtractedField | None = None
    driver_name: ExtractedField | None = None
    driver_passport: ExtractedField | None = None
    driver_phone: ExtractedField | None = None
    cargo_weight_kg: ExtractedField | None = None
    cargo_volume_m3: ExtractedField | None = None
    cargo_places_count: ExtractedField | None = None
    loading_point: ExtractedField | None = None
    unloading_point: ExtractedField | None = None
    temperature_conditions: ExtractedField | None = None
    special_instructions: ExtractedField | None = None
    parsing_errors: list[str] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ValidationRow:
    """Строка отчёта сопоставления конкретного параметра рейса."""

    parameter_name: str
    order_value: str
    waybill_value: str
    status: ValidationStatus
    explanation: str


@dataclass(slots=True)
class SessionReport:
    """Итоговый отчет сессии валидации для передачи в UI."""

    overall_status: ValidationStatus
    critical_errors_count: int
    warnings_count: int
    processing_time_ms: int
    rows: list[ValidationRow] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class RawDocument:
    """Сырые извлеченные данные. Промежуточный слой между парсерами и семантическим извлечением."""

    file_path: Path
    pages: list[list[ExtractedField]]
    document_type: str
    metadata: dict = field(default_factory=dict)
