# Project ERD and Relational Scheme

## Project

Education Workforce Policy Simulation and Recommendation Agent

This document explains the main database entities, attributes, and logical relationships used by the agentic AI workforce planning project.

The schema is based on the DuckDB database:

```text
data/workforce_policy_agent_preclean_20260619_144113.duckdb
```

Important note: DuckDB does not enforce foreign keys in this MVP. The relationships below are **logical analytical relationships** used by the application and simulation engine.

## High-Level Entity Relationship Diagram

```mermaid
erDiagram
    BASE_MURID_DETAIL {
        INTEGER tahun
        VARCHAR kod_sekolah
        VARCHAR negeri
        VARCHAR ppd
        VARCHAR subjek
        VARCHAR KODTINGKATANTAHUN
        BIGINT enrolmen_murid
        BIGINT bil_kelas
        INTEGER jam_setahun_subjek
        INTEGER kapasiti_jam_guru_setahun
        BIGINT beban_jam_tahunan
        DOUBLE FTE_guru_diperlukan
        DOUBLE guru_diperlukan
    }

    BASE_SUPPLY_GURU {
        INTEGER tahun
        VARCHAR kputama
        VARCHAR kod_sekolah
        VARCHAR negeri
        VARCHAR ppd
        VARCHAR jantina
        DATE tarikh_lahir
        BIGINT umur_anggaran
        INTEGER umur_opsyen_bersara
        VARCHAR opsyendominan
        INTEGER flag_opsyen_matematik
        INTEGER flag_opsyen_sains
        INTEGER flag_kontrak
        BIGINT baki_tahun_ke_persaraan
        INTEGER flag_hampir_bersara
    }

    MASTER_MODEL {
        INTEGER tahun
        VARCHAR kod_sekolah
        VARCHAR negeri
        VARCHAR ppd
        VARCHAR subjek
        HUGEINT enrolmen_murid
        HUGEINT bil_kelas
        HUGEINT beban_jam_tahunan
        DOUBLE FTE_guru_diperlukan_akhir
        DOUBLE guru_diperlukan_akhir
        BIGINT guru_sedia_ada
        BIGINT guru_opsyen_semasa
        BIGINT guru_bukan_opsyen_semasa
        DOUBLE nisbah_opsyen_semasa
    }

    POLICY_PARAMETERS {
        VARCHAR parameter_code
        VARCHAR subjek
        VARCHAR kodtingkatantahun
        DOUBLE nilai
        VARCHAR unit
        DATE effective_from
        DATE effective_to
    }

    SCENARIO_VERSION {
        VARCHAR scenario_id
        VARCHAR scenario_name
        VARCHAR scenario_type
        TIMESTAMP created_at
        VARCHAR created_by
        VARCHAR status
    }

    SCENARIO_PARAMETER_VALUES {
        VARCHAR scenario_id
        VARCHAR parameter_code
        VARCHAR subjek
        VARCHAR kodtingkatantahun
        DOUBLE nilai
        VARCHAR unit
        DATE effective_from
        DATE effective_to
    }

    SIMULATION_RUN_LOG {
        VARCHAR run_id
        VARCHAR scenario_id
        TIMESTAMP run_timestamp
        VARCHAR run_by
        VARCHAR run_type
        VARCHAR target_scope
    }

    RECOMMENDATION_OUTPUT_LOG {
        VARCHAR output_id
        VARCHAR run_id
        INTEGER tahun
        VARCHAR kod_sekolah
        VARCHAR negeri
        VARCHAR ppd
        VARCHAR subjek
        DOUBLE priority_score
        VARCHAR priority_label
        VARCHAR recommended_action
    }

    RECOMMENDATION_RULES {
        VARCHAR rule_id
        VARCHAR rule_name
        VARCHAR rule_group
        INTEGER priority_level
        VARCHAR condition_desc
        VARCHAR recommended_action
        VARCHAR action_category
        INTEGER is_active
    }

    SIM_RATIO {
        INTEGER tahun
        VARCHAR kod_sekolah
        VARCHAR negeri
        VARCHAR ppd
        VARCHAR subjek
        DOUBLE sasaran_opsyen_ratio_baru
        DOUBLE target_guru_opsyen_baru
        DOUBLE jurang_opsyen_baru
    }

    SIM_JAM {
        INTEGER tahun
        VARCHAR kod_sekolah
        VARCHAR negeri
        VARCHAR ppd
        VARCHAR subjek
        DOUBLE beban_jam_tahunan_baru
        DOUBLE FTE_guru_diperlukan_baru
        DOUBLE guru_diperlukan_baru
        DOUBLE delta_guru
    }

    SIM_COTEACHING {
        INTEGER tahun
        VARCHAR kod_sekolah
        VARCHAR negeri
        VARCHAR ppd
        VARCHAR subjek
        DOUBLE FTE_asal
        DOUBLE guru_asal
        DOUBLE tambahan_beban_sains
        DOUBLE FTE_baru
        DOUBLE guru_diperlukan_baru
        DOUBLE delta_guru
    }

    MASTER_MODEL ||--o{ BASE_MURID_DETAIL : "aggregates demand by tahun/kod_sekolah/subjek"
    MASTER_MODEL ||--o{ BASE_SUPPLY_GURU : "uses supply by tahun/kod_sekolah and subject option"
    POLICY_PARAMETERS ||--o{ SCENARIO_PARAMETER_VALUES : "provides default policy values"
    SCENARIO_VERSION ||--o{ SCENARIO_PARAMETER_VALUES : "has scenario parameters"
    SCENARIO_VERSION ||--o{ SIMULATION_RUN_LOG : "has simulation runs"
    SIMULATION_RUN_LOG ||--o{ RECOMMENDATION_OUTPUT_LOG : "produces recommendations"
    RECOMMENDATION_RULES ||--o{ RECOMMENDATION_OUTPUT_LOG : "guides recommendation logic"
    MASTER_MODEL ||--o{ SIM_RATIO : "source for option-ratio simulation"
    MASTER_MODEL ||--o{ SIM_JAM : "source for teaching-hours simulation"
    MASTER_MODEL ||--o{ SIM_COTEACHING : "source for co-teaching simulation"
```

