"""FastAPI backend for the Education Workforce Policy Agent MVP."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
import db
import hashlib
import hmac
import json
import secrets

import email_utils

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from agents import Orchestrator
from api_models import (
    AgentQuestionInput,
    ChangePasswordInput,
    CreateUserInput,
    ForecastInput,
    LoginInput,
    SaveRunInput,
    ScenarioInput,
)
from config import (
    get_ai_model,
    get_ai_provider,
    get_ai_provider_label,
    get_database_path,
    get_model_path,
    get_output_directories,
    has_ai_key,
    has_openai_key,
)
from schemas import PolicyType, ScenarioRequest
from tools import WorkforceTools


FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


app = FastAPI(
    title="Education Workforce Policy Agent API",
    description=(
        "Projection 2027, policy simulation, workforce recommendations and "
        "agent explanations. Analytical PostgreSQL tables are accessed read-only."
    ),
    version="0.1.0",
)

# POC setting so a local HTML/CSS/JavaScript frontend can call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the HTML/CSS/JavaScript application from the FastAPI server.
app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ============================================================
# SESSIONS — in-memory token -> user mapping (resets on restart)
# ============================================================

SESSIONS: dict[str, dict[str, Any]] = {}



# Endpoints that must remain callable even while a session is still flagged as
# first-login, otherwise a forced-password-change user could never actually
# complete the change (or log out).
_FIRST_LOGIN_ALLOWED_PATHS = {"/api/auth/change-password", "/api/auth/logout"}


def require_role(*roles: str):
    """FastAPI dependency factory: returns a dependency that requires a valid
    X-Auth-Token belonging to one of the given roles. Returns the session dict."""

    def _dependency(
        request: Request,
        x_auth_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if not x_auth_token or x_auth_token not in SESSIONS:
            raise HTTPException(status_code=401, detail="Missing or invalid session token")
        session = SESSIONS[x_auth_token]
        if session["role_name"] not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        if session.get("is_first_login") and request.url.path not in _FIRST_LOGIN_ALLOWED_PATHS:
            raise HTTPException(status_code=403, detail="Password change required before continuing")
        return session

    return _dependency


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-SHA256 with a fresh random salt."""
    iterations = 260000
    salt = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}"


def write_audit_log(actor_username: str, actor_role: str, action: str, details: str = "") -> None:
    connection = db.get_connection(read_only=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO audit_log (actor_username, actor_role, action, details) VALUES (%s, %s, %s, %s)",
                [actor_username, actor_role, action, details],
            )
        connection.commit()
    finally:
        connection.close()


def _write_run_log(output: dict[str, Any], session: dict[str, Any], run_type: str) -> None:
    scenario = output["scenario"]
    run_id = output["artifacts"]["run_id"]
    target_scope = f"{scenario.subject}/{scenario.negeri}/{scenario.ppd}"
    connection = db.get_connection(read_only=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO simulation_run_log (run_id, scenario_id, run_timestamp, run_by, run_type, target_scope, notes) "
                "VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s)",
                [run_id, run_id, session["username"], run_type, target_scope, output.get("scenario_source", "")],
            )
        connection.commit()
    finally:
        connection.close()


@lru_cache(maxsize=1)
def get_system() -> tuple[WorkforceTools, Orchestrator]:
    try:
        tools = WorkforceTools(get_database_path(), get_model_path())
    except Exception as error:
        # Fall back to a lightweight mock tools implementation so tests and notebooks
        # can run in environments where native extensions or model files fail to load.
        from tools import MockWorkforceTools

        tools = MockWorkforceTools(get_database_path(), get_model_path())
    return tools, Orchestrator(tools)


def serialize_output(output: dict[str, Any]) -> dict[str, Any]:
    scenario_uses_ai = output["scenario_source"].startswith(
        ("OpenAI Scenario Agent", "Groq Scenario Agent")
    )
    explanation_uses_ai = output["explanation_source"].startswith(
        ("OpenAI Explanation Agent", "Groq Explanation Agent")
    )
    provider = get_ai_provider_label() if scenario_uses_ai or explanation_uses_ai else None
    recommendation_columns = [
        "kod_sekolah",
        "negeri",
        "ppd",
        "subjek",
        "scenario_required_2027",
        "available_2027_assumption",
        "scenario_teacher_gap",
        "scenario_option_gap",
        "change_required",
        "change_option_gap",
        "priority_score",
        "priority_label",
        "recommended_action",
    ]
    return {
        "scenario": output["scenario"].to_dict(),
        "scenario_source": output["scenario_source"],
        "summary": output["summary"],
        "subject_summary": output["subject_summary"].to_dict(orient="records"),
        "policy_impacts": output.get("policy_impacts", []),
        "top_recommendations": output["recommendations"][
            recommendation_columns
        ].to_dict(orient="records"),
        "rules": output["rules"],
        "explanation": output["explanation"],
        "explanation_source": output["explanation_source"],
        "ai_usage": {
            "provider": provider,
            "model": get_ai_model() if provider else None,
            "scenario_interpreted_by_ai": scenario_uses_ai,
            "explanation_generated_by_ai": explanation_uses_ai,
        },
        "artifacts": output["artifacts"],
        "agent_trace": [
            "Orchestrator",
            "Scenario Agent",
            "Simulation Agent",
            "Workforce Recommendation Agent",
            "Explanation Agent",
        ],
    }


@app.get("/", response_class=FileResponse, include_in_schema=False)
def root() -> FileResponse:
    """Serve the BM landing page at the root URL."""
    return FileResponse(FRONTEND_DIR / "landing.html")

@app.get("/en", response_class=FileResponse, include_in_schema=False)
def root_en() -> FileResponse:
    """Serve the English landing page."""
    return FileResponse(FRONTEND_DIR / "landing-en.html")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, stored_hash = password_hash.split("$", 3)
            iterations = int(iterations)
        except ValueError:
            return False

        test_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(test_hash, stored_hash)

    return hmac.compare_digest(password, password_hash)


@app.post("/api/auth/login")
def login(payload: LoginInput) -> dict[str, Any]:
    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username, email, password_hash, role_name, is_active, is_first_login, "
                "COALESCE(can_view_audit_log, FALSE) "
                "FROM users WHERE username = %s LIMIT 1",
                [payload.username],
            )
            row = cursor.fetchone()
    finally:
        connection.close()

    if not row:
        write_audit_log(payload.username, "unknown", "login_failed", "no such user")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    username, email, password_hash, role_name, is_active, is_first_login, can_view_audit_log = row
    if not is_active:
        write_audit_log(username, role_name, "login_failed", "inactive account")
        raise HTTPException(status_code=403, detail="User account is inactive")
    if not verify_password(payload.password, password_hash):
        write_audit_log(username, role_name, "login_failed", "bad password")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    write_connection = db.get_connection(read_only=False)
    try:
        with write_connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE username = %s",
                [username],
            )
        write_connection.commit()
    finally:
        write_connection.close()

    token = secrets.token_hex(16)
    SESSIONS[token] = {
        "username": username,
        "role_name": role_name,
        "can_view_audit_log": bool(can_view_audit_log),
        "is_first_login": bool(is_first_login),
    }
    write_audit_log(username, role_name, "login_success", "")

    return {
        "username": username,
        "email": email,
        "role_name": role_name,
        "is_first_login": bool(is_first_login),
        "can_view_audit_log": bool(can_view_audit_log),
        "token": token,
    }


@app.post("/api/auth/logout")
def logout(x_auth_token: str | None = Header(default=None)) -> dict[str, Any]:
    if x_auth_token and x_auth_token in SESSIONS:
        session = SESSIONS.pop(x_auth_token)
        write_audit_log(session["username"], session["role_name"], "logout", "")
    return {"ok": True}


@app.post("/api/admin/create-user")
def create_user(
    payload: CreateUserInput,
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    """Create a new user account. Superadmin only. Password is always
    auto-generated and emailed — never admin-typed, never returned here."""
    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s LIMIT 1",
                [payload.username],
            )
            existing = cursor.fetchone()
    finally:
        connection.close()

    if existing:
        raise HTTPException(status_code=400, detail=f"Username '{payload.username}' already exists")

    temp_password = email_utils.generate_temp_password()
    password_hash = hash_password(temp_password)

    connection = db.get_connection(read_only=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role_name, is_active, is_first_login, can_view_audit_log) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                [payload.username, payload.email, password_hash, payload.role_name, True, True, payload.can_view_audit_log],
            )
            new_id = cursor.fetchone()[0]
        connection.commit()
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(error)}")
    finally:
        connection.close()

    email_sent = email_utils.send_temp_password_email(
        payload.email, payload.username, temp_password, payload.lang
    )

    write_audit_log(
        session["username"], session["role_name"], "user_created",
        f"created '{payload.username}' with role '{payload.role_name}'",
    )

    return {
        "id": new_id,
        "username": payload.username,
        "email": payload.email,
        "role_name": payload.role_name,
        "is_first_login": True,
        "email_sent": email_sent,
        "message": f"User '{payload.username}' created. Temporary password emailed to {payload.email}.",
    }


