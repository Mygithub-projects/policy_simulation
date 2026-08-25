"""Pydantic request models exposed by FastAPI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from schemas import PolicyMode, PolicyType, ScenarioRequest


class ScenarioInput(BaseModel):
    target_year: Literal[2027] = 2027
    subject: Literal["SEMUA", "MATEMATIK", "SAINS"] = "SEMUA"
    negeri: str = "SEMUA"
    ppd: str = "SEMUA"
    kod_sekolah: str = "SEMUA"
    kodtingkatantahun: list[
        Literal["SEMUA", "D1", "D2", "D3", "D4", "D5", "D6", "T1", "T2", "T3", "T4", "T5"]
    ] = Field(default_factory=lambda: ["SEMUA"])
    policy_mode: PolicyMode = PolicyMode.SINGLE
    policy_type: PolicyType = PolicyType.OPTION_RATIO
    active_policies: list[PolicyType] = Field(default_factory=list)
    option_ratio: float = Field(default=0.70, ge=0, le=1)
    teaching_hours_change_pct: float = Field(default=0.0, ge=-100, le=500)
    teacher_capacity_change_pct: float = Field(default=0.0, gt=-100, le=500)
    coteaching_share_pct: float = Field(default=0.0, ge=0, le=100)
    lang: Literal["bm", "en"] = "en"

    def to_scenario(self) -> ScenarioRequest:
        return ScenarioRequest.from_dict(self.model_dump())


class AgentQuestionInput(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    lang: Literal["bm", "en"] = "en"


class LoginInput(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class CreateUserInput(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    role_name: Literal["superadmin", "user"] = "user"
    can_view_audit_log: bool = False
    lang: Literal["bm", "en"] = "bm"


class ChangePasswordInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ForecastInput(BaseModel):
    subject: Literal["SEMUA", "MATEMATIK", "SAINS"] = "SEMUA"
    negeri: str = "SEMUA"
    ppd: str = "SEMUA"
    kod_sekolah: str = "SEMUA"


class SaveRunInput(BaseModel):
    run_id: str = Field(min_length=1, max_length=80)
    run_name: str = Field(default="", max_length=200)


class ReportKpiCard(BaseModel):
    label: str
    value: str
    sub_label: str = ""
    color: Literal["default", "teal", "amber", "green", "red"] = "default"
    value_style: Literal["default", "positive", "negative"] = "default"


class ReportChartDataset(BaseModel):
    label: str
    data: list[float]


class ReportChartSpec(BaseModel):
    """Raw chart data (not a rendered image) — the backend draws the chart
    itself with ReportLab's native charting, so sizing/resolution is always
    consistent regardless of the browser's on-screen layout at capture time.
    See reports/pdf_report.py for the drawing logic."""

    labels: list[str] = Field(default_factory=list)
    datasets: list[ReportChartDataset] = Field(default_factory=list)


class ReportPdfInput(BaseModel):
    """Request body for POST /api/runs/{run_id}/report.pdf.

    All text is already translated client-side (same as the rest of the app) —
    this model carries pre-formatted strings/labels, not raw scenario fields,
    so the backend never needs its own i18n logic.

    section_titles keys: title, params_title, summary_title, kpi_title,
    charts_title, chart_comparison, chart_subject, chart_risk, footer,
    params_scope_subtitle, params_policy_subtitle.
    """

    lang: Literal["bm", "en"] = "en"
    generated_date: str
    scope_rows: list[tuple[str, str]]
    policy_rows: list[tuple[str, str]]
    explanation_text: str
    explanation_source_label: str = ""
    kpi_cards: list[ReportKpiCard]
    chart_comparison: ReportChartSpec
    chart_subject: ReportChartSpec
    chart_risk: ReportChartSpec
    section_titles: dict[str, str]
