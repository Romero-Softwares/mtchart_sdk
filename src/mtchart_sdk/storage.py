from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Protocol

from mtchart_sdk.models import AuditOperation
from mtchart_sdk.rules import clean_identifier


class PartsCatalogStorage(Protocol):
    def save(self, name: str, pn: str, increment: bool = True) -> None:
        """Store or update a part/name relation."""

    def search(self, term: str = "", limit: int = 100) -> list[dict[str, object]]:
        """Return catalog matches ordered by the backend preference."""


class AuditOperationStorage(Protocol):
    def record_audit_operation(
        self,
        operator_id: str,
        action: str,
        tab: str = "",
        details: str = "",
        occurred_at: datetime | str | None = None,
    ) -> int | None:
        """Store an auditable operation and return its id when persisted."""

    def list_audit_operations(
        self,
        limit: int = 1000,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
    ) -> list[dict[str, object]]:
        """Return operation logs ordered from newest to oldest."""

    def has_audit_operations(self) -> bool:
        """Return True when at least one audit operation exists."""


class SQLitePartsCatalog:
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_operacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora DATETIME NOT NULL,
                    matricula TEXT NOT NULL,
                    aba TEXT,
                    acao TEXT NOT NULL,
                    detalhes TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_operacoes_data ON audit_operacoes(data_hora)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_operacoes_matricula ON audit_operacoes(matricula)")

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

    @staticmethod
    def _datetime_text(value: datetime | str | None, *, end: bool = False) -> str | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.replace(second=59 if end else 0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        text = str(value).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(text, fmt)
                return parsed.replace(second=59 if end else 0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        if len(text) >= 16:
            return f"{text[:16]}:{'59' if end else '00'}"
        return text

    @staticmethod
    def _audit_datetime(value: datetime | str | None) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value or datetime.now().strftime("%Y-%m-%d %H:%M:%S")).strip()

    def record_audit_operation(
        self,
        operator_id: str,
        action: str,
        tab: str = "",
        details: str = "",
        occurred_at: datetime | str | None = None,
    ) -> int | None:
        operator = str(operator_id or "").strip().upper()
        action_text = str(action or "").strip()
        if not operator or not action_text:
            return None
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_operacoes (data_hora, matricula, aba, acao, detalhes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self._audit_datetime(occurred_at), operator, str(tab or ""), action_text, str(details or "")),
            )
            return int(cursor.lastrowid)

    def save_audit_operation(self, operation: AuditOperation) -> int | None:
        return self.record_audit_operation(
            operation.operator_id,
            operation.action,
            operation.tab,
            operation.details,
            operation.occurred_at,
        )

    def list_audit_operations(
        self,
        limit: int = 1000,
        start: datetime | str | None = None,
        end: datetime | str | None = None,
    ) -> list[dict[str, object]]:
        limit = max(1, min(5000, int(limit or 1000)))
        filters = []
        params: list[object] = []
        if start:
            filters.append("data_hora >= ?")
            params.append(self._datetime_text(start))
        if end:
            filters.append("data_hora <= ?")
            params.append(self._datetime_text(end, end=True))
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, data_hora, matricula, aba, acao, detalhes
                FROM audit_operacoes
                {where}
                ORDER BY data_hora DESC, id DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [
            {
                "id": row[0],
                "data_hora": row[1],
                "matricula": row[2],
                "aba": row[3],
                "acao": row[4],
                "detalhes": row[5],
            }
            for row in rows
        ]

    def has_audit_operations(self) -> bool:
        with self.connect() as conn:
            return conn.execute("SELECT 1 FROM audit_operacoes LIMIT 1").fetchone() is not None


PartsCatalog = SQLitePartsCatalog
AuditLogStorage = SQLitePartsCatalog
