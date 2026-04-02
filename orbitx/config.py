from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    max_concurrency: int
    max_retries: int
    use_mock_llm: bool


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        max_concurrency=max(1, int(os.getenv("MAX_CONCURRENCY", "4"))),
        max_retries=max(1, int(os.getenv("MAX_RETRIES", "2"))),
        use_mock_llm=os.getenv("USE_MOCK_LLM", "false").strip().lower() == "true",
    )


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
