"""Семантический анализатор документов (Information Extraction).

Осуществляет поиск якорных маркеров и извлечение ключевых реквизитов перевозки
из RawDocument в строго типизированный DocumentPackage.
"""

from __future__ import annotations

import re
from pathlib import Path

from freight_check.contracts import DocumentPackage, ExtractedField, RawDocument
from freight_check.core.normalizers import (
    normalize_passport,
    normalize_phone,
    normalize_plate,
    normalize_weight,
)

_PLATE_REGEX = re.compile(r"\b([А-ЯA-Z]{1}\s*\d{3}\s*[А-ЯA-Z]{2}\s*\d{2,3})\b", re.IGNORECASE)
_TRAILER_PLATE_REGEX = re.compile(r"\b([А-ЯA-Z]{2}\s*\d{4}\s*\d{2,3})\b", re.IGNORECASE)
_PASSPORT_REGEX = re.compile(r"\b(\d{2}\s*\d{2}\s*\d{6}|\d{4}\s*\d{6})\b")
_PHONE_REGEX = re.compile(r"(?:\+7|8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")

_ANCHORS: dict[str, tuple[str, ...]] = {
    "truck_number": ("тягач", "автомобиль", "госномер", "номер тс", "транспорт", "авто"),
    "trailer_number": ("прицеп", "полуприцеп", "номер прицепа", "п/п"),
    "truck_capacity_kg": ("грузоподъемность", "г/п", "паспортная г/п", "вместимость"),
    "driver_name": ("водитель", "фио водителя", "фио", "управляющий"),
    "driver_passport": ("паспорт", "серия и номер паспорта", "уд. личности", "документ"),
    "driver_phone": ("телефон", "тел", "контактный телефон", "моб"),
    "cargo_weight_kg": ("масса", "вес", "масса груза", "вес груза", "нетто", "масса нетто"),
    "cargo_volume_m3": ("объем", "объем груза", "куб.м", "м3"),
    "cargo_places_count": ("количество мест", "мест", "паллет", "грузовых мест"),
    "loading_point": ("погрузка", "адрес погрузки", "пункт погрузки", "грузоотправитель"),
    "unloading_point": (
        "выгрузка",
        "адрес выгрузки",
        "пункт выгрузки",
        "грузополучатель",
        "доставка",
    ),
    "temperature_conditions": ("температурный режим", "температура", "режим перевозки", "t°"),
    "special_instructions": ("особые отметки", "инструкции", "примечание"),
}


