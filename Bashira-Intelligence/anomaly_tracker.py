from __future__ import annotations

import datetime as dt
import logging
import os
import re
import sqlite3
from typing import Any, Dict, List

try:
    import pyodbc
except Exception:  # pragma: no cover - pyodbc is expected in production
    pyodbc = None

from config import settings

log = logging.getLogger("bashira.anomaly")

DEFAULT_ANOMALY_TABLE = "bashira_anomalies"
DEFAULT_WELL_STATE_TABLE = "bashira_well_state"
DEFAULT_SQL_SCHEMA = "dbo"
DEFAULT_SQLITE_PATH = "anomalies.db"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_identifier(value: str, fallback: str) -> str:
    candidate = (value or fallback).strip()
    if not _IDENTIFIER_RE.match(candidate):
        log.warning("Invalid SQL identifier '%s'; falling back to '%s'", candidate, fallback)
        return fallback
    return candidate


class AnomalyTracker:
    """
    Risk-tier transition tracker with config-driven persistence.

    Primary backend is SQL Server using the same `.env` connection as the rest
    of the application. SQLite is only used when explicitly allowed via env.
    If neither persistent backend is available, the tracker falls back to an
    in-memory store so the API stays operational without silent local writes.
    """

    def __init__(self):
        self.backend = "memory"
        self._memory_state: dict[str, dict[str, Any]] = {}
        self._memory_anomalies: list[dict[str, Any]] = []
        self._preferred_backend = os.environ.get("ANOMALY_TRACKER_BACKEND", "sqlserver").strip().lower()
        self._allow_sqlite_fallback = (
            os.environ.get("ANOMALY_TRACKER_ALLOW_SQLITE_FALLBACK", "false").strip().lower() == "true"
        )
        self._sqlite_path = os.environ.get("ANOMALY_SQLITE_PATH", DEFAULT_SQLITE_PATH)
        self._sql_schema = _safe_identifier(
            os.environ.get("ANOMALY_SQL_SCHEMA", DEFAULT_SQL_SCHEMA),
            DEFAULT_SQL_SCHEMA,
        )
        self._anomaly_table = _safe_identifier(
            os.environ.get("ANOMALY_TABLE", DEFAULT_ANOMALY_TABLE),
            DEFAULT_ANOMALY_TABLE,
        )
        self._state_table = _safe_identifier(
            os.environ.get("ANOMALY_WELL_STATE_TABLE", DEFAULT_WELL_STATE_TABLE),
            DEFAULT_WELL_STATE_TABLE,
        )
        self._init_backend()

    def _init_backend(self) -> None:
        if self._preferred_backend == "memory":
            log.info("Anomaly tracker running in memory-only mode")
            self.backend = "memory"
            return

        if self._preferred_backend == "sqlite":
            if self._allow_sqlite_fallback:
                self._init_sqlite()
                return
            log.warning("SQLite backend requested but not allowed; using memory backend")
            self.backend = "memory"
            return

        if self._try_init_sql_server():
            return

        if self._allow_sqlite_fallback:
            self._init_sqlite()
            return

        log.warning(
            "SQL Server anomaly persistence unavailable and SQLite fallback disabled; using memory backend"
        )
        self.backend = "memory"

    def _connect_sql_server(self):
        if pyodbc is None:
            raise RuntimeError("pyodbc is not installed")
        return pyodbc.connect(settings.sql_connection_string, timeout=10)

    def _qualified_table(self, table: str) -> str:
        return f"[{self._sql_schema}].[{table}]"

    def _try_init_sql_server(self) -> bool:
        try:
            self._init_sql_server()
            self.backend = "sqlserver"
            log.info(
                "Anomaly tracker using SQL Server tables %s and %s",
                self._qualified_table(self._anomaly_table),
                self._qualified_table(self._state_table),
            )
            return True
        except Exception as exc:
            log.warning("SQL Server anomaly tracker initialization failed: %s", exc)
            return False

    def _init_sql_server(self) -> None:
        anomaly_table = self._qualified_table(self._anomaly_table)
        state_table = self._qualified_table(self._state_table)
        with self._connect_sql_server() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                IF OBJECT_ID(N'{self._sql_schema}.{self._anomaly_table}', N'U') IS NULL
                BEGIN
                    CREATE TABLE {anomaly_table} (
                        id BIGINT IDENTITY(1,1) PRIMARY KEY,
                        well NVARCHAR(255) NOT NULL,
                        old_tier NVARCHAR(64) NOT NULL,
                        new_tier NVARCHAR(64) NOT NULL,
                        severity NVARCHAR(32) NOT NULL,
                        delta FLOAT NOT NULL,
                        timestamp_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
                    );
                    CREATE INDEX IX_{self._anomaly_table}_timestamp
                    ON {anomaly_table}(timestamp_utc DESC);
                END
                """
            )
            cursor.execute(
                f"""
                IF OBJECT_ID(N'{self._sql_schema}.{self._state_table}', N'U') IS NULL
                BEGIN
                    CREATE TABLE {state_table} (
                        well NVARCHAR(255) PRIMARY KEY,
                        current_tier NVARCHAR(64) NOT NULL,
                        last_score FLOAT NOT NULL,
                        last_updated_utc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
                    );
                END
                """
            )
            conn.commit()

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self._sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    well TEXT NOT NULL,
                    old_tier TEXT NOT NULL,
                    new_tier TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    delta FLOAT NOT NULL,
                    timestamp_utc DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS well_state (
                    well TEXT PRIMARY KEY,
                    current_tier TEXT NOT NULL,
                    last_score FLOAT NOT NULL,
                    last_updated_utc DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        self.backend = "sqlite"
        log.warning("Anomaly tracker fell back to SQLite at %s", self._sqlite_path)

    @staticmethod
    def _calculate_severity(old_idx: int, new_idx: int) -> str:
        if new_idx > old_idx:
            jump = new_idx - old_idx
            return "P1" if jump >= 2 else "P2"
        return "P3"

    @staticmethod
    def _tier_levels() -> dict[str, int]:
        return {
            "HEALTHY": 0,
            "WATCH": 1,
            "HIGH_RISK": 2,
            "CRITICAL": 3,
            "UNKNOWN": 0,
        }

    def sync_well_state(self, well: str, new_score: float, new_tier: str) -> bool:
        normalized_well = (well or "").strip()
        normalized_tier = (new_tier or "UNKNOWN").strip().upper() or "UNKNOWN"
        if not normalized_well:
            return False

        if self.backend == "sqlserver":
            return self._sync_well_state_sql_server(normalized_well, float(new_score), normalized_tier)
        if self.backend == "sqlite":
            return self._sync_well_state_sqlite(normalized_well, float(new_score), normalized_tier)
        return self._sync_well_state_memory(normalized_well, float(new_score), normalized_tier)

    def _sync_well_state_sql_server(self, well: str, new_score: float, new_tier: str) -> bool:
        state_table = self._qualified_table(self._state_table)
        anomaly_table = self._qualified_table(self._anomaly_table)
        tier_levels = self._tier_levels()

        with self._connect_sql_server() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT current_tier, last_score FROM {state_table} WHERE well = ?",
                (well,),
            )
            row = cursor.fetchone()
            changed = False

            if row:
                old_tier, old_score = row
                old_tier = (old_tier or "UNKNOWN").strip().upper()
                old_score = float(old_score or 0.0)
                if old_tier != new_tier:
                    severity = self._calculate_severity(
                        tier_levels.get(old_tier, 0),
                        tier_levels.get(new_tier, 0),
                    )
                    cursor.execute(
                        f"""
                        INSERT INTO {anomaly_table} (well, old_tier, new_tier, severity, delta)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (well, old_tier, new_tier, severity, float(new_score - old_score)),
                    )
                    changed = True
                cursor.execute(
                    f"""
                    UPDATE {state_table}
                    SET current_tier = ?, last_score = ?, last_updated_utc = SYSUTCDATETIME()
                    WHERE well = ?
                    """,
                    (new_tier, new_score, well),
                )
            else:
                cursor.execute(
                    f"""
                    INSERT INTO {state_table} (well, current_tier, last_score)
                    VALUES (?, ?, ?)
                    """,
                    (well, new_tier, new_score),
                )

            conn.commit()
            return changed

    def _sync_well_state_sqlite(self, well: str, new_score: float, new_tier: str) -> bool:
        tier_levels = self._tier_levels()
        with sqlite3.connect(self._sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_tier, last_score FROM well_state WHERE well = ?", (well,))
            row = cursor.fetchone()
            changed = False

            if row:
                old_tier, old_score = row
                old_tier = (old_tier or "UNKNOWN").strip().upper()
                old_score = float(old_score or 0.0)
                if old_tier != new_tier:
                    severity = self._calculate_severity(
                        tier_levels.get(old_tier, 0),
                        tier_levels.get(new_tier, 0),
                    )
                    cursor.execute(
                        """
                        INSERT INTO anomalies (well, old_tier, new_tier, severity, delta)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (well, old_tier, new_tier, severity, float(new_score - old_score)),
                    )
                    changed = True
                cursor.execute(
                    """
                    UPDATE well_state
                    SET current_tier = ?, last_score = ?, last_updated_utc = CURRENT_TIMESTAMP
                    WHERE well = ?
                    """,
                    (new_tier, new_score, well),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO well_state (well, current_tier, last_score)
                    VALUES (?, ?, ?)
                    """,
                    (well, new_tier, new_score),
                )
            conn.commit()
            return changed

    def _sync_well_state_memory(self, well: str, new_score: float, new_tier: str) -> bool:
        tier_levels = self._tier_levels()
        current = self._memory_state.get(well)
        changed = False

        if current and current["current_tier"] != new_tier:
            old_tier = current["current_tier"]
            old_score = float(current["last_score"])
            anomaly = {
                "id": str(len(self._memory_anomalies) + 1),
                "well": well,
                "old_tier": old_tier,
                "new_tier": new_tier,
                "severity": self._calculate_severity(
                    tier_levels.get(old_tier, 0),
                    tier_levels.get(new_tier, 0),
                ),
                "delta": float(new_score - old_score),
                "timestamp_utc": dt.datetime.utcnow(),
            }
            self._memory_anomalies.insert(0, anomaly)
            changed = True

        self._memory_state[well] = {
            "current_tier": new_tier,
            "last_score": float(new_score),
            "last_updated_utc": dt.datetime.utcnow(),
        }
        return changed

    def get_recent_anomalies(self, limit: int = 50) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 50), 200))
        if self.backend == "sqlserver":
            return self._get_recent_anomalies_sql_server(safe_limit)
        if self.backend == "sqlite":
            return self._get_recent_anomalies_sqlite(safe_limit)
        return self._get_recent_anomalies_memory(safe_limit)

    def _get_recent_anomalies_sql_server(self, limit: int) -> List[Dict[str, Any]]:
        anomaly_table = self._qualified_table(self._anomaly_table)
        with self._connect_sql_server() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT well, old_tier, new_tier, severity, delta, timestamp_utc
                FROM {anomaly_table}
                ORDER BY timestamp_utc DESC
                OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY
                """
            )
            rows = cursor.fetchall()
        anomalies: list[dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            anomalies.append(
                self._serialize_anomaly(
                    {
                        "id": str(idx),
                        "well": row[0],
                        "old_tier": row[1],
                        "new_tier": row[2],
                        "severity": row[3],
                        "delta": float(row[4] or 0.0),
                        "timestamp_utc": row[5],
                    }
                )
            )
        return anomalies

    def _get_recent_anomalies_sqlite(self, limit: int) -> List[Dict[str, Any]]:
        with sqlite3.connect(self._sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, well, old_tier, new_tier, severity, delta, timestamp_utc
                FROM anomalies
                ORDER BY timestamp_utc DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        return [self._serialize_anomaly(dict(row)) for row in rows]

    def _get_recent_anomalies_memory(self, limit: int) -> List[Dict[str, Any]]:
        return [self._serialize_anomaly(row) for row in self._memory_anomalies[:limit]]

    def _serialize_anomaly(self, row: dict[str, Any]) -> dict[str, Any]:
        timestamp = row.get("timestamp_utc")
        if isinstance(timestamp, str):
            try:
                timestamp = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                timestamp = None
        return {
            "id": str(row.get("id", "")),
            "well": str(row.get("well", "")),
            "old_tier": str(row.get("old_tier", "UNKNOWN")),
            "new_tier": str(row.get("new_tier", "UNKNOWN")),
            "severity": str(row.get("severity", "P3")),
            "delta": float(row.get("delta", 0.0) or 0.0),
            "timestamp": self._humanize_timestamp(timestamp),
        }

    @staticmethod
    def _humanize_timestamp(value: Any) -> str:
        if not isinstance(value, dt.datetime):
            return "unknown"
        if value.tzinfo is not None:
            value = value.astimezone(dt.timezone.utc).replace(tzinfo=None)
        now = dt.datetime.utcnow()
        diff_seconds = max(0, int((now - value).total_seconds()))
        if diff_seconds < 60:
            return "just now"
        if diff_seconds < 3600:
            return f"{diff_seconds // 60} mins ago"
        if diff_seconds < 86400:
            return f"{diff_seconds // 3600} hours ago"
        return f"{diff_seconds // 86400} days ago"


def seed_dummies() -> None:
    tracker = AnomalyTracker()
    log.info("Demo seeding is disabled; active backend is %s", tracker.backend)


if __name__ == "__main__":
    tracker = AnomalyTracker()
    print(f"Anomaly Tracker initialized with backend: {tracker.backend}")
