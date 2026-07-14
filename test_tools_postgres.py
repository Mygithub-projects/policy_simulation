from pathlib import Path

from config import get_model_path
from tools import WorkforceTools


def test_health_check_reports_postgres_tables():
    tools = WorkforceTools(Path("unused"), get_model_path())
    result = tools.health_check()
    assert result["access_mode"] == "read_only"


def test_get_filter_options_returns_semua_first():
    tools = WorkforceTools(Path("unused"), get_model_path())
    options = tools.get_filter_options("negeri")
    assert options[0] == "SEMUA"
    assert len(options) > 1
