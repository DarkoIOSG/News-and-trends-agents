import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS sent_items (id TEXT PRIMARY KEY, sent_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        self.connection.commit()

    def has(self, item_id: str) -> bool:
        return self.connection.execute("SELECT 1 FROM sent_items WHERE id = ?", (item_id,)).fetchone() is not None

    def mark_sent(self, item_ids: list[str]) -> None:
        self.connection.executemany("INSERT OR IGNORE INTO sent_items (id) VALUES (?)", [(item_id,) for item_id in item_ids])
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

