import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from news_agent.models import Article


class AlphaXivAdapter:
    """Fetch alphaXiv's public hot feed and recent public discussion comments."""

    base_url = "https://api.alphaxiv.org"

    def __init__(self, config: dict):
        self.config = config

    def fetch(self) -> list[Article]:
        sort = self.config.get("sort", "Hot")
        if sort not in {"Hot", "Comments", "Views", "Likes", "Recent"}:
            raise ValueError("Unsupported alphaXiv sort; use Hot, Comments, Views, Likes, or Recent")
        interval = self.config.get("interval", "7 Days")
        if interval not in {"3 Days", "7 Days", "30 Days", "90 Days", "All time"}:
            raise ValueError("Unsupported alphaXiv interval")
        page_size = min(max(int(self.config.get("page_size", 100)), 1), 100)
        max_pages = max(int(self.config.get("max_pages", 2)), 1)
        max_items = max(int(self.config.get("max_items", 10)), 1)
        keywords = [str(word).casefold() for word in self.config.get("keywords", []) if str(word).strip()]
        articles: list[Article] = []
        seen: set[str] = set()

        with httpx.Client(timeout=25, headers={"User-Agent": "NewsTrendsAgent/0.1"}) as client:
            for page in range(1, max_pages + 1):
                response = client.get(
                    f"{self.base_url}/papers/v3/feed",
                    params={
                        "sort": sort,
                        "interval": interval,
                        "pageNum": str(page),
                        "pageSize": str(page_size),
                    },
                )
                response.raise_for_status()
                payload = response.json()
                papers = payload.get("papers", []) if isinstance(payload, dict) else []
                if not papers:
                    break
                for paper in papers:
                    article = self._article(paper)
                    if article is None or article.id in seen:
                        continue
                    seen.add(article.id)
                    searchable = f"{article.title}\n{article.text}".casefold()
                    if keywords and not any(keyword in searchable for keyword in keywords):
                        continue
                    comments = self._comments(client, article.metadata["paper_group_id"])
                    self._attach_discussion(article, comments)
                    articles.append(article)
                    if len(articles) >= max_items:
                        return articles
                if len(papers) < page_size:
                    break
        return articles

    def _article(self, paper: dict[str, Any]) -> Article | None:
        if not isinstance(paper, dict):
            return None
        paper_group_id = str(paper.get("paper_group_id") or paper.get("id") or "").strip()
        title = str(paper.get("title") or "").strip()
        if not paper_group_id or not title:
            return None
        canonical_id = str(paper.get("canonical_id") or paper.get("universal_paper_id") or "").strip()
        if not canonical_id:
            canonical_id = paper_group_id
        canonical_id = canonical_id.removeprefix("arxiv:")
        abstract = str(paper.get("abstract") or paper.get("paper_summary") or "").strip()
        description = str(paper.get("feed_description") or "").strip()
        metrics = paper.get("metrics") or {}
        votes = metrics.get("public_total_votes", metrics.get("total_votes", 0))
        listed_date = _parse_datetime(paper.get("updated_at"))
        paper_date = _parse_datetime(paper.get("first_publication_date") or paper.get("publication_date"))
        text_parts = [part for part in (abstract, f"alphaXiv summary: {description}" if description else "") if part]

        return Article(
            id=f"{self.config['id']}:{paper_group_id}",
            source_id=self.config["id"],
            source_name=f"{self.config.get('name', 'alphaXiv Hot')} · {votes} votes",
            title=title,
            url=f"https://www.alphaxiv.org/abs/{canonical_id}",
            text="\n\n".join(text_parts)[:30_000],
            # Trending can surface older papers; dates are kept for context, not freshness filtering.
            published_at=None,
            metadata={
                "arxiv_id": canonical_id,
                "paper_group_id": paper_group_id,
                "votes": votes,
                "comment_count": 0,
                "views": (metrics.get("visits_count") or {}).get("last_7_days"),
                "paper_published_at": paper_date.isoformat() if paper_date else None,
                "alphaXiv_updated_at": listed_date.isoformat() if listed_date else None,
            },
        )

    def _attach_discussion(self, article: Article, comments: list[dict[str, Any]]) -> None:
        comment_count = _count_comments(comments)
        article.metadata["comment_count"] = comment_count
        article.source_name += f" · {comment_count} comments"
        excerpts = []
        for comment in comments[:3]:
            author = (comment.get("author") or {}).get("username", "reader")
            body = re.sub(r"\s+", " ", str(comment.get("body") or "")).strip()
            if body:
                excerpts.append(f"@{author}: {body[:400]}")
        if excerpts:
            discussion = "Recent alphaXiv discussion (reader comments):\n" + "\n".join(excerpts)
            article.text = f"{article.text}\n\n{discussion}"[:30_000]

    def _comments(self, client: httpx.Client, paper_group_id: str) -> list[dict[str, Any]]:
        response = client.get(f"{self.base_url}/papers/v3/legacy/{paper_group_id}/comments")
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            payload = payload.get("comments", [])
        return sorted(
            (comment for comment in payload if isinstance(comment, dict)),
            key=lambda comment: (
                int(comment.get("upvotes") or 0),
                str(comment.get("date") or ""),
            ),
            reverse=True,
        )


def _count_comments(comments: list[dict[str, Any]]) -> int:
    total = 0
    for comment in comments:
        total += 1
        replies = comment.get("responses") or []
        if isinstance(replies, list):
            total += _count_comments([reply for reply in replies if isinstance(reply, dict)])
    return total


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    raw = str(value)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed

