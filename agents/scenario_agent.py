from __future__ import annotations

import json
import re
from typing import Any

from config import get_ai_model, get_ai_provider_label, has_ai_key
from schemas import PolicyType, ScenarioRequest
from .common import _extract_json, _generate_ai_text


class ScenarioAgent:
    """Converts user language into a validated policy scenario."""

    def __init__(self, available_states: list[str]):
        self.available_states = [value for value in available_states if value != "SEMUA"]

    def parse(
        self,
        question: str,
        defaults: ScenarioRequest | None = None,
    ) -> tuple[ScenarioRequest, str]:
        defaults = defaults or ScenarioRequest(question=question)
        ai_error: Exception | None = None
        if has_ai_key():
            try:
                scenario, provider = self._parse_with_ai(question, defaults)
                return (
                    scenario,
                    f"{get_ai_provider_label(provider)} Scenario Agent ({get_ai_model(provider)})",
                )
            except Exception as error:
                ai_error = error
        try:
            return self._parse_fallback(question, defaults), "Local fallback parser"
        except Exception as fallback_error:
            if ai_error is not None:
                # The local fallback's own message ("use Combined Policies mode or
                # enable an AI provider") is misleading when an AI provider IS
                # enabled but temporarily failed (e.g. rate limit) — surface why.
                raise ValueError(
                    f"{get_ai_provider_label()} Scenario Agent failed ({ai_error}). "
                    f"Local fallback parser also could not handle this question: {fallback_error}"
                ) from fallback_error
            raise

    def _parse_with_ai(
        self,
        question: str,
        defaults: ScenarioRequest,
    ) -> tuple[ScenarioRequest, str]:
        instructions = """
You are the Scenario Agent for Malaysian education workforce planning.
Return JSON only. Never calculate results. Extract:
target_year, subject, negeri, ppd, kod_sekolah, policy_type,
option_ratio, teaching_hours_change_pct, teacher_capacity_change_pct,
coteaching_share_pct, kodtingkatantahun. subject must be exactly SEMUA,
MATEMATIK, or SAINS (map English "Mathematics"/"Math" to MATEMATIK and
"Science" to SAINS; default to SEMUA if no subject is mentioned).
kodtingkatantahun must be a JSON list using SEMUA, D1-D6 (primary) or
T1-T5 (secondary). Malay "Tahun"/"Darjah" and English "Year" both refer to
PRIMARY school grades and map to D-codes (e.g. "Year 1 to 3" or "Tahun 1
hingga 3" becomes D1, D2, D3) — never T-codes. Malay "Tingkatan" and
English "Form" refer to SECONDARY school grades and map to T-codes (e.g.
"Form 1 to 3" becomes T1, T2, T3). policy_type must be exactly one of: baseline,
option_ratio, teaching_hours, teacher_capacity, coteaching — never the
word "combined" or "single", those only ever go in policy_mode. Use
baseline only when the user asks for a forecast without a policy change.
When two or more policies are requested, set policy_type to the first one
in active_policies. Also return policy_mode (single or combined) and
active_policies as a JSON list. Use combined when two or more policies are
explicitly requested. Do not guess a policy or percentage.
Numeric scales matter and must not be mixed up: option_ratio is a
fraction between 0 and 1 (70% becomes 0.7). teaching_hours_change_pct and
teacher_capacity_change_pct are plain percentage-point numbers, negative
for a decrease (an increase of 10% becomes 10, a decrease of 10% becomes
-10). coteaching_share_pct is also a plain percentage number from 0 to
100, NOT a fraction (30% becomes 30, not 0.3).
"""
        prompt = json.dumps(
            {
                "question": question,
                "defaults": defaults.to_dict(),
                "allowed_states": self.available_states,
            },
            ensure_ascii=False,
        )
        values = defaults.to_dict()
        ai_text, provider = _generate_ai_text(instructions, prompt)
        values.update(_extract_json(ai_text))
        values["question"] = question

        # The model reliably extracts each policy's raw VALUE (e.g. a 70%
        # option ratio, a 20% co-teaching share) even on the runs where it
        # fails to also list that policy in active_policies — observed to be
        # inconsistent across identical calls despite temperature=0. Since a
        # dropped entry here silently ignores a policy the user explicitly
        # asked for (no exception, just a wrong scenario), don't trust the
        # model's active_policies membership alone: deterministically detect
        # which policies are textually present in the question (same keyword
        # approach the local fallback parser already relies on) and union
        # that with whatever the model returned.
        keyword_policies = self._detect_policy_keywords(question)
        ai_active_policies = {
            value for value in (values.get("active_policies") or [])
            if value in {member.value for member in PolicyType}
        }
        merged_policies = ai_active_policies | keyword_policies
        if merged_policies:
            # Preserve a stable order: whatever order the model returned first,
            # then any keyword-detected additions the model missed.
            ordered = [value for value in (values.get("active_policies") or []) if value in merged_policies]
            ordered += [value for value in merged_policies if value not in ordered]
            values["active_policies"] = ordered
            values["policy_mode"] = "combined" if len(ordered) > 1 else "single"

        # The model is occasionally asked for policy_type and policy_mode in the
        # same response and echoes "combined"/"single" (the policy_mode value)
        # into policy_type. Fall back to the first active policy in that case,
        # since active_policies is what schemas.validate() relies on anyway.
        valid_policy_types = {member.value for member in PolicyType}
        if values.get("policy_type") not in valid_policy_types:
            active_policies = values.get("active_policies") or []
            values["policy_type"] = active_policies[0] if active_policies else PolicyType.BASELINE.value

        return ScenarioRequest.from_dict(values), provider

    @staticmethod
    def _detect_policy_keywords(question: str) -> set[str]:
        """Deterministically detects which policies are textually mentioned in
        the question, independent of the AI's own active_policies judgment."""
        text = question.upper()
        detected: set[str] = set()
        if "CO-TEACH" in text or "COTEACH" in text or "PENGAJARAN BERSAMA" in text:
            detected.add(PolicyType.COTEACHING.value)
        if "KAPASITI" in text or "CAPACITY" in text:
            detected.add(PolicyType.TEACHER_CAPACITY.value)
        if "JAM" in text or "HOURS" in text or "WAKTU PENGAJARAN" in text or "TEACHING HOURS" in text:
            detected.add(PolicyType.TEACHING_HOURS.value)
        if "OPSYEN" in text or "NISBAH" in text or "OPTION" in text or "RATIO" in text:
            detected.add(PolicyType.OPTION_RATIO.value)
        return detected

    def _parse_fallback(
        self,
        question: str,
        defaults: ScenarioRequest,
    ) -> ScenarioRequest:
        text = question.upper()
        values = defaults.to_dict()
        values["question"] = question
        if "SAINS" in text or "SCIENCE" in text:
            values["subject"] = "SAINS"
        elif "MATEMATIK" in text or "MATH" in text:
            values["subject"] = "MATEMATIK"
        for state in self.available_states:
            if state in text:
                values["negeri"] = state
                break
        explicit_levels = re.findall(r"\b[DT][1-6]\b", text)
        if explicit_levels:
            values["kodtingkatantahun"] = list(dict.fromkeys(explicit_levels))
        else:
            primary_range = re.search(
                r"(?:TAHUN|DARJAH|YEAR|GRADE)\s*([1-6])\s*(?:HINGGA|SAMPAI|KE|TO|THROUGH|-)\s*([1-6])",
                text,
            )
            secondary_range = re.search(
                r"(?:TINGKATAN|FORM)\s*([1-5])\s*(?:HINGGA|SAMPAI|KE|TO|THROUGH|-)\s*([1-5])",
                text,
            )
            if primary_range:
                start, end = map(int, primary_range.groups())
                values["kodtingkatantahun"] = [
                    f"D{number}" for number in range(min(start, end), max(start, end) + 1)
                ]
            elif secondary_range:
                start, end = map(int, secondary_range.groups())
                values["kodtingkatantahun"] = [
                    f"T{number}" for number in range(min(start, end), max(start, end) + 1)
                ]
            else:
                primary_list = re.search(
                    r"(?:TAHUN|DARJAH|YEAR|GRADE)\s*((?:[1-6]\s*(?:,|DAN|AND)?\s*)+)", text
                )
                secondary_list = re.search(
                    r"(?:TINGKATAN|FORM)\s*((?:[1-5]\s*(?:,|DAN|AND)?\s*)+)", text
                )
                if primary_list:
                    values["kodtingkatantahun"] = [
                        f"D{number}" for number in re.findall(r"[1-6]", primary_list.group(1))
                    ]
                elif secondary_list:
                    values["kodtingkatantahun"] = [
                        f"T{number}" for number in re.findall(r"[1-5]", secondary_list.group(1))
                    ]
        percentages = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)]
        if len(percentages) > 1:
            raise ValueError(
                "The local parser cannot safely interpret multiple policies in one question. "
                "Please use Combined Policies mode on the form or enable an AI provider."
            )
        negative_change = any(
            word in text
            for word in (
                "KURANG",
                "DIKURANGKAN",
                "TURUN",
                "MENURUN",
                "PENGURANGAN",
                "REDUCE",
                "REDUCED",
                "DECREASE",
                "DECREASED",
                "LOWER",
            )
        )
        if "CO-TEACH" in text or "COTEACH" in text or "PENGAJARAN BERSAMA" in text:
            values["policy_type"] = PolicyType.COTEACHING.value
            if not percentages:
                raise ValueError(
                    "Please state the percentage of classes using co-teaching, for example 30%."
                )
            values["coteaching_share_pct"] = percentages[0]
        elif "KAPASITI" in text or "CAPACITY" in text:
            values["policy_type"] = PolicyType.TEACHER_CAPACITY.value
            if not percentages:
                raise ValueError(
                    "Please state the percentage change in annual teacher teaching-hour capacity, for example increase by 10%."
                )
            values["teacher_capacity_change_pct"] = (
                -percentages[0] if negative_change else percentages[0]
            )
        elif "JAM" in text or "HOURS" in text:
            values["policy_type"] = PolicyType.TEACHING_HOURS.value
            if not percentages:
                raise ValueError(
                    "Please state the percentage change in annual subject teaching hours, for example increase by 10%."
                )
            values["teaching_hours_change_pct"] = (
                -percentages[0] if negative_change else percentages[0]
            )
        elif "OPSYEN" in text or "NISBAH" in text or "OPTION" in text or "RATIO" in text:
            values["policy_type"] = PolicyType.OPTION_RATIO.value
            if not percentages:
                raise ValueError(
                    "Please state the target subject-option teacher ratio, for example 70%."
                )
            values["option_ratio"] = percentages[0] / 100
        elif any(word in text for word in ("RAMAL", "UNJUR", "KEPERLUAN", "FORECAST", "DEMAND", "REQUIREMENT")):
            values["policy_type"] = PolicyType.BASELINE.value
        else:
            raise ValueError(
                "The intended policy is unclear. Please specify Subject-Option Teacher Ratio, "
                "Annual Subject Teaching Hours, Annual Teacher Teaching-Hour Capacity or Co-teaching, "
                "together with a percentage value."
            )
        return ScenarioRequest.from_dict(values)
