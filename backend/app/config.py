"""Runtime configuration, read once from the environment (and backend/.env)."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in _env(name, default).split(",") if item.strip()]


@dataclass
class Settings:
    # Claude
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-opus-5-5"))
    anthropic_effort: str = field(default_factory=lambda: _env("ANTHROPIC_EFFORT", "medium"))
    # "default" enables server-side refusal fallbacks; empty disables them.
    anthropic_fallbacks: str = field(default_factory=lambda: _env("ANTHROPIC_FALLBACKS", "default"))

    # Data providers
    finnhub_api_key: str = field(default_factory=lambda: _env("FINNHUB_API_KEY"))
    earningscall_api_key: str = field(default_factory=lambda: _env("EARNINGSCALL_API_KEY"))
    # SEC asks automated clients to identify themselves with a contact address.
    sec_user_agent: str = field(
        default_factory=lambda: _env("SEC_USER_AGENT", "StockAnalyzer research-app admin@example.com")
    )

    # Retrieval
    # auto | voyage | local | none  (auto = voyage if a key is set, else local if installed)
    embeddings: str = field(default_factory=lambda: _env("EMBEDDINGS", "auto").lower())
    voyage_api_key: str = field(default_factory=lambda: _env("VOYAGE_API_KEY"))
    voyage_model: str = field(default_factory=lambda: _env("VOYAGE_MODEL", "voyage-finance-2"))
    local_embedding_model: str = field(default_factory=lambda: _env("LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"))

    # App
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(BACKEND_DIR / ".data"))))
    cors_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
        )
    )
    cache_enabled: bool = field(default_factory=lambda: _env("CACHE_ENABLED", "1") not in ("0", "false"))
    report_ttl_seconds: int = field(default_factory=lambda: _env_int("REPORT_TTL_SECONDS", 6 * 3600))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO").upper())

    @property
    def db_path(self) -> Path:
        return self.data_dir / "stockanalyzer.sqlite3"


settings = Settings()
