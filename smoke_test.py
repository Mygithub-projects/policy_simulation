"""Run this before FastAPI to verify database, model and one full workflow."""

from agents import Orchestrator
from config import get_database_path, get_model_path
from schemas import PolicyType, ScenarioRequest
from tools import WorkforceTools


tools = WorkforceTools(get_database_path(), get_model_path())
print("Health:", tools.health_check())

scenario = ScenarioRequest(
    target_year=2027,
    subject="SAINS",
    policy_type=PolicyType.OPTION_RATIO,
    option_ratio=0.70,
)
result = Orchestrator(tools).execute(scenario)
print("Summary:", result["summary"])
print("Explanation:", result["explanation"])
print("Artifacts:", result["artifacts"])