class SemanticExtractor:
    """Извлекает сущности перевозки из сырого документа RawDocument."""

    def extract_package(self, raw_doc: RawDocument, document_role: str) -> DocumentPackage:
        """Формирует DocumentPackage на основе страниц и блоков RawDocument.

        :param raw_doc: Сырой документ от парсера.
        :param document_role: Роль документа ("order" или "waybill").
        """
        all_fields: list[ExtractedField] = []
        for page in raw_doc.pages:
            all_fields.extend(page)

        pkg = DocumentPackage(
            document_role=document_role,
            file_path=str(raw_doc.file_path),
        )

        if not all_fields:
            pkg.parsing_errors.append("Документ не содержит распознанных текстовых данных")
            return pkg

        self._extract_by_anchors(all_fields, pkg)

        self._extract_by_regex(all_fields, pkg)

        return pkg

    def _extract_by_anchors(self, fields: list[ExtractedField], pkg: DocumentPackage) -> None:
        """Ищет маркеры в тексте и привязывает соседние значения."""
        n = len(fields)
        for i, field in enumerate(fields):
            text_lower = field.raw_value.lower()

            for target_field, keywords in _ANCHORS.items():
                if getattr(pkg, target_field) is not None:
                    continue

                for kw in keywords:
                    if kw in text_lower:
                        val_str = self._extract_value_after_keyword(field.raw_value, kw)
                        field_confidence = field.confidence
                        box = field.source_box

                        if not val_str and i + 1 < n:
                            next_f = fields[i + 1]
                            val_str = next_f.raw_value.strip()
                            field_confidence = min(field.confidence, next_f.confidence)
                            box = next_f.source_box

                        if val_str:
                            normalized = self._normalize_by_type(target_field, val_str)
                            setattr(
                                pkg,
                                target_field,
                                ExtractedField(
                                    raw_value=val_str,
                                    normalized_value=normalized,
                                    confidence=field_confidence,
                                    source_box=box,
                                ),
                            )
                        break

    def _extract_by_regex(self, fields: list[ExtractedField], pkg: DocumentPackage) -> None:
        """Фоллбэк: ищет значения по regex-паттернам, если якорные слова не встретились."""
        for f in fields:
            raw = f.raw_value

            if pkg.truck_number is None:
                m = _PLATE_REGEX.search(raw)
                if m:
                    val = m.group(1)
                    pkg.truck_number = ExtractedField(
                        raw_value=val,
                        normalized_value=normalize_plate(val, is_trailer=False),
                        confidence=f.confidence,
                        source_box=f.source_box,
                    )

            if pkg.trailer_number is None:
                m = _TRAILER_PLATE_REGEX.search(raw)
                if m:
                    val = m.group(1)
                    pkg.trailer_number = ExtractedField(
                        raw_value=val,
                        normalized_value=normalize_plate(val, is_trailer=True),
                        confidence=f.confidence,
                        source_box=f.source_box,
                    )

            if pkg.driver_passport is None:
                m = _PASSPORT_REGEX.search(raw)
                if m:
                    val = m.group(1)
                    pkg.driver_passport = ExtractedField(
                        raw_value=val,
                        normalized_value=normalize_passport(val),
                        confidence=f.confidence,
                        source_box=f.source_box,
                    )

            if pkg.driver_phone is None:
                m = _PHONE_REGEX.search(raw)
                if m:
                    val = m.group(0)
                    pkg.driver_phone = ExtractedField(
                        raw_value=val,
                        normalized_value=normalize_phone(val),
                        confidence=f.confidence,
                        source_box=f.source_box,
                    )

    _HEADER_WORDS: frozenset[str] = frozenset(
        {
            "тягача",
            "тс",
            "авто",
            "автомобиля",
            "прицепа",
            "полуприцепа",
            "водителя",
            "груза",
            "нетто",
            "брутто",
            "грузоподъемность",
            "паспорта",
            "номер",
            "данные",
            "серия",
            "рейса",
            "заявка",
            "транспорт",
            "масса",
            "вес",
        }
    )

    @classmethod
    def _extract_value_after_keyword(cls, text: str, keyword: str) -> str:
        """Извлекает значение из строки после ключевого слова.

        Если строка заканчивается двоеточием или содержит только заголовочные слова
        (например, 'Госномер тягача:'), возвращает пустую строку, чтобы значение
        было взято из следующей смежной ячейки.
        """
        if ":" in text or "=" in text:
            delim = ":" if ":" in text else "="
            parts = text.split(delim, 1)
            val = parts[1].strip()
            return val

        idx = text.lower().find(keyword)
        if idx == -1:
            return ""
        after = text[idx + len(keyword) :].strip()
        after = re.sub(r"^[:=\-—–\s]+", "", after).strip()

        words = re.findall(r"[а-яА-Яa-zA-Z]+", after.lower())
        if not words or all(w in cls._HEADER_WORDS for w in words):
            return ""

        return after

    @staticmethod
    def _normalize_by_type(target_field: str, val_str: str) -> str:
        """Нормализует строковое значение в зависимости от типа поля."""
        if target_field == "truck_number":
            return normalize_plate(val_str, is_trailer=False)
        if target_field == "trailer_number":
            return normalize_plate(val_str, is_trailer=True)
        if target_field in ("cargo_weight_kg", "truck_capacity_kg"):
            w = normalize_weight(val_str)
            return f"{w} кг" if w is not None else val_str
        if target_field == "driver_passport":
            return normalize_passport(val_str)
        if target_field == "driver_phone":
            return normalize_phone(val_str)
        return val_str.strip()


def extract_package_from_file(file_path: Path, role: str) -> DocumentPackage:
    """Удобная функция сквозного извлечения: выбор парсера -> извлечение пакета."""
    from freight_check.parsers.router import ParserRouter

    raw_doc = ParserRouter.parse(file_path)
    extractor = SemanticExtractor()
    return extractor.extract_package(raw_doc, role)
