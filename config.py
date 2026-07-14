"""Project configuration and safe input-file discovery."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
_configured_output_dir = os.getenv("OUTPUT_DIR", "").strip()
OUTPUT_DIR = (
    Path(_configured_output_dir).expanduser().resolve()
    if _configured_output_dir
    else (PROJECT_ROOT / "outputs").resolve()
)
FALLBACK_OUTPUT_DIR = (
    Path(os.getenv("TEMP", str(Path.home())))
    / "EducationWorkforceAgent"
    / "outputs"
).resolve()

def get_output_directories() -> list[Path]:
    """Preferred and fallback writable locations for generated run files."""
    directories: list[Path] = []
    for directory in (OUTPUT_DIR, FALLBACK_OUTPUT_DIR):
        if directory not in directories:
            directories.append(directory)
    return directories


def _resolve_input_file(
    env_name: str,
    folder: Path,
    suffixes: tuple[str, ...],
    description: str,
) -> Path:
    configured = os.getenv(env_name, "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"{description} configured in {env_name} not found: {path}")
        return path

    matches = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in suffixes
    ) if folder.exists() else []
    if len(matches) == 1:
        return matches[0].resolve()
    if not matches:
        raise FileNotFoundError(
            f"No {description} found in {folder}. Copy the file there or set {env_name} in .env."
        )
    raise RuntimeError(
        f"Multiple {description} files found in {folder}. Keep one file or set {env_name} in .env."
    )


def get_database_path() -> Path:
    return _resolve_input_file(
        "DATA_FILE",
        DATA_DIR,
        (".duckdb",),
        "DuckDB database",
    )


def get_model_path() -> Path:
    return _resolve_input_file(
        "MODEL_FILE",
        MODEL_DIR,
        (".pk1", ".pkl", ".joblib"),
        "Random Forest model",
    )


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()


def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def get_groq_model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()


def has_groq_key() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def get_ai_provider() -> str:
    """Return groq, openai or local without exposing any credential."""
    configured = os.getenv("AI_PROVIDER", "").strip().lower()
    if configured and configured not in {"groq", "openai", "local"}:
        raise ValueError("AI_PROVIDER must be groq, openai or local.")
    if configured == "groq":
        return "groq" if has_groq_key() else "local"
    if configured == "openai":
        return "openai" if has_openai_key() else "local"
    if configured == "local":
        return "local"
    if has_groq_key():
        return "groq"
    if has_openai_key():
        return "openai"
    return "local"


def get_ai_model() -> str | None:
    provider = get_ai_provider()
    if provider == "groq":
        return get_groq_model()
    if provider == "openai":
        return get_openai_model()
    return None


def get_ai_provider_label() -> str:
    return {"groq": "Groq", "openai": "OpenAI", "local": "Local"}[
        get_ai_provider()
    ]


def has_ai_key() -> bool:
    return get_ai_provider() in {"groq", "openai"}


def get_smtp_host() -> str:
    return os.getenv("SMTP_HOST", "").strip()


def get_smtp_port() -> int:
    return int(os.getenv("SMTP_PORT", "587").strip() or "587")


def get_smtp_username() -> str:
    return os.getenv("SMTP_USERNAME", "").strip()


def get_smtp_password() -> str:
    return os.getenv("SMTP_PASSWORD", "").strip()


def get_smtp_from_address() -> str:
    return os.getenv("SMTP_FROM_ADDRESS", "").strip()


def get_postgres_host() -> str:
    return os.getenv("POSTGRES_HOST", "localhost").strip()


def get_postgres_port() -> int:
    return int(os.getenv("POSTGRES_PORT", "5432").strip() or "5432")


def get_postgres_db() -> str:
    return os.getenv("POSTGRES_DB", "workforce_policy_agent").strip()


def get_postgres_user() -> str:
    return os.getenv("POSTGRES_USER", "postgres").strip()


def get_postgres_password() -> str:
    return os.getenv("POSTGRES_PASSWORD", "").strip()


def get_postgres_dsn() -> str:
    return (
        f"host={get_postgres_host()} port={get_postgres_port()} "
        f"dbname={get_postgres_db()} user={get_postgres_user()} "
        f"password={get_postgres_password()}"
    )
