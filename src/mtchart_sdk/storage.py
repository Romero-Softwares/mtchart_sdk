from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from mtchart_sdk.rules import clean_identifier


class PartsCatalog:
    def __init__(self, db_path: str | Path = "mtchart_sdk.db") -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent != Path("."):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS catalog_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pn TEXT NOT NULL,
                    name_norm TEXT NOT NULL,
                    pn_norm TEXT NOT NULL,
                    use_count INTEGER DEFAULT 1,
                    last_used_at TEXT NOT NULL,
                    UNIQUE(name_norm, pn_norm)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_catalog_parts_name ON catalog_parts(name_norm)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_catalog_parts_pn ON catalog_parts(pn_norm)")

    def save(self, name: str, pn: str, increment: bool = True) -> None:
        name = clean_identifier(name)
        pn = clean_identifier(pn)
        if not name or not pn:
            raise ValueError("name and pn are required")
        name_norm = name.upper()
        pn_norm = pn.upper()
        increment_by = 1 if increment else 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO catalog_parts (name, pn, name_norm, pn_norm, use_count, last_used_at)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(name_norm, pn_norm) DO UPDATE SET
                    name = excluded.name,
                    pn = excluded.pn,
                    use_count = catalog_parts.use_count + ?,
                    last_used_at = excluded.last_used_at
                """,
                (name, pn, name_norm, pn_norm, now, increment_by),
            )

    def search(self, term: str = "", limit: int = 100) -> list[dict[str, object]]:
        term_norm = clean_identifier(term).upper()
        limit = max(1, min(1000, int(limit or 100)))
        query = """
            SELECT id, name, pn, use_count, last_used_at
            FROM catalog_parts
        """
        params: tuple[object, ...]
        if term_norm:
            query += " WHERE name_norm LIKE ? OR pn_norm LIKE ?"
            params = (f"%{term_norm}%", f"%{term_norm}%", limit)
        else:
            params = (limit,)
        query += " ORDER BY use_count DESC, id DESC LIMIT ?"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "pn": row[2],
                "use_count": row[3],
                "last_used_at": row[4],
            }
            for row in rows
        ]
