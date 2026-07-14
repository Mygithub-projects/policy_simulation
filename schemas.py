"""Shared policy-scenario schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PolicyType(str, Enum):
    BASELINE = "baseline"
    OPTION_RATIO = "option_ratio"
    TEACHING_HOURS = "teaching_hours"
    TEACHER_CAPACITY = "teacher_capacity"
    COTEACHING = "coteaching"


class PolicyMode(str, Enum):
    SINGLE = "single"
    COMBINED = "combined"


@dataclass
class ScenarioRequest:
    question: str = ""
    target_year: int = 2027
    subject: str = "SEMUA"
    negeri: str = "SEMUA"
    ppd: str = "SEMUA"
    kod_sekolah: str = "SEMUA"
    kodtingkatantahun: list[str] = field(default_factory=lambda: ["SEMUA"])
    policy_mode: PolicyMode = PolicyMode.SINGLE
    policy_type: PolicyType = PolicyType.OPTION_RATIO
    active_policies: list[PolicyType] = field(default_factory=list)
    option_ratio: float = 0.70
    teaching_hours_change_pct: float = 0.0
    teacher_capacity_change_pct: float = 0.0
    coteaching_share_pct: float = 0.0

    def validate(self) -> "ScenarioRequest":
        if self.target_year != 2027:
            raise ValueError("MVP supports target year 2027 only.")
        self.subject = self.subject.upper().strip() or "SEMUA"
        self.negeri = self.negeri.upper().strip() or "SEMUA"
        self.ppd = self.ppd.upper().strip() or "SEMUA"
        self.kod_sekolah = self.kod_sekolah.upper().strip() or "SEMUA"
        raw_levels = self.kodtingkatantahun
        if isinstance(raw_levels, str):
            raw_levels = [raw_levels]
        allowed_levels = {"SEMUA", "D1", "D2", "D3", "D4", "D5", "D6", "T1", "T2", "T3", "T4", "T5"}
        cleaned_levels = list(dict.fromkeys(str(value).upper().strip() for value in raw_levels if str(value).strip()))
        if not cleaned_levels or "SEMUA" in cleaned_levels:
            cleaned_levels = ["SEMUA"]
        invalid_levels = set(cleaned_levels) - allowed_levels
        if invalid_levels:
            raise ValueError(
                "Invalid kodtingkatantahun: " + ", ".join(sorted(invalid_levels))
            )
        self.kodtingkatantahun = cleaned_levels
        if not isinstance(self.policy_mode, PolicyMode):
            self.policy_mode = PolicyMode(str(self.policy_mode))
        if not isinstance(self.policy_type, PolicyType):
            self.policy_type = PolicyType(str(self.policy_type))
        normalized_policies: list[PolicyType] = []
        for value in self.active_policies:
            policy = value if isinstance(value, PolicyType) else PolicyType(str(value))
            if policy not in normalized_policies:
                normalized_policies.append(policy)
        if not normalized_policies and self.policy_type != PolicyType.BASELINE:
            normalized_policies = [self.policy_type]
        if PolicyType.BASELINE in normalized_policies:
            if len(normalized_policies) > 1:
                raise ValueError("Baseline cannot be combined with a policy change.")
            normalized_policies = []
            self.policy_type = PolicyType.BASELINE
        if self.policy_mode == PolicyMode.SINGLE:
            if len(normalized_policies) > 1:
                raise ValueError("Single mode accepts one active policy only.")
            if normalized_policies:
                self.policy_type = normalized_policies[0]
        elif len(normalized_policies) < 2:
            raise ValueError("Combined mode requires at least two active policies.")
        if self.policy_mode == PolicyMode.COMBINED:
            self.policy_type = normalized_policies[0]
        self.active_policies = normalized_policies
        if self.subject not in {"SEMUA", "MATEMATIK", "SAINS"}:
            raise ValueError("Subject must be SEMUA, MATEMATIK or SAINS.")
        if not 0 <= float(self.option_ratio) <= 1:
            raise ValueError("Option ratio must be between 0 and 1.")
        if float(self.teacher_capacity_change_pct) <= -100:
            raise ValueError("The change in annual teacher teaching-hour capacity must be greater than -100%.")
        if not 0 <= float(self.coteaching_share_pct) <= 100:
            raise ValueError("Co-teaching share must be between 0% and 100%.")
        return self

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["policy_mode"] = self.policy_mode.value
        result["policy_type"] = self.policy_type.value
        result["active_policies"] = [policy.value for policy in self.active_policies]
        return result

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "ScenarioRequest":
        cleaned = dict(values)
        policy_value = cleaned.get("policy_type", PolicyType.OPTION_RATIO.value)
        cleaned["policy_type"] = (
            policy_value
            if isinstance(policy_value, PolicyType)
            else PolicyType(str(policy_value))
        )
        mode_value = cleaned.get("policy_mode", PolicyMode.SINGLE.value)
        cleaned["policy_mode"] = (
            mode_value
            if isinstance(mode_value, PolicyMode)
            else PolicyMode(str(mode_value))
        )
        cleaned["active_policies"] = [
            value if isinstance(value, PolicyType) else PolicyType(str(value))
            for value in cleaned.get("active_policies", [])
        ]
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in cleaned.items() if key in allowed}).validate()
