"""Single source of truth for environment variables.

Loads .env (if present) and exposes one `settings` object. All env reads in the
codebase must go through this module — never call os.getenv directly elsewhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is a dev dependency; keep stdlib fallback

    def load_dotenv(_path: str | Path | None = None) -> bool:  # type: ignore[no-redef]
        return True


def _load() -> None:
    # Read .env from the repo root regardless of CWD.
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")


@dataclass(frozen=True)
class Settings:
    GROQ_API_KEY: str
    GROQ_MODEL: str
    GEMINI_API_KEY: str
    GEMINI_BASE_URL: str
    GEMINI_MODEL: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load()
    return Settings(
        GROQ_API_KEY=os.getenv("GROQ_API_KEY", ""),
        GROQ_MODEL=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
        GEMINI_BASE_URL=os.getenv(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
        ),
        GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )


settings = get_settings()
