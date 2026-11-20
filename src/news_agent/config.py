import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class AppConfig:
    sources: list[dict[str, Any]]
    database: Path
    max_age_hours: int = 48


def load_config(path: Path) -> AppConfig:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or not isinstance(data.get("sources", []), list):
        raise ValueError("Config must be a mapping with a 'sources' list")
    return AppConfig(
        sources=data.get("sources", []),
        database=Path(os.getenv("NEWS_AGENT_DB", "data/news-agent.sqlite3")),
        max_age_hours=int(data.get("max_age_hours", 48)),
    )