## Relational Scheme

### 1. Student Demand Detail

```text
base_murid_detail_2022_2026(
    tahun,
    kod_sekolah,
    negeri,
    ppd,
    subjek,
    KODTINGKATANTAHUN,
    enrolmen_murid,
    bil_kelas,
    jam_setahun_subjek,
    kapasiti_jam_guru_setahun,
    beban_jam_tahunan,
    FTE_guru_diperlukan,
    guru_diperlukan,
    snapshot_label,
    source_database
)
```

Suggested logical grain:

```text
tahun + kod_sekolah + subjek + KODTINGKATANTAHUN
```

Role:

Detailed teaching-demand table by year, school, subject, and year/form level.

### 2. Teacher Supply Profile

```text
base_supply_guru_2022_2026(
    tahun,
    kputama,
    kod_sekolah,
    negeri,
    ppd,
    jantina,
    tarikh_lahir,
    umur_anggaran,
    umur_opsyen_bersara,
    opsyendominan,
    kodstatusstaf,
    gredjawatanhakiki,
    gredpenyandangsemasa,
    jenis_pengisian,
    tarikhmula_kontrak,
    tarikhtamat_kontrak,
    tarikhtamat_perkhidmatan,
    guru_dlp,
    flag_opsyen_matematik,
    flag_opsyen_sains,
    flag_kontrak,
    baki_tahun_ke_persaraan,
    flag_hampir_bersara,
    snapshot_label,
    source_database
)
```

Suggested logical grain:

```text
tahun + kputama
```

Role:

Individual teacher supply profile table. The `kputama` field is anonymized into dummy IDs.

### 3. Master Analytical Model

