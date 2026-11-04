from __future__ import annotations

from scripts.dataset_generator.models import SyntheticPairSpec
from scripts.dataset_generator.scenarios.scenario_1_match import get_scenario_1_specs
from scripts.dataset_generator.scenarios.scenario_2_overload import get_scenario_2_specs
from scripts.dataset_generator.scenarios.scenario_3_typos import get_scenario_3_specs
from scripts.dataset_generator.scenarios.scenario_4_warnings import get_scenario_4_specs
from scripts.dataset_generator.scenarios.scenario_5_uncertain import get_scenario_5_specs


def get_all_specs() -> list[SyntheticPairSpec]:
    """Возвращает спецификации всех 15 пар синтетического набора."""
    return [
        *get_scenario_1_specs(),
        *get_scenario_2_specs(),
        *get_scenario_3_specs(),
        *get_scenario_4_specs(),
        *get_scenario_5_specs(),
    ]


__all__ = [
    "get_all_specs",
    "get_scenario_1_specs",
    "get_scenario_2_specs",
    "get_scenario_3_specs",
    "get_scenario_4_specs",
    "get_scenario_5_specs",
]
