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
    required: bool = True,
) -> Path:
    configured = os.getenv(env_name, "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.exists() and required:
            raise FileNotFoundError(f"{description} configured in {env_name} not found: {path}")
        return path

    matches = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in suffixes
    ) if folder.exists() else []
    if len(matches) == 1:
        return matches[0].resolve()
    if not matches:
        if not required:
            return folder / f"{description.lower().replace(' ', '-')}-not-found"
        raise FileNotFoundError(
            f"No {description} found in {folder}. Copy the file there or set {env_name} in .env."
        )
    raise RuntimeError(
        f"Multiple {description} files found in {folder}. Keep one file or set {env_name} in .env."
    )


def get_database_path(required: bool = True) -> Path:
    return _resolve_input_file(
        "DATA_FILE",
        DATA_DIR,
        (".duckdb",),
        "DuckDB database",
        required=required,
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


def get_deepseek_model() -> str:
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()


def has_deepseek_key() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY", "").strip())


_PROVIDER_MODELS = {
    "groq": get_groq_model,
    "deepseek": get_deepseek_model,
    "openai": get_openai_model,
}
_PROVIDER_KEYS = {
    "groq": has_groq_key,
    "deepseek": has_deepseek_key,
    "openai": has_openai_key,
}
_PROVIDER_LABELS = {"groq": "Groq", "deepseek": "DeepSeek", "openai": "OpenAI", "local": "Local"}


def get_ai_provider_chain() -> list[str]:
    """Ordered providers to try, filtered to those with a key configured.

    AI_PROVIDER can pin a single provider (or "local" to disable AI entirely).
    Left unset, the default fallback order is groq -> deepseek -> openai, so a
    rate-limited/exhausted Groq key automatically falls through to DeepSeek,
    and callers still fall back to the deterministic local parser if every
    configured provider fails.
    """
    configured = os.getenv("AI_PROVIDER", "").strip().lower()
    if configured and configured not in {"groq", "openai", "deepseek", "local"}:
        raise ValueError("AI_PROVIDER must be groq, openai, deepseek or local.")
    if configured == "local":
        return []
    chain = [configured] if configured in _PROVIDER_KEYS else ["groq", "deepseek", "openai"]
    return [provider for provider in chain if _PROVIDER_KEYS[provider]()]


def get_ai_provider() -> str:
    """Return the first provider that would be tried, or "local" if none are configured."""
    chain = get_ai_provider_chain()
    return chain[0] if chain else "local"


def get_ai_model(provider: str | None = None) -> str | None:
    provider = provider if provider is not None else get_ai_provider()
    if provider in _PROVIDER_MODELS:
        return _PROVIDER_MODELS[provider]()
    return None


def get_ai_provider_label(provider: str | None = None) -> str:
    return _PROVIDER_LABELS[provider if provider is not None else get_ai_provider()]


def has_ai_key() -> bool:
    return bool(get_ai_provider_chain())


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


def get_postgres_schema() -> str:
    return os.getenv("POSTGRES_SCHEMA", "g5_p1").strip() or "g5_p1"


def get_postgres_dsn() -> str:
    return (
        f"host={get_postgres_host()} port={get_postgres_port()} "
        f"dbname={get_postgres_db()} user={get_postgres_user()} "
        f"password={get_postgres_password()} "
        f"options='-c search_path={get_postgres_schema()},public'"
    )
