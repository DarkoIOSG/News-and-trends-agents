from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Article:
    id: str
    source_id: str
    source_name: str
    title: str
    url: str
    text: str = ""
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content(self) -> str:
        return self.text.strip() or self.title.strip()


@dataclass(slots=True)
class Summary:
    article: Article
    summary: str
    why_it_matters: str = ""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

