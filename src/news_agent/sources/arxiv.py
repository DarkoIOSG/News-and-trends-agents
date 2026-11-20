import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from news_agent.models import Article


class ArxivAdapter:
    """Fetch recent papers from selected arXiv categories via its Atom API."""

    endpoint = "https://export.arxiv.org/api/query"

    def __init__(self, config: dict):
        self.config = config

    def fetch(self) -> list[Article]:
        categories = self.config.get("categories", ["cs.LG", "cs.CL", "cs.DC"])
        days = max(int(self.config.get("window_days", 7)), 1)
        max_results = min(max(int(self.config.get("max_results_per_category", 100)), 1), 2000)
        per_category = max(int(self.config.get("max_items_per_category", 5)), 1)
        keywords = [str(word).casefold() for word in self.config.get("keywords", []) if str(word).strip()]
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=days)).strftime("%Y%m%d%H%M")
        end = now.strftime("%Y%m%d%H%M")

        articles: list[Article] = []
        with httpx.Client(timeout=40, headers={"User-Agent": "NewsTrendsAgent/0.1 (personal research digest)"}) as client:
            for category_index, category in enumerate(categories):
                if category_index:
                    # arXiv recommends spacing repeated API requests by three seconds.
                    time.sleep(float(self.config.get("request_delay_seconds", 3)))
                params = {
                    "search_query": f"cat:{category} AND submittedDate:[{start} TO {end}]",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }
                response = client.get(self.endpoint, params=params)
                response.raise_for_status()
                feed = feedparser.parse(response.text)
                category_items = 0
                for entry in feed.entries:
                    title = re.sub(r"\s+", " ", entry.get("title", "")).strip()
                    abstract = re.sub(r"\s+", " ", entry.get("summary", "")).strip()
                    searchable = f"{title}\n{abstract}".casefold()
                    if not title or (keywords and not any(word in searchable for word in keywords)):
                        continue
                    url = entry.get("link", "")
                    arxiv_id = _arxiv_id(entry.get("id", "") or url)
                    if not arxiv_id:
                        continue
                    published_at = _parse_datetime(entry.get("published"))
                    articles.append(Article(
                        id=f"{self.config['id']}:{arxiv_id}",
                        source_id=self.config["id"],
                        source_name=f"{self.config.get('name', 'arXiv')} · {category}",
                        title=title,
                        url=f"https://arxiv.org/abs/{arxiv_id}",
                        text=abstract,
                        published_at=published_at,
                        metadata={
                            "arxiv_id": arxiv_id,
                            "categories": [tag.get("term") for tag in entry.get("tags", []) if tag.get("term")],
                            "authors": [author.get("name") for author in entry.get("authors", [])],
                        },
                    ))
                    category_items += 1
                    if category_items >= per_category:
                        break
        return articles


def _arxiv_id(value: str) -> str:
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", value)
    return match.group(1) if match else ""


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed

