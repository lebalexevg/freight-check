"""Модуль ядра: семантика, нормализация и сопоставление."""

from freight_check.core.extractor import SemanticExtractor, extract_package_from_file
from freight_check.core.matcher import ValidationEngine
from freight_check.core.normalizers import (
    normalize_passport,
    normalize_phone,
    normalize_plate,
    normalize_weight,
    parse_address,
)

__all__ = [
    "SemanticExtractor",
    "ValidationEngine",
    "extract_package_from_file",
    "normalize_passport",
    "normalize_phone",
    "normalize_plate",
    "normalize_weight",
    "parse_address",
]
