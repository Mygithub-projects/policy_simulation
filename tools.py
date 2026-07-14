"""Read-only data, ML forecasting and deterministic policy-simulation tools."""

from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import joblib
import numpy as np
import pandas as pd

from config import get_output_directories
from schemas import PolicyType, ScenarioRequest


FEATURES = [
    "source_year",
    "prev_enrolment",
    "prev_classes",
    "prev_fte_required",
    "prev_teachers_required",
    "prev_teachers_available",
    "prev_option_teachers",
    "prev_nonoption_teachers",
    "prev_option_ratio",
    "negeri",
    "subjek",
]


def write_summary_csv(
    output_dir: Path,
    run_id: str,
    summary: dict[str, Any],
    subject_summary: pd.DataFrame,
) -> Path:
    """Writes an aggregated KPI + per-subject CSV (no per-school rows)."""
    csv_path = output_dir / f"{run_id}_summary.csv"
    kpi_rows = pd.DataFrame(
        [{"metric": key, "value": value} for key, value in summary.items()]
    )
    subject_rows = subject_summary.rename(columns={"subjek": "subject"}).copy()
    if "subject" in subject_rows.columns:
        subject_rows["subject"] = subject_rows["subject"].replace(
            {"SAINS": "SCIENCE", "MATEMATIK": "MATHEMATICS"}
        )
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        handle.write("# KPI Summary\n")
        kpi_rows.to_csv(handle, index=False)
        handle.write("\n# Per-Subject Summary\n")
        subject_rows.to_csv(handle, index=False)
    return csv_path


