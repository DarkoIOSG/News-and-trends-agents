from datetime import timedelta

from news_agent.config import AppConfig
from news_agent.models import utc_now
from news_agent.registry import SOURCE_ADAPTERS
from news_agent.slack import SlackWebhook
from news_agent.store import Store
from news_agent.summarizer import create_summarizer


def run(config: AppConfig) -> int:
    store = Store(config.database)
    try:
        fetched = []
        for source in config.sources:
            if not source.get("enabled", True):
                continue
            source_type = source.get("type")
            adapter_class = SOURCE_ADAPTERS.get(source_type)
            if adapter_class is None:
                raise ValueError(f"Unknown source type {source_type!r} for source {source.get('id')!r}")
            try:
                fetched.extend(adapter_class(source).fetch())
            except Exception as exc:
                print(f"Source {source.get('id', source_type)} failed: {exc}")

        cutoff = utc_now() - timedelta(hours=config.max_age_hours)
        fresh = []
        for article in fetched:
            if article.published_at and article.published_at < cutoff:
                continue
            if not store.has(article.id):
                fresh.append(article)
        if not fresh:
            print("No new items to send.")
            return 0

        summaries = create_summarizer().summarize(fresh)
        SlackWebhook().send(summaries)
        store.mark_sent([item.article.id for item in summaries])
        print(f"Sent {len(summaries)} items to Slack.")
        return len(summaries)
    finally:
        store.close()

