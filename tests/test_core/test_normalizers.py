from freight_check.core.normalizers import (
    normalize_passport,
    normalize_phone,
    normalize_plate,
    normalize_weight,
    parse_address,
)


def test_normalize_plate_truck_basic() -> None:
    # Очистка пробелов и приведение к верхнему регистру
    assert normalize_plate("а 123 вс 77") == "А123ВС77"
    assert normalize_plate("А-123-ВС-77") == "А123ВС77"


def test_normalize_plate_truck_latin_transliteration() -> None:
    # Латинские буквы A, B, C, E, H, K, M, O, P, T, X, Y -> русские аналоги
    assert normalize_plate("A123BC77") == "А123ВС77"
    assert normalize_plate("M777OP777") == "М777ОР777"
    assert normalize_plate("y123tx199") == "У123ТХ199"


def test_normalize_plate_truck_ocr_mistakes_gost_mask() -> None:
    # Маска легкового/грузового авто: Буква-Цифра-Цифра-Цифра-Буква-Буква-Регион
    # Позиция 0: цифра '0' -> буква 'О'
    assert normalize_plate("0123ВС77") == "О123ВС77"
    # Позиции 1-3: буква 'О' -> цифра '0'
    assert normalize_plate("АО23ВС77") == "А023ВС77"
    # Позиции 1-3: буква 'В' -> цифра '8'
    assert normalize_plate("А1В3ВС77") == "А183ВС77"
    # Позиции 4-5: цифра '8' -> буква 'В'
    assert normalize_plate("А1238С77") == "А123ВС77"
    # Позиции 4-5: цифра '0' -> буква 'О'
    assert normalize_plate("А1230С77") == "А123ОС77"


def test_normalize_plate_trailer() -> None:
    # Маска прицепа: Буква-Буква-Цифра-Цифра-Цифра-Цифра-Регион
    assert normalize_plate("ве 4567 77", is_trailer=True) == "ВЕ456777"
    assert normalize_plate("BE 4567 77", is_trailer=True) == "ВЕ456777"
    # Оптическая пара: '0' на месте буквы -> 'О', 'В' на месте цифры -> '8'
    assert normalize_plate("0Е 45В7 77", is_trailer=True) == "ОЕ458777"


def test_normalize_weight() -> None:
    # Явные тонны с суффиксами
    assert normalize_weight("20 т") == 20000
    assert normalize_weight("22.5 т") == 22500
    assert normalize_weight("22,5 тн") == 22500
    assert normalize_weight("18.5 тонн") == 18500

    # Килограммы
    assert normalize_weight("20 000 кг") == 20000
    assert normalize_weight("18500кг") == 18500

    # Эвристика п. 3.2: числа от 1 до 50 без указания кг трактуются как тонны
    assert normalize_weight("20") == 20000
    assert normalize_weight("15.5") == 15500

    # Большие числа без единиц считаются килограммами
    assert normalize_weight("18500") == 18500

    # Пустые / невалидные значения
    assert normalize_weight("") is None
    assert normalize_weight("нет данных") is None


def test_normalize_passport() -> None:
    assert normalize_passport("45 10 123456") == "4510 123456"
    assert normalize_passport("4510-123456") == "4510 123456"
    assert normalize_passport("4510123456") == "4510 123456"
    assert normalize_passport("") == ""


def test_normalize_phone() -> None:
    assert normalize_phone("+7 (999) 111-22-33") == "+79991112233"
    assert normalize_phone("89991112233") == "+79991112233"
    assert normalize_phone("9991112233") == "+79991112233"
    assert normalize_phone("") == ""


def test_parse_address() -> None:
    # Извлечение номеров домов/строений
    geo, blds = parse_address("г. Москва, ул. Ленина, д. 15, стр. 2")
    assert "15" in blds
    assert "2" in blds
    assert "москва" in geo
    assert "ленина" in geo

    # Корпус и литера
    geo2, blds2 = parse_address("г. Екатеринбург, ул. 8 Марта, дом 210, корп 1, литер А")
    assert "210" in blds2
    assert "1" in blds2
    assert "а" in blds2