class WorkforceTools:
    """Tool layer used by the Simulation Agent."""

    def __init__(self, database_path: Path, model_path: Path):
        self.database_path = Path(database_path).resolve()
        self.model_path = Path(model_path).resolve()
        try:
            with self.model_path.open("rb") as file:
                self.model = pickle.load(file)
        except Exception:
            # Supports .pk1 files created through joblib.dump as well as pickle.dump.
            self.model = joblib.load(self.model_path)
        self.health_check()

    def _connect(self):
        return duckdb.connect(str(self.database_path), read_only=True)

    def health_check(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            access_mode = connection.execute(
                "SELECT current_setting('access_mode')"
            ).fetchone()[0]
            tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        finally:
            connection.close()
        if str(access_mode).lower() != "read_only":
            raise RuntimeError("Source database is not opened read-only.")
        required_tables = {
            "master_model_2022_2026",
            "base_murid_detail_2022_2026",
        }
        missing_tables = required_tables - tables
        if missing_tables:
            raise RuntimeError(
                "Required table(s) missing: " + ", ".join(sorted(missing_tables))
            )
        if not hasattr(self.model, "predict"):
            raise RuntimeError("The supplied model does not expose predict().")
        return {
            "database": self.database_path.name,
            "access_mode": access_mode,
            "model": self.model_path.name,
        }

    def get_filter_options(
        self,
        field: str,
        negeri: str = "SEMUA",
        ppd: str = "SEMUA",
    ) -> list[str]:
        allowed = {"negeri", "ppd", "kod_sekolah", "kodtingkatantahun"}
        if field not in allowed:
            raise ValueError(f"Unsupported filter field: {field}")
        clauses = ["tahun = 2026"]
        parameters: list[Any] = []
        if field in {"ppd", "kod_sekolah", "kodtingkatantahun"} and negeri != "SEMUA":
            clauses.append("negeri = ?")
            parameters.append(negeri)
        if field in {"kod_sekolah", "kodtingkatantahun"} and ppd != "SEMUA":
            clauses.append("ppd = ?")
            parameters.append(ppd)
        source_table = (
            "base_murid_detail_2022_2026"
            if field == "kodtingkatantahun"
            else "master_model_2022_2026"
        )
        source_column = "KODTINGKATANTAHUN" if field == "kodtingkatantahun" else field
        query = f"""
            SELECT DISTINCT {source_column}
            FROM {source_table}
            WHERE {' AND '.join(clauses)} AND {source_column} IS NOT NULL
            ORDER BY {source_column}
        """
        connection = self._connect()
        try:
            values = [row[0] for row in connection.execute(query, parameters).fetchall()]
        finally:
            connection.close()
        return ["SEMUA", *values]

    def load_coteaching_scope(self, scenario: ScenarioRequest) -> pd.DataFrame:
        """Return the selected grade's 2026 FTE share for each school-subject.

        The selected grade composition from 2026 is used as the assumption for
        the 2027 forecast. The source database remains read-only.
        """
        clauses = ["tahun = 2026", "subjek IN ('MATEMATIK', 'SAINS')"]
        parameters: list[Any] = []
        for column, value in [
            ("subjek", scenario.subject),
            ("negeri", scenario.negeri),
            ("ppd", scenario.ppd),
            ("kod_sekolah", scenario.kod_sekolah),
        ]:
            if value != "SEMUA":
                clauses.append(f"{column} = ?")
                parameters.append(value)

        selected_levels = scenario.kodtingkatantahun
        level_condition = "TRUE"
        level_parameters: list[Any] = []
        if selected_levels != ["SEMUA"]:
            placeholders = ", ".join("?" for _ in selected_levels)
            level_condition = f"KODTINGKATANTAHUN IN ({placeholders})"
            level_parameters.extend(selected_levels)

        query = f"""
            SELECT
                kod_sekolah,
                subjek,
                SUM(CAST(FTE_guru_diperlukan AS DOUBLE)) AS total_detail_fte_2026,
                SUM(
                    CASE WHEN {level_condition}
                         THEN CAST(FTE_guru_diperlukan AS DOUBLE) ELSE 0 END
                ) AS selected_detail_fte_2026,
                SUM(
                    CASE WHEN {level_condition}
                         THEN CAST(beban_jam_tahunan AS DOUBLE) ELSE 0 END
                ) AS selected_workload_hours_2026
            FROM base_murid_detail_2022_2026
            WHERE {' AND '.join(clauses)}
            GROUP BY kod_sekolah, subjek
        """
        # The level condition occurs twice in the query.
        query_parameters = [*level_parameters, *level_parameters, *parameters]
        connection = self._connect()
        try:
            scope = connection.execute(query, query_parameters).df()
        finally:
            connection.close()
        return scope

    def load_2026_features(self, scenario: ScenarioRequest) -> pd.DataFrame:
        clauses = ["tahun = 2026", "subjek IN ('MATEMATIK', 'SAINS')"]
        parameters: list[Any] = []
        for column, value in [
            ("subjek", scenario.subject),
            ("negeri", scenario.negeri),
            ("ppd", scenario.ppd),
            ("kod_sekolah", scenario.kod_sekolah),
        ]:
            if value != "SEMUA":
                clauses.append(f"{column} = ?")
                parameters.append(value)
        query = f"""
            SELECT
                tahun AS source_year,
                kod_sekolah,
                negeri,
                ppd,
                subjek,
                CAST(enrolmen_murid AS DOUBLE) AS prev_enrolment,
                CAST(bil_kelas AS DOUBLE) AS prev_classes,
                FTE_guru_diperlukan_akhir AS prev_fte_required,
                guru_diperlukan_akhir AS prev_teachers_required,
                CAST(guru_sedia_ada AS DOUBLE) AS prev_teachers_available,
                CAST(guru_opsyen_semasa AS DOUBLE) AS prev_option_teachers,
                CAST(guru_bukan_opsyen_semasa AS DOUBLE) AS prev_nonoption_teachers,
                nisbah_opsyen_semasa AS prev_option_ratio
            FROM master_model_2022_2026
            WHERE {' AND '.join(clauses)}
            ORDER BY kod_sekolah, subjek
        """
        connection = self._connect()
        try:
            data = connection.execute(query, parameters).df()
        finally:
            connection.close()
        if data.empty:
            raise ValueError("No 2026 records found for the selected scope.")
        return data

    def forecast_2027(self, scenario: ScenarioRequest) -> pd.DataFrame:
        data = self.load_2026_features(scenario)
        raw_prediction = np.clip(self.model.predict(data[FEATURES]), 0, None)
        data["projection_year"] = 2027
        data["baseline_required_2027_raw"] = raw_prediction
        data["baseline_required_2027"] = np.rint(raw_prediction).astype(int)
        denominator = data["prev_teachers_required"].replace(0, np.nan)
        demand_scale = data["baseline_required_2027"] / denominator
        data["baseline_fte_2027"] = (
            data["prev_fte_required"] * demand_scale
        ).fillna(data["baseline_required_2027_raw"])
        data["available_2027_assumption"] = data[
            "prev_teachers_available"
        ].fillna(0).astype(int)
        data["option_teachers_2027_assumption"] = data[
            "prev_option_teachers"
        ].fillna(0).astype(int)
        return data

    def simulate_policy(self, scenario: ScenarioRequest) -> pd.DataFrame:
        scenario.validate()
        active_policies = set(scenario.active_policies)
        result = self.forecast_2027(scenario)
        available = result["prev_teachers_available"].replace(0, np.nan)
        calculated_current_ratio = result["prev_option_teachers"] / available
        current_option_ratio = (
            result["prev_option_ratio"]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(calculated_current_ratio)
            .fillna(0)
            .clip(0, 1)
        )
        # "Without policy change" means maintaining each school's current
        # option-teacher mix, not imposing a fixed 90% target.
        result["baseline_option_ratio"] = current_option_ratio
        result["scenario_option_ratio"] = current_option_ratio
        result["scenario_fte_2027"] = result["baseline_fte_2027"]
        result["scenario_required_2027"] = result["baseline_required_2027"]
        result["coteaching_eligible_ratio_2026"] = 0.0
        result["coteaching_eligible_fte_2027"] = 0.0
        result["coteaching_extra_fte_2027"] = 0.0
        result["coteaching_eligible_workload_hours_2026"] = 0.0
        result["teaching_hours_multiplier"] = 1.0
        result["teacher_capacity_multiplier"] = 1.0
        result["coteaching_multiplier"] = 1.0

        if PolicyType.OPTION_RATIO in active_policies:
            result["scenario_option_ratio"] = float(scenario.option_ratio)

        if PolicyType.TEACHING_HOURS in active_policies:
            workload_multiplier = 1 + float(scenario.teaching_hours_change_pct) / 100
            if workload_multiplier < 0:
                raise ValueError("Teaching-hours multiplier cannot be negative.")
            result["teaching_hours_multiplier"] = workload_multiplier

        if PolicyType.TEACHER_CAPACITY in active_policies:
            capacity_multiplier = 1 + float(scenario.teacher_capacity_change_pct) / 100
            if capacity_multiplier <= 0:
                raise ValueError("Teacher-capacity multiplier must be positive.")
            result["teacher_capacity_multiplier"] = capacity_multiplier

        if PolicyType.COTEACHING in active_policies:
            share = float(scenario.coteaching_share_pct) / 100
            scope = self.load_coteaching_scope(scenario)
            result = result.merge(scope, on=["kod_sekolah", "subjek"], how="left")
            total_detail = result["total_detail_fte_2026"].replace(0, np.nan)
            eligible_ratio = (
                result["selected_detail_fte_2026"] / total_detail
            ).fillna(0).clip(0, 1)
            result["coteaching_eligible_ratio_2026"] = eligible_ratio
            result["coteaching_eligible_fte_2027"] = (
                result["baseline_fte_2027"] * eligible_ratio
                * result["teaching_hours_multiplier"]
                / result["teacher_capacity_multiplier"]
            )
            result["coteaching_extra_fte_2027"] = (
                result["coteaching_eligible_fte_2027"] * share
            )
            result["coteaching_eligible_workload_hours_2026"] = result[
                "selected_workload_hours_2026"
            ].fillna(0)
            result["coteaching_multiplier"] = 1 + eligible_ratio * share

        result["combined_fte_multiplier"] = (
            result["teaching_hours_multiplier"]
            / result["teacher_capacity_multiplier"]
            * result["coteaching_multiplier"]
        )
        result["scenario_fte_2027"] = (
            result["baseline_fte_2027"] * result["combined_fte_multiplier"]
        )
        calculated_required = np.ceil(result["scenario_fte_2027"]).astype(int)
        multiplier = result["combined_fte_multiplier"]
        result["scenario_required_2027"] = np.where(
            multiplier > 1.0000001,
            np.maximum(calculated_required, result["baseline_required_2027"]),
            np.where(
                multiplier < 0.9999999,
                np.minimum(calculated_required, result["baseline_required_2027"]),
                result["baseline_required_2027"],
            ),
        ).astype(int)

        result["baseline_teacher_gap"] = np.maximum(
            result["baseline_required_2027"] - result["available_2027_assumption"], 0
        )
        result["scenario_teacher_gap"] = np.maximum(
            result["scenario_required_2027"] - result["available_2027_assumption"], 0
        )
        result["baseline_target_option_teachers"] = np.ceil(
            result["baseline_required_2027"] * result["baseline_option_ratio"]
        ).astype(int)
        result["scenario_target_option_teachers"] = np.ceil(
            result["scenario_required_2027"] * result["scenario_option_ratio"]
        ).astype(int)
        result["baseline_option_gap"] = np.maximum(
            result["baseline_target_option_teachers"]
            - result["option_teachers_2027_assumption"],
            0,
        )
        result["scenario_option_gap"] = np.maximum(
            result["scenario_target_option_teachers"]
            - result["option_teachers_2027_assumption"],
            0,
        )
        result["change_required"] = (
            result["scenario_required_2027"] - result["baseline_required_2027"]
        )
        result["change_teacher_gap"] = (
            result["scenario_teacher_gap"] - result["baseline_teacher_gap"]
        )
        result["change_option_gap"] = (
            result["scenario_option_gap"] - result["baseline_option_gap"]
        )
        return result

    @staticmethod
    def summarize(result: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
        summary = {
            "school_subject_rows": int(len(result)),
            "schools": int(result["kod_sekolah"].nunique()),
            "baseline_required_2027": int(result["baseline_required_2027"].sum()),
            "scenario_required_2027": int(result["scenario_required_2027"].sum()),
            "change_required": int(result["change_required"].sum()),
            "baseline_teacher_gap": int(result["baseline_teacher_gap"].sum()),
            "scenario_teacher_gap": int(result["scenario_teacher_gap"].sum()),
            "change_teacher_gap": int(result["change_teacher_gap"].sum()),
            "baseline_option_gap": int(result["baseline_option_gap"].sum()),
            "scenario_option_gap": int(result["scenario_option_gap"].sum()),
            "change_option_gap": int(result["change_option_gap"].sum()),
            "combined_fte_multiplier": round(
                float(result["scenario_fte_2027"].sum())
                / max(float(result["baseline_fte_2027"].sum()), 1e-9),
                4,
            ),
            "coteaching_eligible_fte_2027": round(
                float(result["coteaching_eligible_fte_2027"].sum()), 2
            ),
            "coteaching_extra_fte_2027": round(
                float(result["coteaching_extra_fte_2027"].sum()), 2
            ),
            "coteaching_eligible_workload_hours_2026": round(
                float(result["coteaching_eligible_workload_hours_2026"].sum()), 2
            ),
        }
        subject_summary = (
            result.groupby("subjek", as_index=False)
            .agg(
                schools=("kod_sekolah", "nunique"),
                baseline_required_2027=("baseline_required_2027", "sum"),
                scenario_required_2027=("scenario_required_2027", "sum"),
                change_required=("change_required", "sum"),
                scenario_teacher_gap=("scenario_teacher_gap", "sum"),
                baseline_option_gap=("baseline_option_gap", "sum"),
                scenario_option_gap=("scenario_option_gap", "sum"),
                change_option_gap=("change_option_gap", "sum"),
            )
        )
        return summary, subject_summary

    @staticmethod
    def save_run(
        scenario: ScenarioRequest,
        result: pd.DataFrame,
        summary: dict[str, Any],
        subject_summary: pd.DataFrame,
        run_by: str | None = None,
    ) -> dict[str, str]:
        run_id = datetime.now().strftime("RUN_%Y%m%d_%H%M%S_%f")
        errors: list[str] = []
        for output_dir in get_output_directories():
            csv_path = output_dir / f"{run_id}_detail.csv"
            json_path = output_dir / f"{run_id}_summary.json"
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                export_result = result.rename(
                    columns={
                        "kod_sekolah": "school_code",
                        "negeri": "state",
                        "subjek": "subject",
                    }
                ).copy()
                if "subject" in export_result.columns:
                    export_result["subject"] = export_result["subject"].replace(
                        {"SAINS": "SCIENCE", "MATEMATIK": "MATHEMATICS"}
                    )
                export_result.to_csv(csv_path, index=False)
                summary_csv_path = write_summary_csv(output_dir, run_id, summary, subject_summary)
                json_path.write_text(
                    json.dumps(
                        {
                            "run_id": run_id,
                            "scenario": scenario.to_dict(),
                            "summary": summary,
                            "run_by": run_by,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return {
                    "run_id": run_id,
                    "detail_csv": str(csv_path),
                    "summary_csv": str(summary_csv_path),
                    "summary_json": str(json_path),
                    "output_directory": str(output_dir),
                }
            except OSError as error:
                errors.append(f"{output_dir}: {error}")
        raise PermissionError(
            "Unable to save simulation output. Tried: " + " | ".join(errors)
        )


class MockWorkforceTools:
    """Lightweight fallback used for tests when real tools cannot initialize."""

    def __init__(self, database_path: Path, model_path: Path):
        self.database_path = Path(database_path)
        self.model_path = Path(model_path)

    def health_check(self) -> dict[str, Any]:
        return {"database": self.database_path.name, "access_mode": "read_only", "model": self.model_path.name}

    def get_filter_options(self, field: str, negeri: str = "SEMUA", ppd: str = "SEMUA") -> list[str]:
        # Minimal, deterministic options for tests
        return ["SEMUA", "JOHOR", "KEDAH"]

    def load_coteaching_scope(self, scenario: ScenarioRequest):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "kod_sekolah": "S1",
                    "subjek": scenario.subjek if hasattr(scenario, "subjek") else "SAINS",
                    "total_detail_fte_2026": 10,
                    "selected_detail_fte_2026": 5,
                    "selected_workload_hours_2026": 100,
                }
            ]
        )

    def load_2026_features(self, scenario: ScenarioRequest):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "source_year": 2026,
                    "kod_sekolah": "S1",
                    "negeri": scenario.negeri,
                    "ppd": scenario.ppd,
                    "subjek": scenario.subject if hasattr(scenario, "subject") else "SAINS",
                    "prev_enrolment": 100,
                    "prev_classes": 4,
                    "prev_fte_required": 10,
                    "prev_teachers_required": 10,
                    "prev_teachers_available": 8,
                    "prev_option_teachers": 2,
                    "prev_nonoption_teachers": 6,
                    "prev_option_ratio": 0.2,
                }
            ]
        )

    def forecast_2027(self, scenario: ScenarioRequest):
        data = self.load_2026_features(scenario)
        data["projection_year"] = 2027
        data["baseline_required_2027"] = 10
        data["baseline_fte_2027"] = 10.0
        data["available_2027_assumption"] = data["prev_teachers_available"].fillna(0).astype(int)
        data["option_teachers_2027_assumption"] = data["prev_option_teachers"].fillna(0).astype(int)
        return data

    def simulate_policy(self, scenario: ScenarioRequest):
        import pandas as pd

        data = self.forecast_2027(scenario)
        data["prev_teachers_available"] = data["prev_teachers_available"].astype(int)
        data["prev_option_teachers"] = data["prev_option_teachers"].astype(int)
        data["baseline_option_ratio"] = data["prev_option_ratio"]
        # Apply a simple policy effect when option ratio changes
        option_ratio = getattr(scenario, "option_ratio", 0.7)
        data["scenario_option_ratio"] = option_ratio
        data["scenario_required_2027"] = data["baseline_required_2027"].astype(int)
        data["change_required"] = data["scenario_required_2027"] - data["baseline_required_2027"]
        data["baseline_teacher_gap"] = (data["baseline_required_2027"] - data["available_2027_assumption"]).clip(lower=0)
        data["scenario_teacher_gap"] = (data["scenario_required_2027"] - data["available_2027_assumption"]).clip(lower=0)
        data["change_teacher_gap"] = data["scenario_teacher_gap"] - data["baseline_teacher_gap"]
        data["baseline_option_gap"] = (data["baseline_required_2027"] * data["baseline_option_ratio"]).astype(int) - data["option_teachers_2027_assumption"]
        data["scenario_option_gap"] = (data["baseline_required_2027"] * data["scenario_option_ratio"]).astype(int) - data["option_teachers_2027_assumption"]
        data["change_option_gap"] = data["scenario_option_gap"] - data["baseline_option_gap"]
        data["combined_fte_multiplier"] = 1.0
        data["coteaching_eligible_fte_2027"] = 0.0
        data["coteaching_extra_fte_2027"] = 0.0
        data["coteaching_eligible_workload_hours_2026"] = 0.0
        return data

    @staticmethod
    def summarize(result: "pd.DataFrame") -> tuple[dict[str, Any], "pd.DataFrame"]:
        summary = {
            "school_subject_rows": int(len(result)),
            "schools": int(result["kod_sekolah"].nunique()) if "kod_sekolah" in result else 1,
            "baseline_required_2027": int(result["baseline_required_2027"].sum()),
            "scenario_required_2027": int(result["scenario_required_2027"].sum()),
            "change_required": int(result["change_required"].sum()),
            "baseline_teacher_gap": int(result["baseline_teacher_gap"].sum()),
            "scenario_teacher_gap": int(result["scenario_teacher_gap"].sum()),
            "change_teacher_gap": int(result["change_teacher_gap"].sum()),
            "baseline_option_gap": int(result["baseline_option_gap"].sum()),
            "scenario_option_gap": int(result["scenario_option_gap"].sum()),
            "change_option_gap": int(result["change_option_gap"].sum()),
            "combined_fte_multiplier": 1.0,
            "coteaching_eligible_fte_2027": 0.0,
            "coteaching_extra_fte_2027": 0.0,
            "coteaching_eligible_workload_hours_2026": 0.0,
        }
        import pandas as pd

        subject_summary = pd.DataFrame(
            [
                {
                    "subjek": result.iloc[0].get("subjek", "SAINS"),
                    "schools": int(result["kod_sekolah"].nunique()) if "kod_sekolah" in result else 1,
                    "baseline_required_2027": int(result["baseline_required_2027"].sum()),
                    "scenario_required_2027": int(result["scenario_required_2027"].sum()),
                    "change_required": int(result["change_required"].sum()),
                    "scenario_teacher_gap": int(result["scenario_teacher_gap"].sum()),
                    "baseline_option_gap": int(result["baseline_option_gap"].sum()),
                    "scenario_option_gap": int(result["scenario_option_gap"].sum()),
                    "change_option_gap": int(result["change_option_gap"].sum()),
                }
            ]
        )
        return summary, subject_summary

    def save_run(self, scenario: ScenarioRequest, result: "pd.DataFrame", summary: dict[str, Any]) -> dict[str, str]:
        run_id = "RUN_TEST"
        for output_dir in get_output_directories():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                csv_path = output_dir / f"{run_id}_detail.csv"
                json_path = output_dir / f"{run_id}_summary.json"
                result.to_csv(csv_path, index=False)
                json_path.write_text(
                    json.dumps({"run_id": run_id, "scenario": scenario.to_dict(), "summary": summary}, indent=2),
                    encoding="utf-8",
                )
                return {"run_id": run_id, "detail_csv": str(csv_path), "summary_json": str(json_path), "output_directory": str(output_dir)}
            except Exception:
                continue
        raise PermissionError("Unable to save simulation output for mock tool")


