import hashlib

import httpx
from bs4 import BeautifulSoup

from news_agent.models import Article


class WebpageAdapter:
    """Fetch a configured article page and extract its readable text."""

    def __init__(self, config: dict):
        self.config = config

    def fetch(self) -> list[Article]:
        url = self.config["url"]
        response = httpx.get(url, follow_redirects=True, timeout=20,
                             headers={"User-Agent": "NewsTrendsAgent/0.1 (+personal research)"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            node.decompose()
        title = (soup.title.get_text(" ", strip=True) if soup.title else url)
        main = soup.find("article") or soup.find("main") or soup.body or soup
        content = "\n".join(line.strip() for line in main.get_text("\n").splitlines() if line.strip())
        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        return [Article(
            id=f"{self.config['id']}:{digest}",
            source_id=self.config["id"],
            source_name=self.config.get("name", self.config["id"]),
            title=self.config.get("title", title),
            url=url,
            text=content[:30_000],
        )]

