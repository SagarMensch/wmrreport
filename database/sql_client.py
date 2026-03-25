"""
SQL Server Client — Connection, execution, and schema introspection
===================================================================
Production-grade wrapper with retry logic, INFORMATION_SCHEMA
validation, and safe serialization of result types.
"""

import json
import logging
import datetime
from decimal import Decimal
from typing import Optional, Any

import pyodbc
from config import settings

log = logging.getLogger("bashira.sql")


class SQLClient:
    """SQL Server read-only client with schema introspection."""

    def __init__(self):
        self._conn: Optional[pyodbc.Connection] = None
        self._valid_columns: Optional[set[str]] = None
        self._valid_tables: Optional[set[str]] = None
        self._column_table_map: Optional[dict[str, set[str]]] = None

    # ── Connection Lifecycle ────────────────────────────────────────────

    def connect(self) -> bool:
        """Establish connection to SQL Server. Returns True on success."""
        try:
            self._conn = pyodbc.connect(
                settings.sql_connection_string, timeout=15
            )
            self._conn.execute("SELECT 1")
            log.info("✓ Connected to SQL Server (%s/%s)",
                     settings.SQL_SERVER, settings.SQL_DATABASE)
            # Pre-load schema for validation
            self._load_schema()
            return True
        except Exception as e:
            log.warning("⚠ SQL Server connection failed: %s", e)
            self._conn = None
            return False

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    def _ensure_connection(self) -> pyodbc.Connection:
        """Return active connection, reconnecting if needed."""
        if self._conn is None:
            self.connect()
        if self._conn is None:
            raise ConnectionError("SQL Server is not available")
        return self._conn

    # ── Schema Introspection (INFORMATION_SCHEMA) ───────────────────────

    def _load_schema(self) -> None:
        """Cache all valid table and column names from INFORMATION_SCHEMA."""
        if self._conn is None:
            return

        cursor = self._conn.cursor()

        # Load tables
        cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE'"
        )
        self._valid_tables = {row[0].lower() for row in cursor.fetchall()}

        # Load columns with table mapping
        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS"
        )
        self._valid_columns = set()
        self._column_table_map = {}
        for row in cursor.fetchall():
            table_name = row[0].lower()
            col_name = row[1].lower()
            self._valid_columns.add(col_name)
            if col_name not in self._column_table_map:
                self._column_table_map[col_name] = set()
            self._column_table_map[col_name].add(table_name)

        cursor.close()
        log.info("   Schema loaded: %d tables, %d unique columns",
                 len(self._valid_tables), len(self._valid_columns))

    def get_valid_columns(self) -> set[str]:
        """Return set of all valid column names (lowercase)."""
        if self._valid_columns is None:
            self._load_schema()
        return self._valid_columns or set()

    def get_valid_tables(self) -> set[str]:
        """Return set of all valid table names (lowercase)."""
        if self._valid_tables is None:
            self._load_schema()
        return self._valid_tables or set()

    def validate_identifiers(self, columns: list[str], tables: list[str]) -> dict:
        """
        Validate column and table names against INFORMATION_SCHEMA.
        Returns {valid: bool, invalid_columns: [...], invalid_tables: [...]}.
        """
        valid_cols = self.get_valid_columns()
        valid_tbls = self.get_valid_tables()

        invalid_columns = [c for c in columns if c.lower() not in valid_cols]
        invalid_tables = [t for t in tables if t.lower() not in valid_tbls]

        return {
            "valid": len(invalid_columns) == 0 and len(invalid_tables) == 0,
            "invalid_columns": invalid_columns,
            "invalid_tables": invalid_tables,
        }

    # ── Query Execution ──────────────────────────────────────────────────

    def _fix_well_counting(self, sql: str) -> str:
        """Auto-fix well counting to use pdo_well_id instead of well_name_after_spud."""
        import re
        
        # Pattern to match: COUNT(*) or COUNT(well_name_after_spud) 
        # when counting wells - should use COUNT(DISTINCT pdo_well_id)
        
        # Check if this is a well-related count query
        well_count_patterns = [
            r'COUNT\(\s*\*\s*\)',
            r'COUNT\(\s*\[?well_name_after_spud\]?\s*\)',
            r'COUNT\(\s*\[?well_name\]?\s*\)',
        ]
        
        is_well_query = any(re.search(p, sql, re.IGNORECASE) for p in well_count_patterns)
        
        if is_well_query and 'pdo_well_id' not in sql.lower():
            # Replace COUNT(*) with COUNT(DISTINCT pdo_well_id)
            sql = re.sub(
                r'COUNT\(\s*\*\s*\)',
                'COUNT(DISTINCT [pdo_well_id])',
                sql,
                flags=re.IGNORECASE
            )
            # Replace COUNT(well_name_after_spud) with COUNT(DISTINCT pdo_well_id)
            sql = re.sub(
                r'COUNT\(\s*\[?well_name_after_spud\]?\s*\)',
                'COUNT(DISTINCT [pdo_well_id])',
                sql,
                flags=re.IGNORECASE
            )
        
        return sql

    def _fix_numeric_comparisons(self, sql: str) -> str:
        """Auto-fix ALL SQL queries with numeric comparisons - universal fix."""
        
        if 'TRY_CAST' in sql.upper() or 'CAST' in sql.upper():
            return sql
        
        import re
        
        # UNIVERSAL FIX: Find ALL "WHERE column > number" patterns and wrap in TRY_CAST
        # This works for ANY column, not specific ones
        
        # Pattern to match: WHERE [column] > number or WHERE column > number
        # Capture: column name (with optional brackets) and operator with number
        pattern = r'WHERE\s+(\[?[\w_]+\]?)\s*(>|<|>=|<=|=)\s*(\d+)'
        
        def replace_match(m):
            col = m.group(1).strip()
            op_num = m.group(2) + m.group(3)
            
            # Ensure column has brackets
            if not col.startswith('['):
                col = f'[{col}]'
            
            return f'WHERE TRY_CAST({col} AS FLOAT) {op_num}'
        
        # Apply the fix
        fixed_sql = re.sub(pattern, replace_match, sql, flags=re.IGNORECASE)
        
        return fixed_sql

    def execute_query(self, sql: str, max_rows: Optional[int] = None) -> dict:
        """
        Execute a read-only SQL query.
        Returns {columns, rows, total_rows, truncated, error}.
        """
        max_rows = max_rows or settings.SQL_MAX_ROWS

        # Auto-fix type conversion issues
        original_sql = sql
        sql = self._fix_numeric_comparisons(sql)
        sql = self._fix_well_counting(sql)  # Fix well counting to use pdo_well_id
        if sql != original_sql:
            log.info(f"SQL auto-fixed: {original_sql[:100]}... -> {sql[:100]}...")

        # Debug log
        if 'engg_kpi' in sql.lower() or 'kpi' in sql.lower():
            log.info(f"Executing KPI query: {sql[:200]}")

        try:
            conn = self._ensure_connection()
            cursor = conn.cursor()
            cursor.execute(sql)

            columns = [desc[0] for desc in cursor.description]
            rows_raw = cursor.fetchmany(max_rows)
            total = cursor.rowcount if cursor.rowcount >= 0 else len(rows_raw)
            cursor.close()

            # Serialize to JSON-safe types
            rows = [self._serialize_row(row) for row in rows_raw]

            return {
                "columns": columns,
                "rows": rows,
                "total_rows": total,
                "truncated": len(rows) >= max_rows,
                "error": None,
            }

        except pyodbc.ProgrammingError as e:
            return self._error_result(f"SQL Error: {e}")
        except pyodbc.Error as e:
            # Connection may be dead — reset for next attempt
            self._conn = None
            return self._error_result(f"Database Error: {e}")
        except Exception as e:
            return self._error_result(f"Unexpected Error: {e}")

    @staticmethod
    def _serialize_row(row) -> list[Any]:
        """Convert pyodbc.Row to JSON-serializable list."""
        result = []
        for val in row:
            if val is None:
                result.append(None)
            elif isinstance(val, (datetime.date, datetime.datetime)):
                result.append(val.isoformat())
            elif isinstance(val, Decimal):
                result.append(float(val))
            elif isinstance(val, bytes):
                result.append(val.hex())
            else:
                try:
                    json.dumps(val)
                    result.append(val)
                except (TypeError, ValueError):
                    result.append(str(val))
        return result

    @staticmethod
    def _error_result(msg: str) -> dict:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "truncated": False,
            "error": msg,
        }

    # ── Health ───────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        try:
            conn = self._ensure_connection()
            conn.execute("SELECT 1")
            return True
        except Exception:
            return False


# Singleton
sql_client = SQLClient()