class MockWorkforceTools:
    """Lightweight fallback used for tests when real tools cannot initialize."""

    def __init__(self, database_path: Path, model_path: Path):
        self.database_path = Path(database_path)
        self.model_path = Path(model_path)

    def health_check(self) -> dict[str, Any]:
        return {"database": self.database_path.name, "access_mode": "read_only", "model": self.model_path.name}

    def get_filter_options(self, field: str, negeri: str = "SEMUA", ppd: str = "SEMUA") -> list[str]:
        # Minimal, deterministic options for tests
        return ["SEMUA", "JOHOR", "KEDAH"]

    def load_coteaching_scope(self, scenario: ScenarioRequest):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "kod_sekolah": "S1",
                    "subjek": scenario.subjek if hasattr(scenario, "subjek") else "SAINS",
                    "total_detail_fte_2026": 10,
                    "selected_detail_fte_2026": 5,
                    "selected_workload_hours_2026": 100,
                }
            ]
        )

    def load_2026_features(self, scenario: ScenarioRequest):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "source_year": 2026,
                    "kod_sekolah": "S1",
                    "negeri": scenario.negeri,
                    "ppd": scenario.ppd,
                    "subjek": scenario.subject if hasattr(scenario, "subject") else "SAINS",
                    "prev_enrolment": 100,
                    "prev_classes": 4,
                    "prev_fte_required": 10,
                    "prev_teachers_required": 10,
                    "prev_teachers_available": 8,
                    "prev_option_teachers": 2,
                    "prev_nonoption_teachers": 6,
                    "prev_option_ratio": 0.2,
                }
            ]
        )

    def forecast_2027(self, scenario: ScenarioRequest):
        data = self.load_2026_features(scenario)
        data["projection_year"] = 2027
        data["baseline_required_2027"] = 10
        data["baseline_fte_2027"] = 10.0
        data["available_2027_assumption"] = data["prev_teachers_available"].fillna(0).astype(int)
        data["option_teachers_2027_assumption"] = data["prev_option_teachers"].fillna(0).astype(int)
        return data

    def simulate_policy(self, scenario: ScenarioRequest):
        import pandas as pd

        data = self.forecast_2027(scenario)
        data["prev_teachers_available"] = data["prev_teachers_available"].astype(int)
        data["prev_option_teachers"] = data["prev_option_teachers"].astype(int)
        data["baseline_option_ratio"] = data["prev_option_ratio"]
        # Apply a simple policy effect when option ratio changes
        option_ratio = getattr(scenario, "option_ratio", 0.7)
        data["scenario_option_ratio"] = option_ratio
        data["scenario_required_2027"] = data["baseline_required_2027"].astype(int)
        data["change_required"] = data["scenario_required_2027"] - data["baseline_required_2027"]
        data["baseline_teacher_gap"] = (data["baseline_required_2027"] - data["available_2027_assumption"]).clip(lower=0)
        data["scenario_teacher_gap"] = (data["scenario_required_2027"] - data["available_2027_assumption"]).clip(lower=0)
        data["change_teacher_gap"] = data["scenario_teacher_gap"] - data["baseline_teacher_gap"]
        data["baseline_option_gap"] = (data["baseline_required_2027"] * data["baseline_option_ratio"]).astype(int) - data["option_teachers_2027_assumption"]
        data["scenario_option_gap"] = (data["baseline_required_2027"] * data["scenario_option_ratio"]).astype(int) - data["option_teachers_2027_assumption"]
        data["change_option_gap"] = data["scenario_option_gap"] - data["baseline_option_gap"]
        data["combined_fte_multiplier"] = 1.0
        data["coteaching_eligible_fte_2027"] = 0.0
        data["coteaching_extra_fte_2027"] = 0.0
        data["coteaching_eligible_workload_hours_2026"] = 0.0
        return data

    @staticmethod
    def summarize(result: "pd.DataFrame") -> tuple[dict[str, Any], "pd.DataFrame"]:
        summary = {
            "school_subject_rows": int(len(result)),
            "schools": int(result["kod_sekolah"].nunique()) if "kod_sekolah" in result else 1,
            "baseline_required_2027": int(result["baseline_required_2027"].sum()),
            "scenario_required_2027": int(result["scenario_required_2027"].sum()),
            "change_required": int(result["change_required"].sum()),
            "baseline_teacher_gap": int(result["baseline_teacher_gap"].sum()),
            "scenario_teacher_gap": int(result["scenario_teacher_gap"].sum()),
            "change_teacher_gap": int(result["change_teacher_gap"].sum()),
            "baseline_option_gap": int(result["baseline_option_gap"].sum()),
            "scenario_option_gap": int(result["scenario_option_gap"].sum()),
            "change_option_gap": int(result["change_option_gap"].sum()),
            "combined_fte_multiplier": 1.0,
            "coteaching_eligible_fte_2027": 0.0,
            "coteaching_extra_fte_2027": 0.0,
            "coteaching_eligible_workload_hours_2026": 0.0,
        }
        import pandas as pd

        subject_summary = pd.DataFrame(
            [
                {
                    "subjek": result.iloc[0].get("subjek", "SAINS"),
                    "schools": int(result["kod_sekolah"].nunique()) if "kod_sekolah" in result else 1,
                    "baseline_required_2027": int(result["baseline_required_2027"].sum()),
                    "scenario_required_2027": int(result["scenario_required_2027"].sum()),
                    "change_required": int(result["change_required"].sum()),
                    "scenario_teacher_gap": int(result["scenario_teacher_gap"].sum()),
                    "baseline_option_gap": int(result["baseline_option_gap"].sum()),
                    "scenario_option_gap": int(result["scenario_option_gap"].sum()),
                    "change_option_gap": int(result["change_option_gap"].sum()),
                }
            ]
        )
        return summary, subject_summary

    def save_run(
        self,
        scenario: ScenarioRequest,
        result: "pd.DataFrame",
        summary: dict[str, Any],
        subject_summary: "pd.DataFrame",
        run_by: str | None = None,
    ) -> dict[str, str]:
        # Minimal save that mirrors WorkforceTools.save_run
        run_id = "RUN_TEST"
        for output_dir in get_output_directories():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                csv_path = output_dir / f"{run_id}_detail.csv"
                json_path = output_dir / f"{run_id}_summary.json"
                result.to_csv(csv_path, index=False)
                summary_csv_path = write_summary_csv(output_dir, run_id, summary, subject_summary)
                json_path.write_text(
                    json.dumps(
                        {"run_id": run_id, "scenario": scenario.to_dict(), "summary": summary, "run_by": run_by},
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return {
                    "run_id": run_id,
                    "detail_csv": str(csv_path),
                    "summary_csv": str(summary_csv_path),
                    "summary_json": str(json_path),
                    "output_directory": str(output_dir),
                }
            except Exception:
                continue
        raise PermissionError("Unable to save simulation output for mock tool")
