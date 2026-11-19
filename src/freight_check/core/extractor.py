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

# Регулярные выражения для прямого поиска реквизитов
_PLATE_REGEX = re.compile(r"\b([А-ЯA-Z]{1}\s*\d{3}\s*[А-ЯA-Z]{2}\s*\d{2,3})\b", re.IGNORECASE)
_TRAILER_PLATE_REGEX = re.compile(r"\b([А-ЯA-Z]{2}\s*\d{4}\s*\d{2,3})\b", re.IGNORECASE)
_PASSPORT_REGEX = re.compile(r"\b(\d{2}\s*\d{2}\s*\d{6}|\d{4}\s*\d{6})\b")
_SECTION_HEADING_REGEX = re.compile(r"^\s*\d+[а-яa-z]?\.\s+[^:]+$", re.IGNORECASE)
_PHONE_REGEX = re.compile(r"(?:\+7|8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")

# Словари якорных маркеров
_ANCHORS: dict[str, tuple[str, ...]] = {
    "truck_number": (
        "транспортноесредство@госномертягача",
        "госномер тягача",
        "госномертягача",
        "номер тягача",
        "гос. номер тягача",
        "госномер тс",
        "госномер",
        "гос. номер",
        "номер тс",
        "рег. знак",
        "регистрационный знак",
        "транспорт",
        "тягач",
    ),
    "trailer_number": (
        "транспортноесредство@госномерприцепа",
        "госномер прицепа",
        "госномерприцепа",
        "номер прицепа",
        "полуприцеп",
        "прицеп",
        "п/п",
    ),
    "truck_capacity_kg": (
        "транспортноесредство@грузоподъемность",
        "грузоподъемность тс",
        "грузоподъемность",
        "г/п",
        "паспортная г/п",
        "вместимость",
    ),
    "driver_name": (
        "водитель@фио",
        "водитель (фио)",
        "фио водителя",
        "водитель",
        "фио",
    ),
    "driver_passport": (
        "паспортсерияномер",
        "водитель@паспорт",
        "паспорт водителя",
        "серия и номер",
        "паспорт",
    ),
    "driver_phone": (
        "водитель@телефон",
        "телефон водителя",
        "тел. водителя",
        "контактный телефон водителя",
        "моб. водителя",
        "телефон",
        "тел.",
    ),
    "cargo_weight_kg": (
        "груз@масса",
        "массагруза",
        "масса груза (нетто)",
        "масса груза при взвешивании",
        "масса груза при сдаче",
        "масса груза",
        "масса нетто",
        "масса брутто",
        "масса",
        "вес груза",
        "вес",
    ),
    "cargo_volume_m3": (
        "груз@объем",
        "объемгруза",
        "объем груза",
        "объем",
        "куб.м",
        "м3",
    ),
    "cargo_places_count": (
        "груз@мест",
        "количествомест",
        "количество грузовых мест",
        "количество мест",
        "кол-во мест",
        "колмест",
        "грузовых мест",
        "мест",
        "паллет",
        "палл.",
    ),
    "loading_point": (
        "погрузка@адрес",
        "адреспогрузки",
        "адрес места погрузки",
        "адрес погрузки",
        "пункт погрузки",
        "место погрузки",
        "места погрузки",
        "прием (адрес погрузки)",
        "прием груза (адрес)",
        "погрузка",
    ),
    "unloading_point": (
        "выгрузка@адрес",
        "адресвыгрузки",
        "адрес места выгрузки",
        "адрес места разгрузки",
        "адрес выгрузки",
        "адрес разгрузки",
        "пункт выгрузки",
        "пункт разгрузки",
        "место выгрузки",
        "места выгрузки",
        "выдача (адрес выгрузки)",
        "выдача груза (адрес)",
        "выгрузка",
        "разгрузка",
    ),
    "consignee": (
        "грузополучатель",
        "заказчик",
        "грузоотправитель",
        "наименование организации",
    ),
    "temperature_conditions": (
        "груз@температура",
        "температурныйрежим",
        "температурный режим",
        "температура",
        "режим перевозки",
        "t°",
    ),
    "special_instructions": (
        "особые условия перевозки",
        "особые условия",
        "указания грузоотправителя по особым условиям перевозки",
        "особые отметки",
        "инструкции",
        "примечание",
    ),
}


class SemanticExtractor:
    """Извлекает сущности перевозки из сырого документа RawDocument."""

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
            "фио",
            "перевозки",
            "условия",
            "пункт",
            "адрес",
            "прием",
            "выдача",
            "параметр",
            "значение",
            "инн",
            "кпп",
            "наименование",
            "организации",
            "перевозчик",
            "заказчик",
            "раздел",
            "объем",
            "телефон",
            "тел",
            "моб",
            "контактный",
            "паспорт",
            "погрузка",
            "погрузки",
            "выгрузка",
            "выгрузки",
            "разгрузка",
            "разгрузки",
            "режим",
            "температура",
            "температурный",
            "особые",
            "отметки",
            "инструкции",
            "указания",
        }
    )

    def extract_package(self, raw_doc: RawDocument, document_role: str) -> DocumentPackage:
        pkg = DocumentPackage(
            document_role=document_role,
            file_path=str(raw_doc.file_path),
        )

        unified_fields = self._reconstruct_lines(raw_doc)

        if not unified_fields:
            pkg.parsing_errors.append("Документ не содержит распознанных текстовых данных")
            return pkg

        self._extract_by_anchors(unified_fields, pkg)
        self._extract_by_regex(unified_fields, pkg)

        return pkg

    def _reconstruct_lines(self, raw_doc: RawDocument) -> list[ExtractedField]:
        """Склеивает слова в строки ТОЛЬКО для PDF/сканов. Для XML, DOCX, XLSX сохраняет элементы."""
        all_fields: list[ExtractedField] = []

        if raw_doc.document_type not in ("pdf", "pdf_scan", "image"):
            for page in raw_doc.pages:
                all_fields.extend(page)
            return all_fields

        for page in raw_doc.pages:
            if not page:
                continue

            lines_dict: dict[int, list[ExtractedField]] = {}
            for field in page:
                box = field.source_box
                y = box[1] if box else 0

                found_y = None
                for base_y in lines_dict:
                    if abs(base_y - y) <= 8:
                        found_y = base_y
                        break

                if found_y is not None:
                    lines_dict[found_y].append(field)
                else:
                    lines_dict[y] = [field]

            for _, line_fields in sorted(lines_dict.items(), key=lambda item: item[0]):
                line_fields.sort(key=lambda f: f.source_box[0] if f.source_box else 0)
                full_text = " ".join(f.raw_value for f in line_fields).strip()
                min_conf = min(f.confidence for f in line_fields)
                first_b = line_fields[0].source_box
                last_b = line_fields[-1].source_box

                box = None
                if first_b and last_b:
                    box = (first_b[0], first_b[1], (last_b[0] + last_b[2]) - first_b[0], first_b[3])

                all_fields.append(
                    ExtractedField(
                        raw_value=full_text,
                        normalized_value=full_text,
                        confidence=min_conf,
                        source_box=box,
                    )
                )

        return all_fields

    def _extract_by_anchors(self, fields: list[ExtractedField], pkg: DocumentPackage) -> None:
        """Ищет маркеры в строках и извлекает значения."""
        n = len(fields)
        for i, field in enumerate(fields):
            text_lower = field.raw_value.lower()

            # Нумерованные заголовки таблицы ("2. Грузополучатель", "1а. Заказчик услуг...") — не метки полей.
            # Строки "Раздел N. <метка>" НЕ пропускаются: это настоящие метки, значение лежит рядом или на следующей строке.
            if _SECTION_HEADING_REGEX.match(text_lower):
                continue

            for target_field, keywords in _ANCHORS.items():
                if getattr(pkg, target_field) is not None:
                    continue

                if target_field == "driver_phone":
                    is_company_phone = any(
                        term in text_lower
                        for term in (
                            "контактный телефон",
                            "грузоотправител",
                            "грузополучател",
                            "организаци",
                        )
                    )
                    if is_company_phone and "водител" not in text_lower:
                        continue

                for kw in keywords:
                    pattern = r"(?:\b|^)" + re.escape(kw) + r"(?:\b|[:=@]|$)"
                    if re.search(pattern, text_lower):
                        val_str = self._extract_value_after_keyword(field.raw_value, kw)
                        field_confidence = field.confidence
                        box = field.source_box

                        # Разделение сдвоенной строки: «Количество мест / Объем: 24 палл. / 60 м3»
                        if target_field == "cargo_places_count":
                            m_places = re.search(
                                r"(\d+\s*(?:палл[а-я\.]*|мест[а-я]*|паллет[а-я]*|ящик[а-я]*|кор[а-я\.]*|шт[\.]*|поддон[а-я]*|связок|пачек|биг-бэг[а-я]*))",
                                field.raw_value,
                                re.IGNORECASE,
                            )
                            if m_places:
                                val_str = m_places.group(1).strip()

                        if target_field == "cargo_volume_m3":
                            m_vol = re.search(
                                r"(\d+(?:[.,]\d+)?\s*(?:м3|м³|куб[а-я\.]*))",
                                field.raw_value,
                                re.IGNORECASE,
                            )
                            if m_vol:
                                val_str = m_vol.group(1).strip()

                        # Если значение не найдено в текущей строке/ячейке, ищем в следующих элементах
                        if not val_str:
                            for offset in range(1, 10):
                                if i + offset >= n:
                                    break
                                next_f = fields[i + offset]
                                candidate = next_f.raw_value.strip()
                                if not candidate:
                                    continue

                                candidate_clean = re.sub(r"[^\w\s]", "", candidate).strip()
                                if not candidate_clean:
                                    continue

                                # Заголовки разделов (например, "Раздел 5", "8. Прием груза") пропускаем
                                is_section = bool(
                                    re.match(
                                        r"^(?:раздел\s*\d+|\d+[а-яa-z]?\.\s*[а-яА-Я])",
                                        candidate,
                                        re.IGNORECASE,
                                    )
                                )
                                if is_section:
                                    continue

                                candidate_words = re.findall(r"[а-яА-Яa-zA-Z0-9]+", candidate.lower())
                                has_digits = any(ch.isdigit() for ch in candidate)
                                non_digits = [w for w in candidate_words if not w.isdigit()]

                                # Строка является заголовком ТОЛЬКО если в ней нет цифр
                                # и все слова — служебные (тягача, (ФИО), водителя, нетто и т.д.)
                                is_label = bool(
                                    not has_digits
                                    and non_digits
                                    and all(w in self._HEADER_WORDS for w in non_digits)
                                )
                                if is_label:
                                    continue

                                is_no_trailer_str = target_field == "trailer_number" and any(
                                    w in candidate.lower() for w in ("без прицеп", "нет", "отсутств")
                                )
                                if (
                                        target_field in ("truck_number", "trailer_number")
                                        and not is_no_trailer_str
                                        and not has_digits
                                ):
                                    continue

                                val_str = candidate
                                field_confidence = min(field.confidence, next_f.confidence)
                                box = next_f.source_box
                                break

                        if val_str:
                            is_no_trailer_str = target_field == "trailer_number" and any(
                                w in val_str.lower() for w in ("без прицеп", "нет", "отсутств")
                            )
                            is_plate_field = target_field in ("truck_number", "trailer_number")
                            if is_plate_field and not is_no_trailer_str and not any(
                                    char.isdigit() for char in val_str):
                                continue

                            # Если строка объединяет места и объем (например, "20 паллет / 65 м3")
                            if target_field == "cargo_places_count":
                                m_places = re.search(
                                    r"(\d+\s*(?:палл[а-я\.]*|мест[а-я]*|паллет[а-я]*|ящик[а-я]*|кор[а-я\.]*|шт[\.]*|поддон[а-я]*|связок|пачек|биг-бэг[а-я]*))",
                                    val_str,
                                    re.IGNORECASE,
                                )
                                if m_places:
                                    val_str = m_places.group(1).strip()

                            if target_field == "cargo_volume_m3":
                                m_vol = re.search(
                                    r"(\d+(?:[.,]\d+)?\s*(?:м3|м³|куб[а-я\.]*))",
                                    val_str,
                                    re.IGNORECASE,
                                )
                                if m_vol:
                                    val_str = m_vol.group(1).strip()

                            normalized = self._normalize_by_type(target_field, val_str)
                            display_raw = normalized if target_field == "consignee" else val_str
                            setattr(
                                pkg,
                                target_field,
                                ExtractedField(
                                    raw_value=display_raw,
                                    normalized_value=normalized,
                                    confidence=field_confidence,
                                    source_box=box,
                                ),
                            )
                        break

    def _extract_by_regex(self, fields: list[ExtractedField], pkg: DocumentPackage) -> None:
        """Резервный поиск по регулярным выражениям."""
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
                # Очищаем строку от ИНН, чтобы 10-значный ИНН организации не принимался за паспорт
                clean_raw = re.sub(r"\bинн\s*[:=@]?\s*\d{10,12}\b", "", raw, flags=re.IGNORECASE)
                m = _PASSPORT_REGEX.search(clean_raw)
                if m:
                    val = m.group(1)
                    pkg.driver_passport = ExtractedField(
                        raw_value=val,
                        normalized_value=normalize_passport(val),
                        confidence=f.confidence,
                        source_box=f.source_box,
                    )

            if pkg.driver_phone is None:
                is_company = any(
                    term in raw.lower()
                    for term in ("контактный телефон", "грузоотправител", "грузополучател")
                )
                if not is_company or "водител" in raw.lower():
                    m = _PHONE_REGEX.search(raw)
                    if m:
                        val = m.group(0)
                        pkg.driver_phone = ExtractedField(
                            raw_value=val,
                            normalized_value=normalize_phone(val),
                            confidence=f.confidence,
                            source_box=f.source_box,
                        )

    @classmethod
    def _extract_value_after_keyword(cls, text: str, keyword: str) -> str:
        """Извлекает значение после ключевого слова, очищая XML-атрибуты и служебные знаки."""
        idx = text.lower().find(keyword.lower())
        if idx == -1:
            return ""

        after = text[idx + len(keyword):].strip()

        # Срезаем XML-атрибуты вида @ФИО=, @Адрес=, @Масса=
        after = re.sub(r"^@[а-яА-Яa-zA-Z0-9_]+=", "", after).strip()
        # Очищаем двоеточия, знаки равенства и закрывающие скобки: ")", "]:"
        after = re.sub(r"^[\)\]:—=\s]+", "", after).strip()
        # Тире отрезаем только если за ним идет пробел (сохраняем минус в '-2 °C')
        after = re.sub(r"^[-–]\s+", "", after).strip()

        alnum = re.findall(r"[а-яА-Яa-zA-Z0-9]+", after.lower())
        if not alnum:
            return ""

        words = [w for w in alnum if not w.isdigit()]
        if words and all(w in cls._HEADER_WORDS for w in words):
            return ""

        return after

    @staticmethod
    def _normalize_by_type(target_field: str, val_str: str) -> str:
        """Нормализация строкового значения по типу поля."""
        if target_field == "truck_number":
            return normalize_plate(val_str, is_trailer=False)
        if target_field == "trailer_number":
            if any(w in val_str.lower() for w in ("без прицеп", "нет", "отсутств", "одиночн")):
                return "Без прицепа"
            return normalize_plate(val_str, is_trailer=True)
        if target_field in ("cargo_weight_kg", "truck_capacity_kg"):
            w = normalize_weight(val_str)
            return f"{w} кг" if w is not None else val_str
        if target_field == "consignee":
            from freight_check.core.normalizers import clean_company_name

            return clean_company_name(val_str)
        if target_field == "driver_passport":
            return normalize_passport(val_str)
        if target_field == "driver_phone":
            return normalize_phone(val_str)
        return val_str.strip()


def extract_package_from_file(file_path: Path, role: str) -> DocumentPackage:
    from freight_check.parsers.router import ParserRouter

    raw_doc = ParserRouter.parse(file_path)
    extractor = SemanticExtractor()
    return extractor.extract_package(raw_doc, role)
