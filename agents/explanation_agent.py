from __future__ import annotations

import json
from typing import Any

import pandas as pd

from config import get_ai_model, get_ai_provider_label, has_ai_key
from schemas import PolicyMode, PolicyType, ScenarioRequest
from .common import _generate_ai_text


class ExplanationAgent:
    """Explains verified simulation results without changing calculations."""

    @staticmethod
    def _level_scope_label(scenario: ScenarioRequest, lang: str = "en") -> str:
        """Human-readable school-level scope, computed deterministically so
        neither the fallback text nor the AI provider has to interpret the
        raw kodtingkatantahun codes itself: D1-D6 are Darjah/Tahun (primary,
        sekolah rendah), T1-T5 are Tingkatan (secondary, sekolah menengah).
        """
        levels = scenario.kodtingkatantahun
        if levels == ["SEMUA"]:
            return "semua tahun dan tingkatan" if lang == "bm" else "all years and forms"
        d_codes = sorted(level for level in levels if level.startswith("D"))
        t_codes = sorted(level for level in levels if level.startswith("T"))
        parts = []
        if d_codes:
            codes_text = ", ".join(d_codes)
            parts.append(
                f"Tahun {codes_text} (sekolah rendah)" if lang == "bm"
                else f"Year {codes_text} (primary school)"
            )
        if t_codes:
            codes_text = ", ".join(t_codes)
            parts.append(
                f"Tingkatan {codes_text} (sekolah menengah)" if lang == "bm"
                else f"Form {codes_text} (secondary school)"
            )
        if not parts:
            return ", ".join(levels)
        return (" dan " if lang == "bm" else " and ").join(parts)

    def run(
        self,
        scenario: ScenarioRequest,
        summary: dict[str, Any],
        subject_summary: pd.DataFrame,
        lang: str = "en",
    ) -> tuple[str, str]:
        fallback = self._fallback_explanation(scenario, summary, subject_summary, lang)
        if not has_ai_key():
            return fallback, "Deterministic explanation"
        try:
            level_scope_label = self._level_scope_label(scenario, lang)
            if lang == "bm":
                instructions = (
                    "Anda adalah Ejen Penjelasan. Terangkan simulasi tenaga kerja guru Malaysia yang "
                    "telah disahkan ini dalam bahasa Melayu yang jelas dan mudah difahami untuk pengguna bukan teknikal. "
                    "Elakkan istilah FTE, baseline, senario, unjuran, jurang opsyen dan nama peraturan teknikal. "
                    "Asingkan dengan jelas: anggaran Model Random Forest tanpa perubahan dasar, kesan dasar terhadap "
                    "keperluan guru, kekurangan guru sebelum dasar, kekurangan guru selepas dasar, dan kekurangan baru "
                    "akibat dasar. Jangan huraikan change_required sebagai bilangan guru yang perlu diambil terus. "
                    "Terangkan apa yang berubah dan tindakan yang perlu dipertimbangkan. Jangan cipta nombor. "
                    "Apabila menyebut skop tahun/tingkatan yang diliputi, gunakan field 'level_scope_label' yang "
                    "disediakan dalam data secara terus — jangan tafsir semula kod kodtingkatantahun sendiri. "
                    "Kod bermula 'D' (D1-D6) ialah Darjah di sekolah rendah; kod bermula 'T' (T1-T5) ialah "
                    "Tingkatan di sekolah menengah. Jangan sekali-kali labelkan kod 'D' sebagai sekolah menengah "
                    "atau kod 'T' sebagai sekolah rendah. "
                    "Nyatakan andaian dan bahawa ini adalah sokongan keputusan, bukan keputusan automatik."
                )
            else:
                instructions = (
                    "You are the Explanation Agent. Explain the supplied verified Malaysian "
                    "teacher-workforce simulation in clear, everyday English for a non-technical user. "
                    "Avoid the terms FTE, baseline, scenario, projection, option gap and technical rule names. "
                    "Clearly separate the Random Forest Regressor estimate without policy changes, the policy's "
                    "effect on teacher need, teacher shortage before policy, teacher shortage after policy, and "
                    "the new shortage caused by policy. Never describe change_required as the number that must "
                    "be recruited directly. Explain what changed and what action should be considered. Do not invent numbers. "
                    "When stating which years/forms are covered, use the provided 'level_scope_label' field "
                    "verbatim — do not reinterpret the raw kodtingkatantahun codes yourself. Codes starting "
                    "with 'D' (D1-D6) are Darjah/Year levels in primary school; codes starting with 'T' (T1-T5) "
                    "are Tingkatan/Form levels in secondary school. Never label a 'D' code as secondary school "
                    "or a 'T' code as primary school. "
                    "State assumptions and that this is decision support, not an automatic decision."
                )
            prompt = json.dumps(
                {
                    "scenario": scenario.to_dict(),
                    "level_scope_label": level_scope_label,
                    "summary": summary,
                    "subject_summary": subject_summary.to_dict(orient="records"),
                },
                ensure_ascii=False,
            )
            ai_text, provider = _generate_ai_text(instructions, prompt)
            return (
                ai_text,
                f"{get_ai_provider_label(provider)} Explanation Agent ({get_ai_model(provider)})",
            )
        except Exception:
            return fallback, "Deterministic fallback after AI provider error"

    @staticmethod
    def _fallback_explanation(
        scenario: ScenarioRequest,
        summary: dict[str, Any],
        subject_summary: pd.DataFrame,
        lang: str = "en",
    ) -> str:
        if lang == "bm":
            policy_labels = {
                PolicyType.BASELINE: "unjuran tanpa perubahan dasar",
                PolicyType.OPTION_RATIO: "sasaran guru opsyen mata pelajaran",
                PolicyType.TEACHING_HOURS: "waktu pengajaran tahunan",
                PolicyType.TEACHER_CAPACITY: "kapasiti waktu pengajaran tahunan guru",
                PolicyType.COTEACHING: "pengajaran bersama",
            }
            policy_description = (
                "gabungan dasar: "
                + ", ".join(policy_labels[policy] for policy in scenario.active_policies)
                if scenario.policy_mode == PolicyMode.COMBINED
                else policy_labels[scenario.policy_type]
            )
            level_scope = ExplanationAgent._level_scope_label(scenario, lang)
            change = summary["change_required"]
            baseline_gap = summary.get("baseline_teacher_gap", 0)
            scenario_gap = summary.get("scenario_teacher_gap", 0)
            gap_change = summary.get("change_teacher_gap", scenario_gap - baseline_gap)
            if change > 0:
                change_text = f"Dasar ini meningkatkan permintaan sebanyak {change:,} guru."
            elif change < 0:
                change_text = f"Dasar ini mengurangkan permintaan sebanyak {abs(change):,} guru."
            else:
                change_text = "Jumlah permintaan guru tidak berubah."
            if gap_change > 0:
                gap_text = (
                    f"Selepas mengambil kira guru yang tersedia, kekurangan meningkat daripada {baseline_gap:,} "
                    f"kepada {scenario_gap:,} guru. Dasar ini mewujudkan {gap_change:,} jawatan kekurangan baru."
                )
            elif gap_change < 0:
                gap_text = (
                    f"Selepas mengambil kira guru yang tersedia, kekurangan berkurang daripada {baseline_gap:,} "
                    f"kepada {scenario_gap:,} guru, pengurangan sebanyak {abs(gap_change):,}."
                )
            else:
                gap_text = f"Selepas mengambil kira guru yang tersedia, kekurangan kekal pada {scenario_gap:,} guru."
            option_text = ""
            if PolicyType.OPTION_RATIO in scenario.active_policies:
                option_text = (
                    f" Kekurangan guru opsyen mata pelajaran selepas dasar ialah "
                    f"{summary['scenario_option_gap']:,} guru."
                )
            return (
                f"Analisis {policy_description} untuk {scenario.target_year} merangkumi "
                f"{summary['schools']:,} sekolah merentasi {level_scope}. "
                f"Model Random Forest menganggarkan permintaan sebanyak {summary['baseline_required_2027']:,} "
                "guru jika dasar tidak berubah. "
                f"Selepas perubahan dasar, anggaran menjadi {summary['scenario_required_2027']:,} guru. "
                f"{change_text} Perubahan ini bukan bilangan guru yang perlu diambil secara terus. "
                f"{gap_text}{option_text} Anggaran ini menganggap bilangan guru 2026 kekal tersedia pada 2027. "
                "Ini adalah sokongan keputusan dan masih perlu disemak oleh pegawai yang bertanggungjawab."
            )
        else:
            policy_labels = {
                PolicyType.BASELINE: "forecast without policy change",
                PolicyType.OPTION_RATIO: "subject-option teacher target",
                PolicyType.TEACHING_HOURS: "annual subject teaching hours",
                PolicyType.TEACHER_CAPACITY: "annual teacher teaching-hour capacity",
                PolicyType.COTEACHING: "co-teaching",
            }
            policy_description = (
                "combined policies: "
                + ", ".join(policy_labels[policy] for policy in scenario.active_policies)
                if scenario.policy_mode == PolicyMode.COMBINED
                else policy_labels[scenario.policy_type]
            )
            level_scope = ExplanationAgent._level_scope_label(scenario, lang)
            change = summary["change_required"]
            baseline_gap = summary.get("baseline_teacher_gap", 0)
            scenario_gap = summary.get("scenario_teacher_gap", 0)
            gap_change = summary.get("change_teacher_gap", scenario_gap - baseline_gap)
            if change > 0:
                change_text = f"The policy increases demand by {change:,} teachers."
            elif change < 0:
                change_text = f"The policy reduces demand by {abs(change):,} teachers."
            else:
                change_text = "Total teacher demand does not change."
            if gap_change > 0:
                gap_text = (
                    f"After accounting for available teachers, the shortage increases from {baseline_gap:,} "
                    f"to {scenario_gap:,} teachers. The policy creates {gap_change:,} new shortage positions."
                )
            elif gap_change < 0:
                gap_text = (
                    f"After accounting for available teachers, the shortage decreases from {baseline_gap:,} "
                    f"to {scenario_gap:,} teachers, a reduction of {abs(gap_change):,}."
                )
            else:
                gap_text = f"After accounting for available teachers, the shortage remains at {scenario_gap:,} teachers."
            option_text = ""
            if PolicyType.OPTION_RATIO in scenario.active_policies:
                option_text = (
                    f" The subject-option teacher shortage after policy is "
                    f"{summary['scenario_option_gap']:,} teachers."
                )
            return (
                f"The {policy_description} analysis for {scenario.target_year} covers "
                f"{summary['schools']:,} schools across {level_scope}. "
                f"The Random Forest Regressor estimates a demand of {summary['baseline_required_2027']:,} "
                "teachers if policy remains unchanged. "
                f"After the policy change, the estimate becomes {summary['scenario_required_2027']:,} teachers. "
                f"{change_text} This change is not the number of teachers that should be recruited directly. "
                f"{gap_text}{option_text} The estimate assumes 2026 teacher numbers remain available in 2027. "
                "This is decision support and must still be reviewed by the responsible officers."
            )
