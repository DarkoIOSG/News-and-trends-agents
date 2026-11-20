# News and trends agents

A modular home for agents that collect information from configurable sources, summarize it, and deliver it to a destination. The first agent focuses on AI news and trends, with Slack as its first destination.

## First agent

1. Read enabled sources from config/sources.yaml.
2. Fetch items through a source adapter.
3. Skip old and previously sent items using SQLite.
4. Summarize each new item with Anthropic Claude by default (OpenAI is also supported).
5. Send the digest to Slack through an incoming webhook.

Supported source types:

| Type | Use |
| --- | --- |
| rss | RSS and Atom feeds, including many newsletters and Substack publications |
| hf_daily_papers | Trending Hugging Face Daily Papers, filtered by configurable keywords |
| webpage | A specific article URL |
| x_search | Recent public posts matching an X API v2 search query |
| imap_newsletter | Unseen messages from an IMAP mailbox, optionally filtered by sender and subject |

## Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .
    cp .env.example .env

Set ANTHROPIC_API_KEY and SLACK_WEBHOOK_URL in the environment before running. Anthropic is the default summarizer and uses claude-sonnet-5; set ANTHROPIC_MODEL to choose another Claude model. To use OpenAI instead, set SUMMARY_PROVIDER=openai and OPENAI_API_KEY. Set the X bearer token or IMAP credentials only if those adapters are enabled. The CLI loads values from .env; ensure your scheduler loads the same environment.

Edit config/sources.yaml. For a feed:

    max_age_hours: 48
    sources:
      - id: example-substack
        type: rss
        name: Example Substack
        url: https://example.substack.com/feed
        enabled: true
        max_items: 10

The default configuration enables a Hugging Face Daily Papers source for the current week, sorted by trending score and filtered for agents, inference, serving, compute, GPUs, hardware, and scaling. The public feed does not require a Hugging Face token. Adjust its period (day, week, month), sort order, keywords, or result limits in config/sources.yaml.

For X search, use type x_search and a query accepted by the X API. For newsletters delivered by email, enable imap_newsletter; credentials should stay in environment variables. config/sources.example.yaml contains examples of each adapter.

## Run and schedule

    news-agent run
    # or: python -m news_agent.cli run --config config/sources.yaml

The GitHub Actions workflow runs every Monday at 08:00 in Europe/Belgrade and also supports manual runs from the Actions tab. It caches the SQLite sent-item database between runs to avoid repeating papers.

Before the scheduled workflow can deliver digests, add these repository Actions secrets under Settings > Secrets and variables > Actions:

- ANTHROPIC_API_KEY
- SLACK_WEBHOOK_URL

Local runs use data/news-agent.sqlite3 by default; set NEWS_AGENT_DB to change it. GitHub Actions stores its own state cache and does not use the local .env file.

## Add or remove sources

Add a source object to sources.yaml and set its type; remove it or set enabled: false to stop fetching it. Each adapter lives in src/news_agent/sources/. To add a new kind, implement a class with fetch() -> list[Article] and register it in src/news_agent/registry.py; the pipeline does not need source-specific changes.

## Project layout

    config/                 Source configuration
    src/news_agent/
      sources/              RSS, webpage, X, and IMAP adapters
      pipeline.py           Collection, dedupe, summarize, delivery
      summarizer.py         Anthropic default and OpenAI alternative
      slack.py              Replaceable delivery boundary
      store.py               Sent-item deduplication

This is a first runnable foundation. Add destinations, richer ranking, per-source instructions, and a persistent scheduler as the workflow becomes clearer.
