from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from news_agent.models import Article


class HuggingFacePapersAdapter:
    """Fetch trending Daily Papers from the public Hugging Face Hub API."""

    endpoint = "https://huggingface.co/api/daily_papers"

    def __init__(self, config: dict):
        self.config = config

    def fetch(self) -> list[Article]:
        period = self.config.get("period", "week")
        sort = self.config.get("sort", "trending")
        if period not in {"day", "week", "month"}:
            raise ValueError("Hugging Face papers period must be day, week, or month")
        if sort not in {"publishedAt", "trending"}:
            raise ValueError("Hugging Face papers sort must be publishedAt or trending")

        now = datetime.now(timezone.utc)
        params: dict[str, Any] = {
            "limit": min(max(int(self.config.get("api_limit", 100)), 1), 100),
            "sort": sort,
        }
        if period == "day":
            params["date"] = now.date().isoformat()
        elif period == "week":
            params["week"] = now.strftime("%G-W%V")
        else:
            params["month"] = now.strftime("%Y-%m")

        max_pages = max(int(self.config.get("max_pages", 3)), 1)
        api_limit = params["limit"]
        keywords = [str(word).casefold() for word in self.config.get("keywords", []) if str(word).strip()]
        articles: list[Article] = []
        seen: set[str] = set()
        with httpx.Client(timeout=20, headers={"User-Agent": "NewsTrendsAgent/0.1"}) as client:
            for page in range(max_pages):
                response = client.get(self.endpoint, params={**params, "p": page})
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list) or not payload:
                    break
                for row in payload:
                    article = self._article(row)
                    if article is None or article.id in seen:
                        continue
                    seen.add(article.id)
                    searchable = f"{article.title}\n{article.text}".casefold()
                    if keywords and not any(keyword in searchable for keyword in keywords):
                        continue
                    articles.append(article)
                    if len(articles) >= int(self.config.get("max_items", 10)):
                        return articles
                if len(payload) < api_limit:
                    break
        return articles

    def _article(self, row: dict[str, Any]) -> Article | None:
        if not isinstance(row, dict):
            return None
        paper = row.get("paper") or row
        if not isinstance(paper, dict):
            return None
        paper_id = str(paper.get("id") or paper.get("paperId") or "").strip()
        title = str(paper.get("title") or "").strip()
        if not paper_id or not title:
            return None

        abstract = str(paper.get("summary") or paper.get("abstract") or "").strip()
        ai_summary = str(paper.get("ai_summary") or paper.get("aiSummary") or "").strip()
        text = abstract or ai_summary
        paper_published_at = _parse_datetime(
            paper.get("publishedAt") or paper.get("published_at")
        )
        listed_at = _parse_datetime(
            paper.get("submittedOnDailyAt") or paper.get("submitted_on_daily_at")
            or row.get("submittedAt") or row.get("submitted_at")
        )
        upvotes = paper.get("upvotes", row.get("upvotes", 0))
        comments = paper.get("comments", row.get("comments", 0))
        source_name = self.config.get("name", "Hugging Face Daily Papers")
        if upvotes is not None:
            source_name = f"{source_name} · {upvotes} upvotes"

        return Article(
            id=f"{self.config['id']}:{paper_id}",
            source_id=self.config["id"],
            source_name=source_name,
            title=title,
            url=f"https://huggingface.co/papers/{paper_id}",
            text=text,
            # HF trending rankings can feature older papers that are newly popular.
            # Keep dates as metadata instead of letting the generic age filter drop them.
            published_at=None,
            metadata={
                "paper_id": paper_id,
                "upvotes": upvotes,
                "comments": comments,
                "paper_published_at": paper_published_at.isoformat() if paper_published_at else None,
                "hf_daily_listed_at": listed_at.isoformat() if listed_at else None,
                "github_repo": paper.get("githubRepo") or paper.get("github_repo"),
                "project_page": paper.get("projectPage") or paper.get("project_page"),
            },
        )


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value)
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(raw)
            except (TypeError, ValueError, OverflowError):
                return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed

