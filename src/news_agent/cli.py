import argparse
from pathlib import Path

from dotenv import load_dotenv

from news_agent.config import load_config
from news_agent.pipeline import run


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Collect, summarize, and send an AI news digest.")
    parser.add_argument("run", nargs="?", default="run", choices=["run"])
    parser.add_argument("--config", type=Path, default=Path("config/sources.yaml"))
    args = parser.parse_args()
    run(load_config(args.config))


if __name__ == "__main__":
    main()

