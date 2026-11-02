"""Модуль генерации моковых данных для демонстрации и тестирования GUI.

Содержит 5 эталонных сценариев сопоставления документов в соответствии с AGENTS.md:
1. Корректный рейс (все совпадает)
2. Критический перегруз автомобиля
3. Опечатки в критических идентификаторах (госномера, паспорта, дом)
4. Допустимые расхождения (сокращения, перестановка слов)
5. Сомнительное считывание скан-образа (низкая уверенность OCR)
"""

from freight_check.contracts import SessionReport, ValidationRow, ValidationStatus


def get_mock_scenario_1_match() -> SessionReport:
    """Сценарий 1: Корректный рейс (все реквизиты совпадают)."""
    rows: list[ValidationRow] = [
        ValidationRow(
            parameter_name="Госномер тягача",
            order_value="А 123 ВС 77",
            waybill_value="А123ВС77",
            status=ValidationStatus.MATCH,
            explanation="Полное совпадение с учетом нормализации ГОСТ",
        ),
        ValidationRow(
            parameter_name="Госномер прицепа",
            order_value="ВЕ 4567 77",
            waybill_value="ВЕ456777",
            status=ValidationStatus.MATCH,
            explanation="Полное совпадение",
        ),
        ValidationRow(
            parameter_name="Грузоподъемность ТС",
            order_value="20 000 кг",
            waybill_value="20 000 кг",
            status=ValidationStatus.MATCH,
            explanation="Совпадает с паспортными данными",
        ),
        ValidationRow(
            parameter_name="ФИО водителя",
            order_value="Иванов Иван Иванович",
            waybill_value="Иванов И. И.",
            status=ValidationStatus.MATCH,
            explanation="Инициалы полностью соответствуют ФИО",
        ),
        ValidationRow(
            parameter_name="Паспорт водителя",
            order_value="4510 123456",
            waybill_value="45 10 123456",
            status=ValidationStatus.MATCH,
            explanation="Серия и номер совпадают",
        ),
        ValidationRow(
            parameter_name="Телефон водителя",
            order_value="+7 (999) 111-22-33",
            waybill_value="+79991112233",
            status=ValidationStatus.MATCH,
            explanation="Номер нормализован к международному формату",
        ),
        ValidationRow(
            parameter_name="Масса груза (нетто)",
            order_value="18.5 т",
            waybill_value="18 500 кг",
            status=ValidationStatus.MATCH,
            explanation="Масса груза не превышает грузоподъемность тягача",
        ),
        ValidationRow(
            parameter_name="Количество мест",
            order_value="32 паллеты",
            waybill_value="32 палл.",
            status=ValidationStatus.MATCH,
            explanation="Количество грузовых мест совпадает",
        ),
        ValidationRow(
            parameter_name="Адрес погрузки",
            order_value="г. Москва, ул. Ленина, д. 15, стр. 2",
            waybill_value="г. Москва, ул. Ленина, д. 15, стр. 2",
            status=ValidationStatus.MATCH,
            explanation="Географическая часть и номер строения совпадают",
        ),
        ValidationRow(
            parameter_name="Адрес выгрузки",
            order_value="г. Санкт-Петербург, Московский пр-кт, д. 100",
            waybill_value="Санкт-Петербург, Московский пр-т, д. 100",
            status=ValidationStatus.MATCH,
            explanation="Географическая часть и номер дома совпадают",
        ),
        ValidationRow(
            parameter_name="Температурный режим",
            order_value="+2...+4 °C",
            waybill_value="+2...+4 C",
            status=ValidationStatus.MATCH,
            explanation="Условия перевозки скоропортящегося груза соблюдены",
        ),
    ]

    return SessionReport(
        overall_status=ValidationStatus.MATCH,
        critical_errors_count=0,
        warnings_count=0,
        processing_time_ms=124,
        rows=rows,
    )


