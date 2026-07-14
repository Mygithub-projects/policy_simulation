"""Retrain and re-save the Random Forest teacher demand model.

Run this script whenever the saved .pk1 file is incompatible with the
current scikit-learn version (e.g. 'SimpleImputer has no attribute _fill_dtype').

Usage:
    python retrain_model.py
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from config import get_database_path, get_model_path

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

NUMERIC_FEATURES = [f for f in FEATURES if f not in ("negeri", "subjek")]
CATEGORICAL_FEATURES = ["negeri", "subjek"]

# Target: teacher FTE required for the following year.
# The table contains rows for 2022-2026.  For each school-subject-year row,
# the target is the FTE required in the *next* year (lead by 1 year).
# Rows where no next-year record exists are dropped automatically.
TARGET = "fte_required_next_year"


def load_training_data(database_path: Path) -> pd.DataFrame:
    query = """
        WITH base AS (
            SELECT
                tahun                                   AS source_year,
                kod_sekolah,
                negeri,
                subjek,
                CAST(enrolmen_murid AS DOUBLE)          AS prev_enrolment,
                CAST(bil_kelas AS DOUBLE)               AS prev_classes,
                FTE_guru_diperlukan_akhir               AS prev_fte_required,
                guru_diperlukan_akhir                   AS prev_teachers_required,
                CAST(guru_sedia_ada AS DOUBLE)          AS prev_teachers_available,
                CAST(guru_opsyen_semasa AS DOUBLE)      AS prev_option_teachers,
                CAST(guru_bukan_opsyen_semasa AS DOUBLE) AS prev_nonoption_teachers,
                nisbah_opsyen_semasa                    AS prev_option_ratio,
                FTE_guru_diperlukan_akhir               AS fte_required_current_year
            FROM master_model_2022_2026
            WHERE subjek IN ('MATEMATIK', 'SAINS')
        ),
        with_lead AS (
            SELECT
                b.*,
                LEAD(b.fte_required_current_year)
                    OVER (PARTITION BY b.kod_sekolah, b.subjek
                          ORDER BY b.source_year)  AS fte_required_next_year
            FROM base b
        )
        SELECT *
        FROM with_lead
        WHERE fte_required_next_year IS NOT NULL
        ORDER BY source_year, kod_sekolah, subjek
    """
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        data = connection.execute(query).df()
    finally:
        connection.close()
    return data


def build_pipeline() -> Pipeline:
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
    ])
    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
    ])
    preprocessor = ColumnTransformer([
        ("num", numeric_transformer, NUMERIC_FEATURES),
        ("cat", categorical_transformer, CATEGORICAL_FEATURES),
    ])
    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", RandomForestRegressor(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )),
    ])


def main() -> None:
    database_path = get_database_path()
    model_path = get_model_path()

    print(f"Loading training data from: {database_path}")
    data = load_training_data(database_path)
    print(f"  Rows loaded: {len(data)}")
    print(f"  Years:       {sorted(data['source_year'].unique().tolist())}")

    X = data[FEATURES]
    y = data[TARGET].values

    print("Training Random Forest pipeline ...")
    pipeline = build_pipeline()
    pipeline.fit(X, y)

    # Quick sanity check: predictions should be non-negative
    sample_pred = np.clip(pipeline.predict(X[:5]), 0, None)
    print(f"  Sample predictions (first 5): {sample_pred.round(2).tolist()}")

    # Back up the existing model file before overwriting
    if model_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = model_path.with_name(
            model_path.stem + f"_backup_{timestamp}" + model_path.suffix
        )
        shutil.copy2(model_path, backup_path)
        print(f"  Existing model backed up to: {backup_path.name}")

    joblib.dump(pipeline, model_path)
    print(f"Model saved to: {model_path}")
    print("Done. Restart the FastAPI server and run smoke tests.")


if __name__ == "__main__":
    main()
