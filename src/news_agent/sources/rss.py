from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from news_agent.models import Article


def _date(entry: object) -> datetime | None:
    struct_time = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if struct_time:
        return datetime(*struct_time[:6], tzinfo=timezone.utc)
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if raw:
        try:
            parsed = parsedate_to_datetime(raw)
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        except (TypeError, ValueError, OverflowError):
            return None
    return None


class RSSAdapter:
    def __init__(self, config: dict):
        self.config = config

    def fetch(self) -> list[Article]:
        feed = feedparser.parse(self.config["url"])
        if feed.bozo and not feed.entries:
            raise ValueError(f"Could not parse feed: {self.config['url']}: {feed.bozo_exception}")
        articles = []
        for entry in feed.entries[: int(self.config.get("max_items", 20))]:
            url = entry.get("link", self.config["url"])
            key = entry.get("id") or url
            articles.append(Article(
                id=f"{self.config['id']}:{key}",
                source_id=self.config["id"],
                source_name=self.config.get("name", self.config["id"]),
                title=entry.get("title", "Untitled"),
                url=url,
                text=entry.get("summary", "") or entry.get("description", ""),
                published_at=_date(entry),
            ))
        return articles

