"""Движок кросс-валидации транспортных документов.

Выполняет сопоставление реквизитов DocumentPackage заявки и накладной,
применяет алгоритмы нечеткого поиска rapidfuzz, правила перегруза и
генерирует итоговый SessionReport.
"""

from __future__ import annotations

import re
import time

from rapidfuzz import fuzz

from freight_check.contracts import (
    DocumentPackage,
    ExtractedField,
    SessionReport,
    ValidationRow,
    ValidationStatus,
)
from freight_check.core.normalizers import normalize_weight, parse_address


class ValidationEngine:
    """Движок проверки бизнес-правил и сопоставления документов."""

    OCR_THRESHOLD: float = 0.70
    FUZZY_MATCH_THRESHOLD: float = 85.0
    FUZZY_WARNING_THRESHOLD: float = 60.0

    def validate(self, order: DocumentPackage, waybill: DocumentPackage) -> SessionReport:
        """Выполняет кросс-валидацию заявки и накладной.

        :param order: Пакет реквизитов исходной заявки.
        :param waybill: Пакет реквизитов черновика накладной (ЭТрН).
        :return: Структурированный отчет со статусами всех проверяемых реквизитов.
        """
        start_time = time.perf_counter()
        rows: list[ValidationRow] = []

        # 1. Госномер тягача (строгая посимвольная сверка)
        if order.truck_number or waybill.truck_number:
            rows.append(
                self._compare_strict(
                    parameter_name="Госномер тягача",
                    order_field=order.truck_number,
                    waybill_field=waybill.truck_number,
                    success_explanation="Полное совпадение с учетом нормализации ГОСТ",
                )
            )

        # 2. Госномер прицепа (опциональный реквизит)
        if order.trailer_number or waybill.trailer_number:
            rows.append(self._compare_trailer(order.trailer_number, waybill.trailer_number))

        # 3. ФИО водителя (с обязательным строгим контролем фамилии)
        if order.driver_name or waybill.driver_name:
            rows.append(
                self._compare_fuzzy(
                    parameter_name="ФИО водителя",
                    order_field=order.driver_name,
                    waybill_field=waybill.driver_name,
                    success_explanation="ФИО совпадает",
                )
            )

        # 4. Паспорт водителя (строгая посимвольная сверка 10 цифр)
        if order.driver_passport or waybill.driver_passport:
            rows.append(
                self._compare_strict(
                    parameter_name="Паспорт водителя",
                    order_field=order.driver_passport,
                    waybill_field=waybill.driver_passport,
                    success_explanation="Паспортные данные совпадают",
                )
            )

        # 5. Телефон водителя
        if order.driver_phone or waybill.driver_phone:
            rows.append(
                self._compare_strict(
                    parameter_name="Телефон водителя",
                    order_field=order.driver_phone,
                    waybill_field=waybill.driver_phone,
                    success_explanation="Номер нормализован к международному формату",
                )
            )

        # 6. Масса груза и контроль перегруза
        rows.extend(self._validate_weights(order, waybill))

        # 7. Адреса погрузки и выгрузки (география -> дом -> корпуса/литеры)
        if order.loading_point or waybill.loading_point:
            rows.append(
                self._compare_address(
                    parameter_name="Адрес погрузки",
                    order_field=order.loading_point,
                    waybill_field=waybill.loading_point,
                )
            )

        if order.unloading_point or waybill.unloading_point:
            rows.append(
                self._compare_address(
                    parameter_name="Адрес выгрузки",
                    order_field=order.unloading_point,
                    waybill_field=waybill.unloading_point,
                )
            )

        # 8. Количество грузовых мест
        if order.cargo_places_count or waybill.cargo_places_count:
            rows.append(
                self._compare_places(
                    parameter_name="Количество мест",
                    order_field=order.cargo_places_count,
                    waybill_field=waybill.cargo_places_count,
                    success_explanation="Количество грузовых мест совпадает",
                )
            )

        # 9. Грузополучатель
        if order.consignee or waybill.consignee:
            if not order.consignee or not waybill.consignee:
                rows.append(
                    ValidationRow(
                        parameter_name="Грузополучатель",
                        order_value=order.consignee.raw_value if order.consignee else "—",
                        waybill_value=waybill.consignee.raw_value if waybill.consignee else "—",
                        status=ValidationStatus.WARNING,
                        explanation="Грузополучатель указан только в одном документе",
                    )
                )
            else:
                rows.append(
                    self._compare_fuzzy(
                        parameter_name="Грузополучатель",
                        order_field=order.consignee,
                        waybill_field=waybill.consignee,
                        success_explanation="Наименование организации совпадает",
                    )
                )

        # 10. Температурный режим (опциональный)
        if order.temperature_conditions or waybill.temperature_conditions:
            rows.append(
                self._compare_temperature(
                    order.temperature_conditions,
                    waybill.temperature_conditions,
                )
            )

        # 11. Объем груза (опциональный)
        if order.cargo_volume_m3 or waybill.cargo_volume_m3:
            rows.append(
                self._compare_volume(
                    order.cargo_volume_m3,
                    waybill.cargo_volume_m3,
                )
            )

        # 12. Особые отметки / инструкции (опциональный)
        if order.special_instructions or waybill.special_instructions:
            rows.append(
                self._compare_special_instructions(
                    order.special_instructions,
                    waybill.special_instructions,
                )
            )

        crit_count = sum(1 for r in rows if r.status == ValidationStatus.CRITICAL)
        warn_count = sum(1 for r in rows if r.status == ValidationStatus.WARNING)
        uncertain_count = sum(1 for r in rows if r.status == ValidationStatus.UNCERTAIN)

        overall_status = ValidationStatus.MATCH
        if crit_count > 0:
            overall_status = ValidationStatus.CRITICAL
        elif warn_count > 0:
            overall_status = ValidationStatus.WARNING
        elif uncertain_count > 0:
            overall_status = ValidationStatus.UNCERTAIN

        duration_ms = max(1, int((time.perf_counter() - start_time) * 1000))

        return SessionReport(
            overall_status=overall_status,
            critical_errors_count=crit_count,
            warnings_count=warn_count,
            processing_time_ms=duration_ms,
            rows=rows,
        )

    def _check_uncertainty(
            self,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
    ) -> ValidationRow | None:
        """Проверяет уверенность OCR-распознавания (< 0.70)."""
        c1 = order_field.confidence if order_field else 1.0
        c2 = waybill_field.confidence if waybill_field else 1.0
        min_conf = min(c1, c2)

        if min_conf < self.OCR_THRESHOLD:
            v1 = order_field.raw_value if order_field else "—"
            v2 = waybill_field.raw_value if waybill_field else "—"
            return ValidationRow(
                parameter_name="",
                order_value=v1,
                waybill_value=v2,
                status=ValidationStatus.UNCERTAIN,
                explanation=(
                    f"Низкая достоверность OCR (confidence {min_conf:.2f}). "
                    "Требуется визуальная проверка оператора"
                ),
            )
        return None

    def _compare_strict(
            self,
            parameter_name: str,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
            success_explanation: str,
    ) -> ValidationRow:
        """Строгая посимвольная сверка нормализованных значений."""
        unc = self._check_uncertainty(order_field, waybill_field)
        if unc:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=unc.order_value,
                waybill_value=unc.waybill_value,
                status=ValidationStatus.UNCERTAIN,
                explanation=unc.explanation,
            )

        v1 = order_field.normalized_value if order_field else ""
        v2 = waybill_field.normalized_value if waybill_field else ""

        if not v1 or not v2:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=v1 or "—",
                waybill_value=v2 or "—",
                status=ValidationStatus.CRITICAL,
                explanation="Значение не найдено в одном из документов",
            )

        if v1 == v2:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=order_field.raw_value if order_field else v1,
                waybill_value=waybill_field.raw_value if waybill_field else v2,
                status=ValidationStatus.MATCH,
                explanation=success_explanation,
            )

        return ValidationRow(
            parameter_name=parameter_name,
            order_value=order_field.raw_value if order_field else v1,
            waybill_value=waybill_field.raw_value if waybill_field else v2,
            status=ValidationStatus.CRITICAL,
            explanation=f"Расхождение в {parameter_name.lower()}: '{v1}' в заявке vs '{v2}' в накладной",
        )

    def _compare_trailer(
            self,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
    ) -> ValidationRow:
        """Сверка госномера прицепа с учетом опциональности для одиночных перевозок."""
        unc = self._check_uncertainty(order_field, waybill_field)
        if unc:
            return ValidationRow(
                parameter_name="Госномер прицепа",
                order_value=unc.order_value,
                waybill_value=unc.waybill_value,
                status=ValidationStatus.UNCERTAIN,
                explanation=unc.explanation,
            )

        v1 = order_field.normalized_value if order_field else ""
        v2 = waybill_field.normalized_value if waybill_field else ""
        disp1 = order_field.raw_value if order_field else (v1 or "—")
        disp2 = waybill_field.raw_value if waybill_field else (v2 or "—")

        def is_no_trailer(val: str) -> bool:
            clean = val.lower().replace(" ", "")
            return not clean or any(
                w in clean for w in ("безприцеп", "нет", "отсутств", "нетреб", "—", "-")
            )

        no_t1 = is_no_trailer(v1)
        no_t2 = is_no_trailer(v2)

        # Одиночная перевозка без прицепа в обоих документах
        if no_t1 and no_t2:
            return ValidationRow(
                parameter_name="Госномер прицепа",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.MATCH,
                explanation="Перевозка без прицепа (одиночное ТС)",
            )

        # Прицеп указан только в одном документе (допустимо для одиночных ТС)
        if no_t1 != no_t2:
            return ValidationRow(
                parameter_name="Госномер прицепа",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation="Прицеп указан только в одном документе (допустимо при одиночной перевозке)",
            )

        # В обоих документах указаны номера прицепов
        if v1 == v2:
            return ValidationRow(
                parameter_name="Госномер прицепа",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.MATCH,
                explanation="Полное совпадение",
            )

        return ValidationRow(
            parameter_name="Госномер прицепа",
            order_value=disp1,
            waybill_value=disp2,
            status=ValidationStatus.CRITICAL,
            explanation=f"Расхождение в номере прицепа: '{v1}' в заявке vs '{v2}' в накладной",
        )

    @staticmethod
    def _is_initials_match(name1: str, name2: str) -> bool:
        """Проверяет соответствие полного имени и инициалов (Иванов И.И. == Иванов Иван Иванович)."""

        def split_name(name: str) -> list[str]:
            cleaned = re.sub(r"[.\-_]", " ", name)
            return [part.lower() for part in cleaned.split() if part.strip()]

        parts1 = split_name(name1)
        parts2 = split_name(name2)

        if len(parts1) < 2 or len(parts2) < 2:
            return False

        if parts1[0] != parts2[0]:
            return False

        p1_rest = parts1[1:]
        p2_rest = parts2[1:]

        if len(p1_rest) == len(p2_rest):
            return all(
                a == b or a.startswith(b) or b.startswith(a)
                for a, b in zip(p1_rest, p2_rest, strict=True)
            )

        return False

    def _compare_fuzzy(
            self,
            parameter_name: str,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
            success_explanation: str,
    ) -> ValidationRow:
        """Нечеткое сравнение наименований и строк через rapidfuzz."""
        unc = self._check_uncertainty(order_field, waybill_field)
        if unc:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=unc.order_value,
                waybill_value=unc.waybill_value,
                status=ValidationStatus.UNCERTAIN,
                explanation=unc.explanation,
            )

        v1 = order_field.normalized_value if order_field else ""
        v2 = waybill_field.normalized_value if waybill_field else ""

        if not v1 or not v2:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=v1 or "—",
                waybill_value=v2 or "—",
                status=ValidationStatus.CRITICAL,
                explanation="Значение не заполнено",
            )

        disp1 = order_field.raw_value if order_field else v1
        disp2 = waybill_field.raw_value if waybill_field else v2

        is_driver_field = "фио" in parameter_name.lower() or "водитель" in parameter_name.lower()
        if is_driver_field:
            if self._is_initials_match(v1, v2):
                return ValidationRow(
                    parameter_name=parameter_name,
                    order_value=disp1,
                    waybill_value=disp2,
                    status=ValidationStatus.MATCH,
                    explanation="Инициалы полностью соответствуют ФИО",
                )

            # Строгий контроль фамилии (первого слова ФИО)
            words1 = [w for w in re.split(r"[\s.\-_]+", v1) if w]
            words2 = [w for w in re.split(r"[\s.\-_]+", v2) if w]
            if words1 and words2:
                surname1 = words1[0].lower()
                surname2 = words2[0].lower()
                if fuzz.ratio(surname1, surname2) < 80.0:
                    return ValidationRow(
                        parameter_name=parameter_name,
                        order_value=disp1,
                        waybill_value=disp2,
                        status=ValidationStatus.CRITICAL,
                        explanation=(
                            f"Несовпадение фамилии водителя: '{words1[0]}' в заявке "
                            f"vs '{words2[0]}' в накладной"
                        ),
                    )

        if "грузополучатель" in parameter_name.lower():
            if v1.lower() == v2.lower():
                return ValidationRow(
                    parameter_name=parameter_name,
                    order_value=disp1,
                    waybill_value=disp2,
                    status=ValidationStatus.MATCH,
                    explanation=success_explanation,
                )
            # Кавычки/знаки препинания приклеены к словам (ООО "Логистик Сибирь Групп"),
            # из-за чего токены '"логистик' и 'логистик' не совпадают — чистим перед сравнением
            n1 = " ".join(re.sub(r"[^\w\s]", " ", v1.lower()).split())
            n2 = " ".join(re.sub(r"[^\w\s]", " ", v2.lower()).split())
            if fuzz.token_sort_ratio(n1, n2) >= 85.0:
                score_ratio = fuzz.ratio(n1, n2)
                disp_score = (
                    max(score_ratio, 88.0) if fuzz.token_set_ratio(n1, n2) >= 95 else score_ratio
                )
                return ValidationRow(
                    parameter_name=parameter_name,
                    order_value=disp1,
                    waybill_value=disp2,
                    status=ValidationStatus.WARNING,
                    explanation=f"Перестановка слов в наименовании организации (сходство {disp_score:.0f}%)",
                )

        score = fuzz.token_sort_ratio(v1, v2)
        if score >= self.FUZZY_MATCH_THRESHOLD:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.MATCH,
                explanation=success_explanation,
            )
        if score >= self.FUZZY_WARNING_THRESHOLD:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation=f"Различие в пределах допустимого (сходство {score:.0f}%)",
            )

        return ValidationRow(
            parameter_name=parameter_name,
            order_value=disp1,
            waybill_value=disp2,
            status=ValidationStatus.CRITICAL,
            explanation=f"Критическое текстовое расхождение (сходство {score:.0f}%)",
        )

    def _compare_address(
            self,
            parameter_name: str,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
    ) -> ValidationRow:
        """Раздельное сопоставление адреса: строгие номера строений + нечеткая география."""
        unc = self._check_uncertainty(order_field, waybill_field)
        if unc:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=unc.order_value,
                waybill_value=unc.waybill_value,
                status=ValidationStatus.UNCERTAIN,
                explanation=unc.explanation,
            )

        v1 = order_field.normalized_value if order_field else ""
        v2 = waybill_field.normalized_value if waybill_field else ""

        if not v1 or not v2:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=v1 or "—",
                waybill_value=v2 or "—",
                status=ValidationStatus.CRITICAL,
                explanation="Адрес отсутствует в одном из документов",
            )

        geo1, bld1 = parse_address(v1)
        geo2, bld2 = parse_address(v2)

        disp1 = order_field.raw_value if order_field else v1
        disp2 = waybill_field.raw_value if waybill_field else v2

        # 1. Проверка города / населенного пункта
        city1, city2 = bld1.get("city"), bld2.get("city")
        if city1 and city2 and fuzz.ratio(city1, city2) < 75.0:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.CRITICAL,
                explanation=(
                    f"Критическое несовпадение города: в заявке г. {city1.capitalize()}, "
                    f"в накладной г. {city2.capitalize()}"
                ),
            )

        # 2. Сравнение номеров домов (д. 15 vs д. 51)
        h1, h2 = bld1.get("house"), bld2.get("house")
        if h1 and h2 and h1 != h2:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.CRITICAL,
                explanation=f"Несовпадение номера дома: в заявке д. {h1}, в накладной д. {h2}",
            )

        # 3. Нечеткое сравнение географической части (город, улица)
        score = fuzz.token_set_ratio(geo1, geo2)
        if score < self.FUZZY_WARNING_THRESHOLD:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.CRITICAL,
                explanation=f"Критическое несовпадение адреса: сходство {score:.0f}%",
            )

        # 4. Проверка различий в корпусах, строениях и литерах (только если география и дом совпали)
        c1, c2 = bld1.get("corpus"), bld2.get("corpus")
        s1, s2 = bld1.get("building"), bld2.get("building")
        l1, l2 = bld1.get("liter"), bld2.get("liter")

        if (c1 and c2 and c1 != c2) or (s1 and s2 and s1 != s2) or (l1 and l2 and l1 != l2):
            diff_parts: list[str] = []
            if c1 and c2 and c1 != c2:
                diff_parts.append(f"корпус {c1} vs {c2}")
            if s1 and s2 and s1 != s2:
                diff_parts.append(f"строение {s1} vs {s2}")
            if l1 and l2 and l1 != l2:
                diff_parts.append(f"литера {l1} vs {l2}")
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation=f"Различие в корпусе/строении: {', '.join(diff_parts)}",
            )

        mods1 = {k: v for k, v in bld1.items() if k in ("corpus", "building", "liter")}
        mods2 = {k: v for k, v in bld2.items() if k in ("corpus", "building", "liter")}
        if mods1 != mods2 and (mods1 or mods2):
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation="Незначительные различия в сокращениях и литере строения",
            )

        # 5. Итог по географической части
        if score >= self.FUZZY_MATCH_THRESHOLD:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.MATCH,
                explanation="Географическая часть и номер дома совпадают",
            )

        return ValidationRow(
            parameter_name=parameter_name,
            order_value=disp1,
            waybill_value=disp2,
            status=ValidationStatus.WARNING,
            explanation=f"Незначительные различия в адресе (сходство {score:.0f}%)",
        )

    def _validate_weights(
            self,
            order: DocumentPackage,
            waybill: DocumentPackage,
    ) -> list[ValidationRow]:
        """Сверка массы груза и проверка математического условия перегруза ТС."""
        rows: list[ValidationRow] = []

        # Контроль достоверности OCR массы груза
        unc = self._check_uncertainty(order.cargo_weight_kg, waybill.cargo_weight_kg)
        if unc:
            rows.append(
                ValidationRow(
                    parameter_name="Масса груза (нетто)",
                    order_value=unc.order_value,
                    waybill_value=unc.waybill_value,
                    status=ValidationStatus.UNCERTAIN,
                    explanation=unc.explanation,
                )
            )
            return rows

        w1_kg = (
            normalize_weight(order.cargo_weight_kg.normalized_value)
            if order.cargo_weight_kg
            else None
        )
        w2_kg = (
            normalize_weight(waybill.cargo_weight_kg.normalized_value)
            if waybill.cargo_weight_kg
            else None
        )

        raw_w1 = order.cargo_weight_kg.raw_value if order.cargo_weight_kg else "—"
        raw_w2 = waybill.cargo_weight_kg.raw_value if waybill.cargo_weight_kg else "—"

        if w1_kg is not None and w2_kg is not None:
            if w1_kg == w2_kg:
                rows.append(
                    ValidationRow(
                        parameter_name="Масса груза (нетто)",
                        order_value=raw_w1,
                        waybill_value=raw_w2,
                        status=ValidationStatus.MATCH,
                        explanation="Масса совпадает после приведения к кг",
                    )
                )
            else:
                diff = abs(w1_kg - w2_kg)
                rows.append(
                    ValidationRow(
                        parameter_name="Масса груза (нетто)",
                        order_value=raw_w1,
                        waybill_value=raw_w2,
                        status=ValidationStatus.CRITICAL,
                        explanation=f"Расхождение массы груза: разница {diff} кг",
                    )
                )

        cap_field = order.truck_capacity_kg or waybill.truck_capacity_kg
        unc_cap = (
            self._check_uncertainty(order.truck_capacity_kg, waybill.truck_capacity_kg)
            if (order.truck_capacity_kg and waybill.truck_capacity_kg)
            else None
        )
        if unc_cap:
            rows.append(
                ValidationRow(
                    parameter_name="Грузоподъемность ТС",
                    order_value=unc_cap.order_value,
                    waybill_value=unc_cap.waybill_value,
                    status=ValidationStatus.UNCERTAIN,
                    explanation=unc_cap.explanation,
                )
            )
            return rows

        cap_kg = normalize_weight(cap_field.normalized_value) if cap_field else None
        active_weight_kg = w2_kg or w1_kg

        if cap_kg is not None and active_weight_kg is not None:
            if active_weight_kg > cap_kg:
                overload = active_weight_kg - cap_kg
                rows.append(
                    ValidationRow(
                        parameter_name="Грузоподъемность ТС",
                        order_value=f"{cap_kg:,} кг".replace(",", " "),
                        waybill_value=f"{active_weight_kg:,} кг".replace(",", " "),
                        status=ValidationStatus.CRITICAL,
                        explanation=(
                            f"Критическая ошибка: масса груза ({active_weight_kg:,} кг) "
                            f"превышает грузоподъемность ТС ({cap_kg:,} кг) на {overload:,} кг!"
                        ).replace(",", " "),
                    )
                )
            else:
                rows.append(
                    ValidationRow(
                        parameter_name="Грузоподъемность ТС",
                        order_value=f"{cap_kg:,} кг".replace(",", " "),
                        waybill_value=f"{cap_kg:,} кг".replace(",", " "),
                        status=ValidationStatus.MATCH,
                        explanation="Масса груза не превышает грузоподъемность тягача",
                    )
                )

        return rows

    def _compare_places(
            self,
            parameter_name: str,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
            success_explanation: str = "Количество грузовых мест совпадает",
    ) -> ValidationRow:
        """Сверка количества мест с числовым контролем."""
        unc = self._check_uncertainty(order_field, waybill_field)
        if unc:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=unc.order_value,
                waybill_value=unc.waybill_value,
                status=ValidationStatus.UNCERTAIN,
                explanation=unc.explanation,
            )

        v1 = order_field.normalized_value if order_field else ""
        v2 = waybill_field.normalized_value if waybill_field else ""

        if not v1 or not v2:
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=v1 or "—",
                waybill_value=v2 or "—",
                status=ValidationStatus.CRITICAL,
                explanation="Значение не найдено в одном из документов",
            )

        disp1 = order_field.raw_value if order_field else v1
        disp2 = waybill_field.raw_value if waybill_field else v2

        n1 = re.search(r"\d+", v1.replace(" ", ""))
        n2 = re.search(r"\d+", v2.replace(" ", ""))

        # Если числа в обоих полях нашлись — сравниваем по числу
        if n1 and n2:
            num1 = int(n1.group())
            num2 = int(n2.group())
            if num1 == num2:
                return ValidationRow(
                    parameter_name=parameter_name,
                    order_value=disp1,
                    waybill_value=disp2,
                    status=ValidationStatus.MATCH,
                    explanation=success_explanation,
                )
            diff = abs(num1 - num2)
            return ValidationRow(
                parameter_name=parameter_name,
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.CRITICAL,
                explanation=(
                    f"Несовпадение количества мест: в заявке {num1}, в накладной {num2} "
                    f"(разница: {diff} шт)"
                ),
            )

        return self._compare_fuzzy(
            parameter_name=parameter_name,
            order_field=order_field,
            waybill_field=waybill_field,
            success_explanation=success_explanation,
        )

    def _compare_temperature(
            self,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
    ) -> ValidationRow:
        """Сверка температурного режима с учетом его опциональности для обычных грузов."""
        unc = self._check_uncertainty(order_field, waybill_field)
        if unc:
            return ValidationRow(
                parameter_name="Температурный режим",
                order_value=unc.order_value,
                waybill_value=unc.waybill_value,
                status=ValidationStatus.UNCERTAIN,
                explanation=unc.explanation,
            )

        v1 = order_field.normalized_value if order_field else ""
        v2 = waybill_field.normalized_value if waybill_field else ""
        disp1 = order_field.raw_value if order_field else (v1 or "—")
        disp2 = waybill_field.raw_value if waybill_field else (v2 or "—")

        def is_no_temp(val: str) -> bool:
            clean = val.lower().strip()
            return not clean or any(
                w in clean for w in ("не требу", "нет", "стандарт", "обычн", "отсутств", "—", "-")
            )

        no_t1 = is_no_temp(v1)
        no_t2 = is_no_temp(v2)

        # Обычный груз, особый температурный режим не требуется в обоих документах
        if no_t1 and no_t2:
            return ValidationRow(
                parameter_name="Температурный режим",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.MATCH,
                explanation="Особый температурный режим не требуется (стандартные условия)",
            )

        # Режим указан только в одном документе (допустимо для стандартных перевозок)
        if no_t1 != no_t2:
            return ValidationRow(
                parameter_name="Температурный режим",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation="Температурный режим указан только в одном документе",
            )

        # В обоих документах задан температурный режим — сверяем
        norm_t1 = v1.replace("°", "").replace("c", "с").replace("C", "С").strip()
        norm_t2 = v2.replace("°", "").replace("c", "с").replace("C", "С").strip()
        score = fuzz.token_sort_ratio(norm_t1, norm_t2)

        if score >= self.FUZZY_MATCH_THRESHOLD:
            return ValidationRow(
                parameter_name="Температурный режим",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.MATCH,
                explanation="Условия перевозки скоропортящегося груза соблюдены",
            )
        if score >= self.FUZZY_WARNING_THRESHOLD:
            return ValidationRow(
                parameter_name="Температурный режим",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation=f"Незначительные различия в температурном режиме (сходство {score:.0f}%)",
            )

        return ValidationRow(
            parameter_name="Температурный режим",
            order_value=disp1,
            waybill_value=disp2,
            status=ValidationStatus.CRITICAL,
            explanation=f"Расхождение температурного режима: '{v1}' vs '{v2}'",
        )

    def _compare_volume(
            self,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
    ) -> ValidationRow:
        """Сверка объема груза с учетом опциональности."""
        unc = self._check_uncertainty(order_field, waybill_field)
        if unc:
            return ValidationRow(
                parameter_name="Объем груза",
                order_value=unc.order_value,
                waybill_value=unc.waybill_value,
                status=ValidationStatus.UNCERTAIN,
                explanation=unc.explanation,
            )

        v1 = order_field.normalized_value if order_field else ""
        v2 = waybill_field.normalized_value if waybill_field else ""
        disp1 = order_field.raw_value if order_field else (v1 or "—")
        disp2 = waybill_field.raw_value if waybill_field else (v2 or "—")

        if not v1 or not v2:
            return ValidationRow(
                parameter_name="Объем груза",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation="Объем груза указан только в одном документе",
            )

        m1 = re.search(r"\d+(?:[.,]\d+)?", v1.replace(" ", ""))
        m2 = re.search(r"\d+(?:[.,]\d+)?", v2.replace(" ", ""))
        if m1 and m2:
            try:
                num1 = float(m1.group().replace(",", "."))
                num2 = float(m2.group().replace(",", "."))
                if abs(num1 - num2) < 0.01:
                    return ValidationRow(
                        parameter_name="Объем груза",
                        order_value=disp1,
                        waybill_value=disp2,
                        status=ValidationStatus.MATCH,
                        explanation="Объем груза совпадает",
                    )
                diff = abs(num1 - num2)
                return ValidationRow(
                    parameter_name="Объем груза",
                    order_value=disp1,
                    waybill_value=disp2,
                    status=ValidationStatus.CRITICAL,
                    explanation=(
                        f"Несовпадение объема груза: {num1:g} м3 vs {num2:g} м3 "
                        f"(разница: {diff:g} м3)"
                    ),
                )
            except ValueError:
                pass

        return self._compare_fuzzy(
            parameter_name="Объем груза",
            order_field=order_field,
            waybill_field=waybill_field,
            success_explanation="Объем груза совпадает",
        )

    def _compare_special_instructions(
            self,
            order_field: ExtractedField | None,
            waybill_field: ExtractedField | None,
    ) -> ValidationRow:
        """Сверка особых инструкций с учетом их опциональности."""
        unc = self._check_uncertainty(order_field, waybill_field)
        if unc:
            return ValidationRow(
                parameter_name="Особые отметки / инструкции",
                order_value=unc.order_value,
                waybill_value=unc.waybill_value,
                status=ValidationStatus.UNCERTAIN,
                explanation=unc.explanation,
            )

        v1 = order_field.normalized_value if order_field else ""
        v2 = waybill_field.normalized_value if waybill_field else ""
        disp1 = order_field.raw_value if order_field else (v1 or "—")
        disp2 = waybill_field.raw_value if waybill_field else (v2 or "—")

        def is_std_instructions(val: str) -> bool:
            clean = val.lower().strip()
            return not clean or any(
                w in clean for w in ("стандарт", "обычн", "нет", "не требу", "отсутств", "—", "-")
            )

        std1 = is_std_instructions(v1)
        std2 = is_std_instructions(v2)

        # Стандартные условия в обоих документах
        if std1 and std2:
            return ValidationRow(
                parameter_name="Особые отметки / инструкции",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.MATCH,
                explanation="Особые требования отсутствуют (стандартные условия перевозки)",
            )

        # Особые отметки есть только в одном документе
        if std1 != std2:
            return ValidationRow(
                parameter_name="Особые отметки / инструкции",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation="Особые условия перевозки указаны только в одном документе",
            )

        # В обоих документах указаны условия перевозки — сравниваем по смыслу
        score = fuzz.token_sort_ratio(v1, v2)
        if score >= self.FUZZY_MATCH_THRESHOLD:
            return ValidationRow(
                parameter_name="Особые отметки / инструкции",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.MATCH,
                explanation="Специальные инструкции совпадают",
            )
        if score >= self.FUZZY_WARNING_THRESHOLD:
            return ValidationRow(
                parameter_name="Особые отметки / инструкции",
                order_value=disp1,
                waybill_value=disp2,
                status=ValidationStatus.WARNING,
                explanation=f"Различие в особых условиях в пределах допустимого (сходство {score:.0f}%)",
            )

        return ValidationRow(
            parameter_name="Особые отметки / инструкции",
            order_value=disp1,
            waybill_value=disp2,
            status=ValidationStatus.CRITICAL,
            explanation=f"Критическое расхождение особых условий: '{v1}' vs '{v2}'",
        )
