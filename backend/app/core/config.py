"""Security & Config Isolation point.

Every environment-dependent value (DB URL, AI provider, egress policy, API keys,
local LLM endpoint) is read here and nowhere else. Services receive a Settings
object; they never touch os.environ directly. This is what lets the same code run
on-premise (LOCAL_LLM, egress_allowed=false) or with an external provider.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
load_dotenv(BASE_DIR / ".env")


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "ReplaceFlow API"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./replaceflow.db"
    ai_provider: str = "MOCK"  # MOCK | LOCAL_LLM | AX_PLATFORM | OPENAI
    egress_allowed: bool = False
    openai_api_key: str = ""
    local_llm_url: str = ""
    background_advance: bool = False
    prompts_path: Path = BASE_DIR.parent / "docs" / "05_ai_ready" / "prompts.md"
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173"])
    seed_on_startup: bool = True

    def validate_egress(self) -> None:
        """Refuse to start an external provider when egress is disabled."""
        if self.ai_provider in {"OPENAI", "AX_PLATFORM"} and not self.egress_allowed:
            raise RuntimeError(
                f"AI_PROVIDER={self.ai_provider} requires EGRESS_ALLOWED=true (on-premise policy)"
            )


@lru_cache
def get_settings() -> Settings:
    prompts = os.getenv("PROMPTS_PATH")
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./replaceflow.db"),
        ai_provider=os.getenv("AI_PROVIDER", "MOCK").upper(),
        egress_allowed=_bool(os.getenv("EGRESS_ALLOWED"), False),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        local_llm_url=os.getenv("LOCAL_LLM_URL", ""),
        background_advance=_bool(os.getenv("BACKGROUND_ADVANCE"), False),
        prompts_path=(BASE_DIR / prompts).resolve() if prompts else Settings.prompts_path,
        cors_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
        seed_on_startup=_bool(os.getenv("SEED_ON_STARTUP"), True),
    )