@app.get("/api/admin/users")
def list_users(
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email, role_name, is_active, created_at, last_login_at "
                "FROM users ORDER BY id"
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    return {
        "users": [
            {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "role_name": row[3],
                "is_active": bool(row[4]),
                "created_at": str(row[5]) if row[5] is not None else None,
                "last_login_at": str(row[6]) if row[6] is not None else None,
            }
            for row in rows
        ]
    }


@app.post("/api/admin/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username, email FROM users WHERE id = %s LIMIT 1", [user_id]
            )
            row = cursor.fetchone()
    finally:
        connection.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    username, email = row

    temp_password = email_utils.generate_temp_password()
    password_hash = hash_password(temp_password)

    write_connection = db.get_connection(read_only=False)
    try:
        with write_connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s, is_first_login = TRUE WHERE id = %s",
                [password_hash, user_id],
            )
        write_connection.commit()
    finally:
        write_connection.close()

    # The `users` table has no stored per-user language preference column, and
    # adding one requires explicit approval (see CLAUDE.md "Things Not to Touch").
    # Defaulting to "bm" here is an intentional choice, not an oversight.
    email_sent = email_utils.send_temp_password_email(email, username, temp_password, lang="bm")
    write_audit_log(
        session["username"], session["role_name"], "password_reset",
        f"reset password for '{username}'",
    )

    return {
        "id": user_id,
        "email_sent": email_sent,
        "message": f"Password reset for '{username}'. New temporary password emailed to {email}.",
    }


@app.post("/api/admin/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username, role_name, is_active FROM users WHERE id = %s LIMIT 1", [user_id]
            )
            row = cursor.fetchone()
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE role_name = 'superadmin' AND is_active = TRUE"
            )
            active_superadmins = cursor.fetchone()[0]
    finally:
        connection.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    username, role_name, is_active = row

    if username == session["username"]:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    if role_name == "superadmin" and is_active and active_superadmins <= 1:
        raise HTTPException(status_code=400, detail="Cannot deactivate the last remaining active superadmin")

    write_connection = db.get_connection(read_only=False)
    try:
        with write_connection.cursor() as cursor:
            cursor.execute("UPDATE users SET is_active = FALSE WHERE id = %s", [user_id])
        write_connection.commit()
    finally:
        write_connection.close()

    write_audit_log(
        session["username"], session["role_name"], "user_deactivated",
        f"deactivated '{username}'",
    )
    return {"id": user_id, "is_active": False, "message": f"User '{username}' deactivated."}


@app.post("/api/auth/change-password")
def change_password(
    payload: ChangePasswordInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
    x_auth_token: str | None = Header(default=None),
) -> dict[str, Any]:
    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM users WHERE username = %s LIMIT 1",
                [session["username"]],
            )
            row = cursor.fetchone()
    finally:
        connection.close()

    if not row or not verify_password(payload.current_password, row[0]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    password_hash = hash_password(payload.new_password)

    write_connection = db.get_connection(read_only=False)
    try:
        with write_connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s, is_first_login = FALSE, password_changed_at = CURRENT_TIMESTAMP "
                "WHERE username = %s",
                [password_hash, session["username"]],
            )
        write_connection.commit()
    finally:
        write_connection.close()

    if x_auth_token and x_auth_token in SESSIONS:
        SESSIONS[x_auth_token]["is_first_login"] = False

    write_audit_log(session["username"], session["role_name"], "password_changed", "")
    return {"ok": True}


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        tools, _ = get_system()
        status = tools.health_check()
        status["openai_enabled"] = has_openai_key()
        status["ai_enabled"] = has_ai_key()
        status["ai_provider"] = get_ai_provider_label() if has_ai_key() else "Local"
        status["ai_model"] = get_ai_model()
        status["source_database_mutable"] = False
        return status
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/filters/{field}")
def filters(
    field: Literal["negeri", "ppd", "kod_sekolah", "kodtingkatantahun"],
    negeri: str = Query(default="SEMUA"),
    ppd: str = Query(default="SEMUA"),
) -> dict[str, Any]:
    try:
        tools, _ = get_system()
        return {
            "field": field,
            "values": tools.get_filter_options(
                field,
                negeri=negeri.upper(),
                ppd=ppd.upper(),
            ),
        }
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/forecast/2027")
def forecast_2027(
    payload: ForecastInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin")),
) -> dict[str, Any]:
    """Return the ML baseline projection without changing policy parameters."""
    try:
        _, orchestrator = get_system()
        scenario = ScenarioRequest(
            target_year=2027,
            subject=payload.subject,
            negeri=payload.negeri,
            ppd=payload.ppd,
            kod_sekolah=payload.kod_sekolah,
            policy_type=PolicyType.BASELINE,
        )
        output = orchestrator.execute(scenario)
        response = serialize_output(output)
        response["forecast_only"] = True
        return response
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/simulate")
def simulate(
    payload: ScenarioInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
) -> dict[str, Any]:
    try:
        _, orchestrator = get_system()
        output = orchestrator.execute(payload.to_scenario(), lang=payload.lang, run_by=session["username"])
        _write_run_log(output, session, run_type="simulate")
        return serialize_output(output)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/agent/run")
