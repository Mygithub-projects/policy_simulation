# Policy Simulation & Recommendation Agent

This is a compact MVP for the existing **Agentic AI for Education Workforce Planning** project.

## Architecture

- Orchestrator
- Scenario Agent
- Simulation Agent with Random Forest Forecasting Component
- Workforce Recommendation Agent
- Explanation Agent

All agents run behind one FastAPI backend. They are logical components, not separate apps. A later HTML/CSS/JavaScript frontend will call the API.

Co-teaching simulations can be scoped by `kodtingkatantahun`: `D1`-`D6`
for primary Year 1-6 and `T1`-`T5` for secondary Form 1-5. This uses the
grade-level workload in `base_murid_detail_2022_2026` without modifying the
source database.

## 1. Copy your two files

Copy the source database into:

```text
data/workforce_policy_agent_preclean_20260619_144113.duckdb
```

Copy the trained model into:

```text
models/random_forest_teacher_demand.pk1
```

Do not copy multiple `.duckdb` or model files into those folders unless you configure exact paths in `.env`.

## 2. Create an Anaconda environment

Open Anaconda Prompt in this project folder:

```powershell
conda create -n workforce-agent python=3.12 -y
conda activate workforce-agent
pip install -r requirements.txt
```

## 3. Optional Groq or OpenAI configuration

Copy `.env.example` to `.env`. For Groq:

```text
AI_PROVIDER=groq
GROQ_API_KEY=your-new-key
GROQ_MODEL=llama-3.3-70b-versatile
```

For OpenAI:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4.1-mini
```

Without an API key, the direct simulation interface remains fully functional and Agent Chat uses a local keyword parser plus deterministic explanation.

## 4. Run the smoke test

```powershell
python smoke_test.py
python api_smoke_test.py
```

The test verifies:

- DuckDB opens as read-only.
- `master_model_2022_2026` exists.
- The `.pk1` pipeline loads.
- A Science 2027 subject-option-ratio scenario completes.
- Outputs are written only to `outputs/`.

## 5. Start FastAPI

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002
```

Alternatively, double-click `run_api.bat` after activating the environment.

Open the application:

```text
http://127.0.0.1:8002
```

Open the interactive documentation:

```text
http://127.0.0.1:8002/docs
```

The HTML/CSS/JavaScript frontend is served by the same FastAPI process under `/app/`.

## Supported policy simulations

The application has two modes:

1. Single mode: one active policy.
2. Combined mode: two, three or all four policies using one formula engine.

Policies:

1. Target option ratio.
2. Annual subject teaching-hours per class.
3. Annual teaching-hour capacity per teacher (600 hours primary; 800 hours secondary).
4. Co-teaching share.

## Safety and assumptions

- The source DuckDB is never modified.
- Projection year is 2027.
- 2026 teacher supply remains constant for the MVP baseline.
- One available teacher is treated as 1.0 FTE.
- Policy calculations are deterministic Python formulas; the language model does not perform arithmetic.
- Recommendations require human review.

## Example Agent Chat question

```text
Forecast Science teacher demand in Johor for 2027 and simulate a 70% subject-option teacher target.
```
