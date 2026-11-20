from typing import Protocol

from news_agent.models import Article


class SourceAdapter(Protocol):
    def fetch(self) -> list[Article]: ...

