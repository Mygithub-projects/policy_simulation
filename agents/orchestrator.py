from __future__ import annotations

from typing import Any

from schemas import ScenarioRequest
from tools import WorkforceTools

from .explanation_agent import ExplanationAgent
from .recommendation_agent import RecommendationAgent
from .scenario_agent import ScenarioAgent
from .simulation_agent import SimulationAgent


class Orchestrator:
    """Controls the complete agent workflow."""

    def __init__(self, tools: WorkforceTools):
        states = tools.get_filter_options("negeri")
        self.scenario_agent = ScenarioAgent(states)
        self.simulation_agent = SimulationAgent(tools)
        self.recommendation_agent = RecommendationAgent()
        self.explanation_agent = ExplanationAgent()
        self.tools = tools

    def execute(self, scenario: ScenarioRequest, lang: str = "en", run_by: str | None = None) -> dict[str, Any]:
        scenario.validate()
        detail, summary, subject_summary = self.simulation_agent.run(scenario)
        policy_impacts = self.simulation_agent.compare_active_policies(scenario)
        recommendations, rules = self.recommendation_agent.run(detail, lang)
        explanation, explanation_source = self.explanation_agent.run(
            scenario, summary, subject_summary, lang
        )
        artifacts = self.tools.save_run(scenario, detail, summary, subject_summary, run_by=run_by)
        return {
            "scenario": scenario,
            "scenario_source": "Direct user controls",
            "detail": detail,
            "summary": summary,
            "subject_summary": subject_summary,
            "policy_impacts": policy_impacts,
            "recommendations": recommendations,
            "rules": rules,
            "explanation": explanation,
            "explanation_source": explanation_source,
            "artifacts": artifacts,
        }

    def execute_from_text(
        self,
        question: str,
        defaults: ScenarioRequest | None = None,
        lang: str = "en",
        run_by: str | None = None,
    ) -> dict[str, Any]:
        scenario, source = self.scenario_agent.parse(question, defaults)
        output = self.execute(scenario, lang, run_by=run_by)
        output["scenario_source"] = source
        return output
