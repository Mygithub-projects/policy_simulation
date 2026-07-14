from __future__ import annotations

from typing import Any

import pandas as pd

from schemas import PolicyMode, PolicyType, ScenarioRequest
from tools import WorkforceTools


class SimulationAgent:
    """Calls the ML forecasting and deterministic simulation tools."""

    def __init__(self, tools: WorkforceTools):
        self.tools = tools

    def run(self, scenario: ScenarioRequest) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
        result = self.tools.simulate_policy(scenario)
        summary, subject_summary = self.tools.summarize(result)
        return result, summary, subject_summary

    def compare_active_policies(self, scenario: ScenarioRequest) -> list[dict[str, Any]]:
        if scenario.policy_mode != PolicyMode.COMBINED:
            return []
        comparisons: list[dict[str, Any]] = []
        for policy in scenario.active_policies:
            values = scenario.to_dict()
            values.update(
                {
                    "policy_mode": PolicyMode.SINGLE.value,
                    "policy_type": policy.value,
                    "active_policies": [policy.value],
                }
            )
            single_scenario = ScenarioRequest.from_dict(values)
            single_result = self.tools.simulate_policy(single_scenario)
            single_summary, _ = self.tools.summarize(single_result)
            comparisons.append(
                {
                    "policy": policy.value,
                    "scenario_required_2027": single_summary["scenario_required_2027"],
                    "change_required": single_summary["change_required"],
                    "scenario_teacher_gap": single_summary["scenario_teacher_gap"],
                    "scenario_option_gap": single_summary["scenario_option_gap"],
                }
            )
        return comparisons
