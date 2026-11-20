import os

import anthropic
from openai import OpenAI

from news_agent.models import Article, Summary


class AnthropicSummarizer:
    def __init__(self):
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("Set ANTHROPIC_API_KEY to use the Anthropic summarizer")
        self.client = anthropic.Anthropic()
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

    def summarize(self, articles: list[Article]) -> list[Summary]:
        summaries = []
        for article in articles:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                system=(
                    "You summarize AI industry news for a busy reader. Be accurate and concrete. "
                    "Use only the supplied material; say when details are unclear. Return two short "
                    "sentences: first the development, second why it matters."
                ),
                messages=[{
                    "role": "user",
                    "content": f"Title: {article.title}\nSource: {article.source_name}\n\n{article.content[:12_000]}",
                }],
            )
            text = "\n".join(block.text for block in response.content if block.type == "text").strip()
            summaries.append(Summary(article=article, summary=text))
        return summaries


class OpenAISummarizer:
    def __init__(self):
        self.client = OpenAI()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def summarize(self, articles: list[Article]) -> list[Summary]:
        summaries = []
        for article in articles:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": (
                        "You summarize AI industry news for a busy reader. Be accurate and concrete. "
                        "Use only the supplied material; say when details are unclear. Return two short "
                        "sentences: first the development, second why it matters."
                    )},
                    {"role": "user", "content": f"Title: {article.title}\nSource: {article.source_name}\n\n{article.content[:12_000]}"},
                ],
            )
            text = (response.choices[0].message.content or "").strip()
            summaries.append(Summary(article=article, summary=text))
        return summaries


def create_summarizer():
    provider = os.getenv("SUMMARY_PROVIDER", "anthropic").casefold()
    if provider == "anthropic":
        return AnthropicSummarizer()
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Set OPENAI_API_KEY to use the OpenAI summarizer")
        return OpenAISummarizer()
    raise ValueError(f"Unknown SUMMARY_PROVIDER {provider!r}; choose 'anthropic' or 'openai'")

