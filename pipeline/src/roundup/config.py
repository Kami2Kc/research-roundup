"""Paths, environment settings and the source configuration."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

from roundup.models import Source

# pipeline/src/roundup/config.py -> repository root
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCES_PATH = REPO_ROOT / "config" / "sources.yaml"
DB_PATH = REPO_ROOT / "data" / "roundup.db"
WEB_PUBLIC = REPO_ROOT / "web" / "public"


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_api_key: str | None
    llm_screen_model: str | None
    llm_editor_model: str | None
    contact_email: str | None


def load_settings() -> Settings:
    """Read settings from the environment, loading a local .env file if there is one."""
    load_dotenv(REPO_ROOT / ".env")
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "anthropic"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_screen_model=os.getenv("LLM_SCREEN_MODEL"),
        llm_editor_model=os.getenv("LLM_EDITOR_MODEL"),
        contact_email=os.getenv("CONTACT_EMAIL"),
    )


def load_sources(path: Path = SOURCES_PATH) -> list[Source]:
    """Load and validate every source in the YAML config."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    sources = [Source(**entry) for entry in raw["sources"]]

    seen: set[str] = set()
    for source in sources:
        if source.id in seen:
            raise ValueError(f"Duplicate source id in {path.name}: {source.id}")
        seen.add(source.id)
    return sources