```text
master_model_2022_2026(
    tahun,
    kod_sekolah,
    negeri,
    ppd,
    subjek,
    enrolmen_murid,
    bil_kelas,
    beban_jam_tahunan,
    FTE_guru_diperlukan_akhir,
    guru_diperlukan_akhir,
    guru_sedia_ada,
    guru_opsyen_semasa,
    guru_bukan_opsyen_semasa,
    nisbah_opsyen_semasa,
    snapshot_label,
    source_database
)
```

Suggested logical grain:

```text
tahun + kod_sekolah + subjek
```

Role:

Main modelling and simulation table. This is the key table used by the Random Forest forecasting component and policy simulation engine.

### 4. Policy Parameter Reference

```text
policy_parameters(
    parameter_code,
    subjek,
    kodtingkatantahun,
    nilai,
    unit,
    effective_from,
    effective_to,
    sumber_dokumen,
    catatan
)
```

Suggested logical grain:

```text
parameter_code + subjek + kodtingkatantahun + effective_from
```

Role:

Stores baseline or reference policy values.

### 5. Scenario Version

```text
scenario_version(
    scenario_id,
    scenario_name,
    scenario_type,
    description,
    created_at,
    created_by,
    status,
    notes
)
```

Suggested logical key:

```text
scenario_id
```

Role:

Stores scenario metadata.

### 6. Scenario Parameter Values

```text
scenario_parameter_values(
    scenario_id,
    parameter_code,
    subjek,
    kodtingkatantahun,
    nilai,
    unit,
    effective_from,
    effective_to,
    source_type,
    notes
)
```

Suggested logical grain:

```text
scenario_id + parameter_code + subjek + kodtingkatantahun
```

Role:

Stores parameter values used in a specific scenario.

### 7. Simulation Run Log

```text
simulation_run_log(
    run_id,
    scenario_id,
    run_timestamp,
    run_by,
    run_type,
    target_scope,
    notes
)
```

Suggested logical key:

```text
run_id
```

Role:

Records metadata for each simulation run.

### 8. Recommendation Output Log

```text
recommendation_output_log(
    output_id,
    run_id,
    tahun,
    kod_sekolah,
    negeri,
    ppd,
    subjek,
    priority_score,
    priority_label,
    recommended_action,
    reason_summary,
    created_at
)
```

Suggested logical key:

```text
output_id
```

Role:

Stores recommendation outputs produced by a simulation run.

### 9. Recommendation Rules

```text
recommendation_rules(
    rule_id,
    rule_name,
    rule_group,
    priority_level,
    condition_desc,
    recommended_action,
    action_category,
    notes,
    is_active
)
```

Suggested logical key:

```text
rule_id
```

Role:

Stores transparent rule-based recommendation logic.

### 10. Simulation Output Tables

These tables store precomputed or reference simulation outputs for 2026 policy scenarios.

```text
sim_ratio_2026(
    tahun,
    kod_sekolah,
    negeri,
    ppd,
    subjek,
    enrolmen_murid,
    bil_kelas,
    FTE_guru_diperlukan_akhir,
    guru_diperlukan_akhir,
    guru_sedia_ada,
    guru_opsyen_semasa,
    guru_bukan_opsyen_semasa,
    nisbah_opsyen_semasa,
    sasaran_opsyen_ratio_baru,
    target_guru_opsyen_baru,
    jurang_opsyen_baru
)
```

```text
sim_jam_2026(
    tahun,
    kod_sekolah,
    negeri,
    ppd,
    subjek,
    enrolmen_murid,
    bil_kelas,
    beban_jam_tahunan_baru,
    FTE_guru_diperlukan_baru,
    guru_diperlukan_baru,
    FTE_asal,
    guru_diperlukan_asal,
    delta_fte,
    delta_guru
)
```

```text
sim_coteaching_2026(
    tahun,
    kod_sekolah,
    negeri,
    ppd,
    subjek,
    FTE_asal,
    guru_asal,
    tambahan_beban_sains,
    tambahan_fte_sains,
    FTE_baru,
    guru_diperlukan_baru,
    delta_guru
)
```

