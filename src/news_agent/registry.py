from news_agent.sources.imap_newsletter import IMAPNewsletterAdapter
from news_agent.sources.huggingface_papers import HuggingFacePapersAdapter
from news_agent.sources.alphaxiv import AlphaXivAdapter
from news_agent.sources.arxiv import ArxivAdapter
from news_agent.sources.rss import RSSAdapter
from news_agent.sources.webpage import WebpageAdapter
from news_agent.sources.x_search import XSearchAdapter

SOURCE_ADAPTERS = {
    "rss": RSSAdapter,
    "webpage": WebpageAdapter,
    "x_search": XSearchAdapter,
    "imap_newsletter": IMAPNewsletterAdapter,
    "hf_daily_papers": HuggingFacePapersAdapter,
    "alphaxiv": AlphaXivAdapter,
    "arxiv": ArxivAdapter,
}


def register_source(name: str, adapter: type) -> None:
    """Register an adapter so new source types can be added without pipeline changes."""
    SOURCE_ADAPTERS[name] = adapter

