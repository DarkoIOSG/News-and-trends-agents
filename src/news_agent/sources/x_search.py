import os
from datetime import datetime

import httpx

from news_agent.models import Article


class XSearchAdapter:
    """Search recent public posts through the official X API v2."""

    def __init__(self, config: dict):
        self.config = config

    def fetch(self) -> list[Article]:
        token = self.config.get("bearer_token") or os.getenv("X_BEARER_TOKEN")
        if not token:
            raise ValueError("Set X_BEARER_TOKEN to use an x_search source")
        params = {
            "query": self.config["query"],
            "max_results": min(max(int(self.config.get("max_items", 10)), 10), 100),
            "tweet.fields": "created_at,author_id,public_metrics",
            "expansions": "author_id",
            "user.fields": "name,username",
        }
        response = httpx.get("https://api.x.com/2/tweets/search/recent", params=params,
                             headers={"Authorization": f"Bearer {token}"}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        users = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}
        articles = []
        for post in payload.get("data", []):
            user = users.get(post.get("author_id"), {})
            username = user.get("username", "i")
            post_id = post["id"]
            articles.append(Article(
                id=f"{self.config['id']}:{post_id}",
                source_id=self.config["id"],
                source_name=self.config.get("name", self.config["id"]),
                title=f"@{username}: {post['text'][:120]}",
                url=f"https://x.com/{username}/status/{post_id}",
                text=post["text"],
                published_at=datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
                if post.get("created_at") else None,
                metadata={"metrics": post.get("public_metrics", {})},
            ))
        return articles[:int(self.config.get("max_items", 10))]

