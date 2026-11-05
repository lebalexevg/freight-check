"""Модуль нормализации значений параметров рейса.

Реализует правила приведения госномеров к ГОСТ, конвертацию весовых категорий,
разделение адресных строк и очистку персональных идентификаторов водителя.
"""

import re

LATIN_TO_CYRILLIC: dict[str, str] = {
    "A": "А",
    "B": "В",
    "E": "Е",
    "K": "К",
    "M": "М",
    "H": "Н",
    "O": "О",
    "P": "Р",
    "C": "С",
    "T": "Т",
    "Y": "У",
    "X": "Х",
}

DIGIT_TO_LETTER: dict[str, str] = {"0": "О", "8": "В", "3": "З"}
LETTER_TO_DIGIT: dict[str, str] = {
    "О": "0",
    "O": "0",
    "В": "8",
    "B": "8",
    "З": "3",
}

_BUILDING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:дом|д)\b\.?\s*(\d+[а-яА-Яa-zA-Z]?(?:/\d+)?)", re.IGNORECASE),
    re.compile(r"\b(?:корпус|корп|к)\b\.?\s*(\d+[а-яА-Яa-zA-Z]?)", re.IGNORECASE),
    re.compile(r"\b(?:строение|стр)\b\.?\s*(\d+[а-яА-Яa-zA-Z]?)", re.IGNORECASE),
    re.compile(r"\b(?:литера|литер|лит)\b\.?\s*([а-яА-Яa-zA-Z\d]+)", re.IGNORECASE),
    re.compile(r"\b(?:сооружение|соор)\b\.?\s*(\d+[а-яА-Яa-zA-Z]?)", re.IGNORECASE),
    re.compile(r"\b(?:владение|вл)\b\.?\s*(\d+[а-яА-Яa-zA-Z]?)", re.IGNORECASE),
)


def normalize_plate(raw_value: str, is_trailer: bool = False) -> str:
    """Приводит автомобильный номер к кириллице и стандарту ГОСТ с коррекцией OCR.

    :param raw_value: Исходный текст госномера (например, "A 123 BC 77" или "AВ 1234 77").
    :param is_trailer: Флаг прицепа (маска 2 буквы + 4 цифры + регион).
    :return: Нормализованный госномер в верхнем регистре без разделителей.
    """
    if not raw_value:
        return ""

    cleaned = re.sub(r"[\s\-_./\\,]", "", raw_value).upper()

    chars = [LATIN_TO_CYRILLIC.get(ch, ch) for ch in cleaned]

    if not is_trailer and len(chars) in (8, 9):
        if chars[0] in DIGIT_TO_LETTER:
            chars[0] = DIGIT_TO_LETTER[chars[0]]

        for idx in range(1, 4):
            if chars[idx] in LETTER_TO_DIGIT:
                chars[idx] = LETTER_TO_DIGIT[chars[idx]]

        for idx in (4, 5):
            if chars[idx] in DIGIT_TO_LETTER:
                chars[idx] = DIGIT_TO_LETTER[chars[idx]]

        for idx in range(6, len(chars)):
            if chars[idx] in LETTER_TO_DIGIT:
                chars[idx] = LETTER_TO_DIGIT[chars[idx]]

    elif is_trailer and len(chars) in (8, 9):
        for idx in (0, 1):
            if chars[idx] in DIGIT_TO_LETTER:
                chars[idx] = DIGIT_TO_LETTER[chars[idx]]

        for idx in range(2, 6):
            if chars[idx] in LETTER_TO_DIGIT:
                chars[idx] = LETTER_TO_DIGIT[chars[idx]]

        for idx in range(6, len(chars)):
            if chars[idx] in LETTER_TO_DIGIT:
                chars[idx] = LETTER_TO_DIGIT[chars[idx]]

    return "".join(chars)


def normalize_weight(raw_value: str) -> int | None:
    """Нормализует значение массы груза или грузоподъемности к целому числу килограммов.

    :param raw_value: Исходная строка (например, "20 т", "22.5 тонн", "18 500 кг").
    :return: Масса в килограммах либо None, если число не распознано.
    """
    if not raw_value:
        return None

    text = raw_value.strip().lower().replace("\xa0", " ").replace(",", ".")

    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(" ", ""))
    if not match:
        return None

    try:
        val = float(match.group(1))
    except ValueError:
        return None

    is_tons = bool(re.search(r"(?:тн?|тонн[а-я]*|tn|ton)", text))

    if is_tons or (1.0 <= val <= 50.0 and "кг" not in text and "kg" not in text):
        return int(round(val * 1000))

    return int(round(val))


def normalize_passport(raw_value: str) -> str:
    """Извлекает и форматирует 10 цифр паспорта гражданина РФ (серия и номер)."""
    if not raw_value:
        return ""
    digits = re.sub(r"\D", "", raw_value)
    if len(digits) == 10:
        return f"{digits[:4]} {digits[4:]}"
    return digits


def normalize_phone(raw_value: str) -> str:
    """Приводит номер мобильного телефона к стандарту +7XXXXXXXXXX."""
    if not raw_value:
        return ""
    digits = re.sub(r"\D", "", raw_value)
    if len(digits) == 11 and digits.startswith(("7", "8")):
        return f"+7{digits[1:]}"
    if len(digits) == 10:
        return f"+7{digits}"
    return raw_value.strip()


def parse_address(raw_value: str) -> tuple[str, frozenset[str]]:
    """Разбивает адресную строку на географическую часть и строгие идентификаторы строений.

    :param raw_value: Исходная строка адреса.
    :return: Кортеж (географическая_часть, множество_идентификаторов_домов).
    """
    if not raw_value:
        return "", frozenset()

    text = raw_value.strip()

    identifiers: set[str] = set()
    for pattern in _BUILDING_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            identifiers.add(m.strip().lower())

    geo_part = text
    for pattern in _BUILDING_PATTERNS:
        geo_part = pattern.sub("", geo_part)

    geo_part = re.sub(r"[\s,;]+", " ", geo_part).strip().lower()

    geo_part = re.sub(
        r"\b(?:г|город|пос|пгт|с|село|д|деревня|обл|область|р-н|район|ул|улица|пр|пр-кт|проспект|ш|шоссе|пер|переулок|проезд|наб|набережная)\.?\b",
        "",
        geo_part,
    )
    geo_part = re.sub(r"\s+", " ", geo_part).strip()

    return geo_part, frozenset(identifiers)
