from __future__ import annotations

import numpy as np
import pandas as pd


class RecommendationAgent:
    """Applies transparent rule-based workforce recommendations."""

    @staticmethod
    def run(result: pd.DataFrame, lang: str = "en") -> tuple[pd.DataFrame, list[str]]:
        recommendations = result.copy()
        recommendations["priority_score"] = (
            recommendations["scenario_teacher_gap"] * 5
            + recommendations["scenario_option_gap"] * 3
            + np.maximum(recommendations["change_required"], 0) * 2
        )
        if lang == "bm":
            recommendations["priority_label"] = np.select(
                [
                    recommendations["priority_score"] >= 15,
                    recommendations["priority_score"] >= 5,
                ],
                ["TINGGI", "SEDERHANA"],
                default="RENDAH",
            )
            recommendations["recommended_action"] = np.select(
                [
                    recommendations["scenario_teacher_gap"] > 0,
                    recommendations["scenario_option_gap"] > 0,
                    recommendations["change_option_gap"] < 0,
                ],
                [
                    "Ambil guru baharu atau tempatkan semula guru ke sekolah ini",
                    "Tempatkan guru berkelayakan dalam opsyen mata pelajaran ini atau latih guru yang ada",
                    "Pantau kualiti pengajaran selepas mengubah sasaran nisbah guru opsyen mata pelajaran",
                ],
                default="Bilangan guru mencukupi; teruskan pemantauan",
            )
            rules = [
                "Sekolah dengan kekurangan guru perlu diutamakan untuk pelantikan baharu atau penempatan semula guru.",
                "Di mana guru opsyen mata pelajaran tidak mencukupi, tempatkan guru berkelayakan atau latih guru yang ada.",
                "Selepas mengubah sasaran nisbah guru opsyen mata pelajaran, pantau kualiti pengajaran untuk melindungi pembelajaran murid.",
            ]
        else:
            recommendations["priority_label"] = np.select(
                [
                    recommendations["priority_score"] >= 15,
                    recommendations["priority_score"] >= 5,
                ],
                ["HIGH", "MEDIUM"],
                default="LOW",
            )
            recommendations["recommended_action"] = np.select(
                [
                    recommendations["scenario_teacher_gap"] > 0,
                    recommendations["scenario_option_gap"] > 0,
                    recommendations["change_option_gap"] < 0,
                ],
                [
                    "Recruit a new teacher or redeploy a teacher to this school",
                    "Place a teacher qualified in this subject option or train an available teacher",
                    "Monitor teaching quality after changing the subject-option teacher target",
                ],
                default="Teacher numbers are sufficient; continue monitoring",
            )
            rules = [
                "Schools with teacher shortages should be prioritised for new appointments or teacher redeployment.",
                "Where subject-option teachers are insufficient, place a qualified teacher or train an available teacher.",
                "After changing the subject-option teacher target, monitor teaching quality to protect student learning.",
            ]
        top = recommendations.sort_values(
            ["priority_score", "scenario_teacher_gap", "scenario_option_gap"],
            ascending=False,
        ).head(30)
        return top, rules