def run_agent(
    payload: AgentQuestionInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
) -> dict[str, Any]:
    try:
        _, orchestrator = get_system()
        output = orchestrator.execute_from_text(payload.question, lang=payload.lang, run_by=session["username"])
        _write_run_log(output, session, run_type="agent")
        return serialize_output(output)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/runs/{run_id}/detail.csv")
def download_run(
    run_id: str,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin")),
):
    if not run_id.startswith("RUN_") or not run_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid run_id")
    for output_root in get_output_directories():
        output_root = output_root.resolve()
        file_path = (output_root / f"{run_id}_detail.csv").resolve()
        if output_root in file_path.parents and file_path.exists():
            return FileResponse(
                file_path,
                media_type="text/csv",
                filename=file_path.name,
            )
    raise HTTPException(status_code=404, detail="Run detail not found")


@app.get("/api/audit-log")
def get_audit_log(
    session: dict[str, Any] = Depends(require_role("superadmin", "admin")),
) -> dict[str, Any]:
    if session["role_name"] == "admin" and not session.get("can_view_audit_log"):
        raise HTTPException(status_code=403, detail="Audit log is not enabled for this account")

    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT occurred_at, actor_username, actor_role, action, details FROM audit_log"
            )
            audit_rows = cursor.fetchall()
            cursor.execute(
                "SELECT run_timestamp, run_by, run_type, target_scope, notes FROM simulation_run_log"
            )
            run_rows = cursor.fetchall()
    finally:
        connection.close()

    entries = [
        {"occurred_at": str(r[0]), "actor": r[1], "role": r[2], "action": r[3], "details": r[4] or ""}
        for r in audit_rows
    ] + [
        {
            "occurred_at": str(r[0]),
            "actor": r[1] or "unknown",
            "role": "",
            "action": f"simulation_run:{r[2] or 'simulate'}",
            "details": f"scope={r[3] or ''} {r[4] or ''}".strip(),
        }
        for r in run_rows
    ]
    entries.sort(key=lambda e: e["occurred_at"], reverse=True)
    return {"entries": entries}


@app.get("/api/runs/{run_id}/summary.csv")
def download_run_summary(
    run_id: str,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
):
    if not run_id.startswith("RUN_") or not run_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid run_id")
    for output_root in get_output_directories():
        output_root = output_root.resolve()
        file_path = (output_root / f"{run_id}_summary.csv").resolve()
        if output_root in file_path.parents and file_path.exists():
            return FileResponse(
                file_path,
                media_type="text/csv",
                filename=file_path.name,
            )
    raise HTTPException(status_code=404, detail="Run summary not found")


def _read_run_scenario(run_id: str) -> dict[str, Any] | None:
    """Reads the archived `scenario` dict from a run's summary.json, or None
    if the run_id is malformed or the file can't be found/parsed."""
    if not run_id.startswith("RUN_") or not run_id.replace("_", "").isalnum():
        return None
    for output_root in get_output_directories():
        output_root = output_root.resolve()
        file_path = (output_root / f"{run_id}_summary.json").resolve()
        if output_root in file_path.parents and file_path.exists():
            try:
                return json.loads(file_path.read_text(encoding="utf-8")).get("scenario")
            except (OSError, ValueError):
                return None
    return None


@app.post("/api/runs/save")
def save_run(
    payload: SaveRunInput,
    session: dict[str, Any] = Depends(require_role("user")),
) -> dict[str, Any]:
    if not payload.run_id.startswith("RUN_") or not payload.run_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid run_id")

    connection = db.get_connection(read_only=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_timestamp FROM simulation_run_log WHERE run_id = %s AND run_by = %s",
                [payload.run_id, session["username"]],
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Run not found")
            run_timestamp = row[0]

            run_name = payload.run_name.strip()
            if not run_name:
                run_name = f"Simulation - {run_timestamp:%Y-%m-%d %H:%M}"

            cursor.execute(
                "UPDATE simulation_run_log SET run_name = %s, is_saved = TRUE "
                "WHERE run_id = %s AND run_by = %s",
                [run_name, payload.run_id, session["username"]],
            )
        connection.commit()
    finally:
        connection.close()

    return {"run_id": payload.run_id, "run_name": run_name}


@app.get("/api/my-runs")
def get_my_runs(
    session: dict[str, Any] = Depends(require_role("user")),
) -> dict[str, Any]:
    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_id, run_timestamp FROM simulation_run_log "
                "WHERE run_by = %s AND run_type IN ('simulate', 'agent') "
                "ORDER BY run_timestamp DESC LIMIT 20",
                [session["username"]],
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    runs: list[dict[str, Any]] = []
    for run_id, run_timestamp in rows:
        scenario = _read_run_scenario(run_id)
        if scenario is None:
            continue
        runs.append({
            "run_id": run_id,
            "run_timestamp": str(run_timestamp),
            "scenario": scenario,
        })
    return {"runs": runs}
