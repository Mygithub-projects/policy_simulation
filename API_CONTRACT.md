# API Contract for HTML/CSS/JavaScript Frontend

Start FastAPI:

```powershell
uvicorn main:app --reload
```

Interactive API documentation:

```text
http://127.0.0.1:8002/docs
```

## Health

```javascript
const health = await fetch("http://127.0.0.1:8002/api/health").then(r => r.json());
```

## Filter values

```javascript
const states = await fetch(
  "http://127.0.0.1:8002/api/filters/negeri"
).then(r => r.json());

const ppds = await fetch(
  "http://127.0.0.1:8002/api/filters/ppd?negeri=JOHOR"
).then(r => r.json());

const levels = await fetch(
  "http://127.0.0.1:8002/api/filters/kodtingkatantahun?negeri=JOHOR"
).then(r => r.json());
```

## Forecast 2027

```javascript
const forecast = await fetch("http://127.0.0.1:8002/api/forecast/2027", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    subject: "SAINS",
    negeri: "JOHOR",
    ppd: "SEMUA",
    kod_sekolah: "SEMUA"
  })
}).then(r => r.json());
```

## Direct policy simulation

```javascript
const result = await fetch("http://127.0.0.1:8002/api/simulate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    target_year: 2027,
    subject: "SAINS",
    negeri: "JOHOR",
    ppd: "SEMUA",
    kod_sekolah: "SEMUA",
    kodtingkatantahun: ["SEMUA"],
    policy_mode: "single",
    policy_type: "option_ratio",
    active_policies: ["option_ratio"],
    option_ratio: 0.70,
    teaching_hours_change_pct: 0,
    teacher_capacity_change_pct: 0,
    coteaching_share_pct: 0
  })
}).then(r => r.json());
```

Allowed `policy_type` values:

```text
baseline
option_ratio
teaching_hours
teacher_capacity
coteaching
```

`teaching_hours` means annual teaching hours for the selected subject per class.
The annual subject workload is `subject hours per year × number of classes`.

`teacher_capacity` means annual teaching-hour capacity per teacher: 600 hours
for primary and 800 hours for secondary before applying the selected percentage.

## Combined policy simulation

Use the same formula engine with two or more entries in `active_policies`:

```javascript
const combined = await fetch("http://127.0.0.1:8002/api/simulate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    target_year: 2027,
    subject: "SAINS",
    negeri: "JOHOR",
    ppd: "SEMUA",
    kod_sekolah: "SEMUA",
    kodtingkatantahun: ["D1", "D2", "D3"],
    policy_mode: "combined",
    policy_type: "option_ratio",
    active_policies: [
      "option_ratio",
      "teaching_hours",
      "teacher_capacity",
      "coteaching"
    ],
    option_ratio: 0.80,
    teaching_hours_change_pct: 10,
    teacher_capacity_change_pct: 5,
    coteaching_share_pct: 20
  })
}).then(r => r.json());
```

The response includes `policy_impacts` for each selected policy and the normal
`summary` for their combined effect.

## Co-teaching for selected school years/forms

`D1`-`D6` mean primary Year 1-6. `T1`-`T5` mean secondary Form 1-5.

```javascript
const coteaching = await fetch("http://127.0.0.1:8002/api/simulate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    target_year: 2027,
    subject: "SAINS",
    negeri: "JOHOR",
    ppd: "SEMUA",
    kod_sekolah: "SEMUA",
    kodtingkatantahun: ["D1", "D2", "D3"],
    policy_type: "coteaching",
    option_ratio: 0.60,
    teaching_hours_change_pct: 0,
    teacher_capacity_change_pct: 0,
    coteaching_share_pct: 50
  })
}).then(r => r.json());
```

The API assumes the selected grades' share of school-subject FTE in 2026 remains
the same in 2027. Co-teaching adds a second-teacher FTE only to that eligible
share. Relevant summary fields are:

```text
coteaching_eligible_fte_2027
coteaching_extra_fte_2027
coteaching_eligible_workload_hours_2026
```

## Natural-language agent workflow

```javascript
const agentResult = await fetch("http://127.0.0.1:8002/api/agent/run", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    question: "Forecast Science teacher demand in Johor for 2027 with a 70% subject-option ratio"
  })
}).then(r => r.json());
```

## Response fields required by the frontend

```text
scenario
summary
subject_summary
top_recommendations
rules
explanation
agent_trace
artifacts
ai_usage
```

`ai_usage` states whether Groq or OpenAI was used and identifies the configured model.
If the local fallback parser or deterministic explanation was used, the relevant
boolean is `false` and no AI model is claimed.

Use `summary` for KPI cards, `subject_summary` for charts and `top_recommendations` for the priority table.
