import os

import httpx

from news_agent.models import Summary


class SlackWebhook:
    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("SLACK_WEBHOOK_URL")
        if not self.url:
            raise ValueError("Set SLACK_WEBHOOK_URL to deliver a digest")

    def send(self, summaries: list[Summary]) -> None:
        if not summaries:
            return
        entries = []
        for item in summaries:
            article = item.article
            title = article.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            summary = item.summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            linked_title = f"<{article.url}|{title}>" if article.url else title
            entries.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*{linked_title}*\n_{article.source_name}_\n{summary}"[:2900]}})
        for start in range(0, len(entries), 24):
            blocks = [{"type": "header", "text": {"type": "plain_text", "text": "AI news & trends"}}]
            for entry in entries[start:start + 24]:
                blocks.extend([entry, {"type": "divider"}])
            response = httpx.post(self.url, json={"blocks": blocks}, timeout=20)
            response.raise_for_status()