def get_mock_scenario_2_overload() -> SessionReport:
    """Сценарий 2: Критический перегруз (масса превышает грузоподъемность)."""
    rows: list[ValidationRow] = [
        ValidationRow(
            parameter_name="Госномер тягача",
            order_value="О 777 ОО 777",
            waybill_value="О777ОО777",
            status=ValidationStatus.MATCH,
            explanation="Полное совпадение",
        ),
        ValidationRow(
            parameter_name="Грузоподъемность ТС",
            order_value="20 000 кг",
            waybill_value="20 000 кг",
            status=ValidationStatus.MATCH,
            explanation="Паспортная г/п автомобиля",
        ),
        ValidationRow(
            parameter_name="Масса груза (нетто)",
            order_value="22.5 т",
            waybill_value="22 500 кг",
            status=ValidationStatus.CRITICAL,
            explanation="Критическая ошибка: масса груза (22 500 кг) превышает грузоподъемность ТС (20 000 кг) на 2 500 кг!",
        ),
        ValidationRow(
            parameter_name="ФИО водителя",
            order_value="Петров Петр Петрович",
            waybill_value="Петров П. П.",
            status=ValidationStatus.MATCH,
            explanation="ФИО совпадает",
        ),
        ValidationRow(
            parameter_name="Паспорт водителя",
            order_value="4608 654321",
            waybill_value="4608 654321",
            status=ValidationStatus.MATCH,
            explanation="Паспортные данные совпадают",
        ),
        ValidationRow(
            parameter_name="Адрес погрузки",
            order_value="г. Казань, ул. Восстания, д. 45",
            waybill_value="Казань, ул. Восстания, д. 45",
            status=ValidationStatus.MATCH,
            explanation="Адрес совпадает",
        ),
        ValidationRow(
            parameter_name="Адрес выгрузки",
            order_value="г. Самара, Заводское ш., д. 12",
            waybill_value="Самара, Заводское шоссе, д. 12",
            status=ValidationStatus.MATCH,
            explanation="Адрес совпадает",
        ),
    ]

    return SessionReport(
        overall_status=ValidationStatus.CRITICAL,
        critical_errors_count=1,
        warnings_count=0,
        processing_time_ms=98,
        rows=rows,
    )


def get_mock_scenario_3_typos() -> SessionReport:
    """Сценарий 3: Опечатки в критических идентификаторах."""
    rows: list[ValidationRow] = [
        ValidationRow(
            parameter_name="Госномер тягача",
            order_value="А 123 ВС 77",
            waybill_value="А 128 ВС 77",
            status=ValidationStatus.CRITICAL,
            explanation="Расхождение в номере ТС: '123' в заявке vs '128' в накладной (критично для ГИС ЭПД)",
        ),
        ValidationRow(
            parameter_name="Госномер прицепа",
            order_value="АК 8899 77",
            waybill_value="АК 8899 77",
            status=ValidationStatus.MATCH,
            explanation="Номер прицепа совпадает",
        ),
        ValidationRow(
            parameter_name="Паспорт водителя",
            order_value="4510 123456",
            waybill_value="4510 123457",
            status=ValidationStatus.CRITICAL,
            explanation="Расхождение в номере паспорта: последняя цифра '6' vs '7'",
        ),
        ValidationRow(
            parameter_name="ФИО водителя",
            order_value="Сидоров Алексей Михайлович",
            waybill_value="Сидоров Алексей Михайлович",
            status=ValidationStatus.MATCH,
            explanation="ФИО совпадает",
        ),
        ValidationRow(
            parameter_name="Масса груза",
            order_value="15 000 кг",
            waybill_value="15 000 кг",
            status=ValidationStatus.MATCH,
            explanation="Масса груза совпадает",
        ),
        ValidationRow(
            parameter_name="Адрес погрузки",
            order_value="г. Нижний Новгород, ул. Родионова, д. 15",
            waybill_value="г. Нижний Новгород, ул. Родионова, д. 51",
            status=ValidationStatus.CRITICAL,
            explanation="Несовпадение номера дома: в заявке д. 15, в накладной д. 51",
        ),
        ValidationRow(
            parameter_name="Адрес выгрузки",
            order_value="г. Владимир, ул. Мира, д. 8",
            waybill_value="г. Владимир, ул. Мира, д. 8",
            status=ValidationStatus.MATCH,
            explanation="Адрес выгрузки совпадает",
        ),
    ]

    return SessionReport(
        overall_status=ValidationStatus.CRITICAL,
        critical_errors_count=3,
        warnings_count=0,
        processing_time_ms=142,
        rows=rows,
    )


def get_mock_scenario_4_warnings() -> SessionReport:
    """Сценарий 4: Допустимые расхождения (сокращения, перестановка слов)."""
    rows: list[ValidationRow] = [
        ValidationRow(
            parameter_name="Госномер тягача",
            order_value="Е 555 КХ 799",
            waybill_value="Е555КХ799",
            status=ValidationStatus.MATCH,
            explanation="Полное совпадение",
        ),
        ValidationRow(
            parameter_name="ФИО водителя",
            order_value="Козлов Дмитрий Сергеевич",
            waybill_value="Козлов Д. С.",
            status=ValidationStatus.MATCH,
            explanation="ФИО совпадает",
        ),
        ValidationRow(
            parameter_name="Грузополучатель",
            order_value='ООО "Логистик Сибирь Групп"',
            waybill_value='ООО "Сибирь Логистик Групп"',
            status=ValidationStatus.WARNING,
            explanation="Перестановка слов в наименовании организации (сходство 88%)",
        ),
        ValidationRow(
            parameter_name="Адрес погрузки",
            order_value="г. Екатеринбург, ул. 8 Марта, д. 210, литер А",
            waybill_value="Екатеринбург, 8 Марта ул., дом 210",
            status=ValidationStatus.WARNING,
            explanation="Незначительные различия в сокращениях и литере строения",
        ),
        ValidationRow(
            parameter_name="Адрес выгрузки",
            order_value="г. Тюмень, ул. Республики, д. 50",
            waybill_value="г. Тюмень, ул. Республики, д. 50",
            status=ValidationStatus.MATCH,
            explanation="Адрес совпадает",
        ),
        ValidationRow(
            parameter_name="Масса груза",
            order_value="12 400 кг",
            waybill_value="12.4 т",
            status=ValidationStatus.MATCH,
            explanation="Масса совпадает после приведения к кг",
        ),
    ]

    return SessionReport(
        overall_status=ValidationStatus.WARNING,
        critical_errors_count=0,
        warnings_count=2,
        processing_time_ms=115,
        rows=rows,
    )


def get_mock_scenario_5_uncertain() -> SessionReport:
    """Сценарий 5: Сомнительное считывание скан-образа (уверенность OCR < 0.70)."""
    rows: list[ValidationRow] = [
        ValidationRow(
            parameter_name="Госномер тягача",
            order_value="М 345 ТР 777",
            waybill_value="М345ТР777",
            status=ValidationStatus.MATCH,
            explanation="Распознано успешно (confidence 0.94)",
        ),
        ValidationRow(
            parameter_name="Госномер прицепа",
            order_value="РВ 1234 77",
            waybill_value="РВ12347?",
            status=ValidationStatus.UNCERTAIN,
            explanation="Низкая достоверность OCR (confidence 0.61). Требуется визуальная проверка оператора",
        ),
        ValidationRow(
            parameter_name="Телефон водителя",
            order_value="+7 (916) 123-45-67",
            waybill_value="+7916123458?",
            status=ValidationStatus.UNCERTAIN,
            explanation="Зашумленный скан в поле телефона (confidence 0.58). Требуется ручной контроль",
        ),
        ValidationRow(
            parameter_name="ФИО водителя",
            order_value="Воронов Сергей Павлович",
            waybill_value="Воронов Сергей Павлович",
            status=ValidationStatus.MATCH,
            explanation="Распознано успешно (confidence 0.91)",
        ),
        ValidationRow(
            parameter_name="Масса груза",
            order_value="19 000 кг",
            waybill_value="19 000 кг",
            status=ValidationStatus.MATCH,
            explanation="Масса совпадает",
        ),
        ValidationRow(
            parameter_name="Адрес погрузки",
            order_value="г. Уфа, Индустриальное ш., д. 7",
            waybill_value="г. Уфа, Индустриальное ш., д. 7",
            status=ValidationStatus.MATCH,
            explanation="Адрес совпадает",
        ),
    ]

    return SessionReport(
        overall_status=ValidationStatus.UNCERTAIN,
        critical_errors_count=0,
        warnings_count=0,
        processing_time_ms=185,
        rows=rows,
    )


def get_all_scenarios() -> dict[str, SessionReport]:
    """Возвращает словарь всех доступных моковых сценариев."""
    return {
        "Сценарий 1: Корректный рейс (все совпадает)": get_mock_scenario_1_match(),
        "Сценарий 2: Критический перегруз ТС": get_mock_scenario_2_overload(),
        "Сценарий 3: Опечатки в реквизитах (номера, паспорт, дом)": get_mock_scenario_3_typos(),
        "Сценарий 4: Допустимые расхождения (сокращения)": get_mock_scenario_4_warnings(),
        "Сценарий 5: Сомнительное считывание скана (OCR)": get_mock_scenario_5_uncertain(),
    }