Suggested logical grain:

```text
tahun + kod_sekolah + subjek
```

Role:

Stores simulation results or historical scenario references by school and subject.

## Main Analytical Flow

```mermaid
flowchart TD
    A["base_murid_detail_2022_2026<br/>Student demand by school, subject, year/form"] --> C["master_model_2022_2026<br/>School-subject analytical model"]
    B["base_supply_guru_2022_2026<br/>Teacher supply profile"] --> C
    D["policy_parameters<br/>Baseline policy values"] --> E["scenario_parameter_values<br/>Scenario-specific policy values"]
    F["scenario_version<br/>Scenario metadata"] --> E
    E --> G["Simulation Agent<br/>Policy calculation"]
    C --> G
    G --> H["Recommendation Agent<br/>Priority and action rules"]
    I["recommendation_rules<br/>Transparent recommendation rules"] --> H
    H --> J["recommendation_output_log<br/>Recommendation output"]
    F --> K["simulation_run_log<br/>Run metadata"]
    K --> J
```

## Simplified Explanation for Stakeholders

The database can be understood as five main groups:

| Group | Tables | Meaning |
|---|---|---|
| Demand data | `base_murid_detail_2022_2026`, `master_model_2022_2026` | Shows how many students, classes, teaching hours, and teachers are needed. |
| Supply data | `base_supply_guru_2022_2026` | Shows available teachers, subject option, contract status, and retirement risk. |
| Policy data | `policy_parameters`, `scenario_parameter_values`, `scenario_version` | Stores baseline policy settings and scenario-specific changes. |
| Simulation data | `sim_ratio_2026`, `sim_jam_2026`, `sim_coteaching_2026`, `simulation_run_log` | Stores or supports policy simulation runs. |
| Recommendation data | `recommendation_rules`, `recommendation_output_log` | Stores rule-based recommendation logic and generated recommendations. |

## Relationship Summary

| Relationship | Join Logic | Explanation |
|---|---|---|
| `base_murid_detail_2022_2026` to `master_model_2022_2026` | `tahun + kod_sekolah + subjek` | Detail-level demand is aggregated into the master school-subject model. |
| `base_supply_guru_2022_2026` to `master_model_2022_2026` | `tahun + kod_sekolah`, with subject-option logic | Teacher supply supports school-subject demand and option-ratio analysis. |
| `scenario_version` to `scenario_parameter_values` | `scenario_id` | One scenario can contain many changed policy parameters. |
| `policy_parameters` to `scenario_parameter_values` | `parameter_code + subjek + kodtingkatantahun` | Scenario values are based on or override baseline policy parameters. |
| `scenario_version` to `simulation_run_log` | `scenario_id` | A scenario may be run multiple times. |
| `simulation_run_log` to `recommendation_output_log` | `run_id` | One simulation run may produce many recommendations. |
| `recommendation_rules` to `recommendation_output_log` | Rule logic, not enforced FK | Rules guide the actions written into recommendation outputs. |
| `master_model_2022_2026` to `sim_ratio_2026` | `tahun + kod_sekolah + subjek` | Option-ratio scenario output uses the master model as baseline. |
| `master_model_2022_2026` to `sim_jam_2026` | `tahun + kod_sekolah + subjek` | Teaching-hours scenario output uses the master model as baseline. |
| `master_model_2022_2026` to `sim_coteaching_2026` | `tahun + kod_sekolah + subjek` | Co-teaching scenario output uses the master model as baseline. |

## Notes for AI Developers

- Do not treat these relationships as enforced database constraints.
- The source database should normally be opened in read-only mode.
- `master_model_2022_2026` is the main table for forecasting and simulation.
- `base_murid_detail_2022_2026` is needed when simulation requires year/form-level workload.
- `base_supply_guru_2022_2026` contains sensitive teacher-level data and must be handled carefully.
- Recommendations are rule-based and require human review.
