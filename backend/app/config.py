import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw else default


def _database_url() -> str:
    """Resolve relative SQLite paths against backend/, not the current directory.

    Otherwise running the seed and the server from different folders would
    silently use two different database files.
    """
    url = os.getenv("DATABASE_URL", "sqlite:///./growth_os.db")
    prefix = "sqlite:///"
    path = url.removeprefix(prefix)
    if url.startswith(prefix) and path != ":memory:" and not Path(path).is_absolute():
        return f"{prefix}{(BACKEND_DIR / path).resolve().as_posix()}"
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=_database_url)
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-insecure-jwt-secret-change-me")
    jwt_expire_minutes: int = _int("JWT_EXPIRE_MINUTES", 60 * 12)
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    ai_timeout_seconds: int = _int("AI_TIMEOUT_SECONDS", 60)
    # Anthropic reasoning effort: low keeps interactive generation fast.
    ai_effort: str = os.getenv("AI_EFFORT", "low")
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))
    )


settings = Settings()
