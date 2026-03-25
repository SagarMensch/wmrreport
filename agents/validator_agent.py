"""
Validator Agent — SQL validation + self-healing loop
===================================================
Validates generated SQL against:
  1. Security rules (forbidden keywords, patterns)
  2. Schema correctness (INFORMATION_SCHEMA column/table check)
  3. BM25 anti-hallucination check (verify tables/columns exist)
  4. Execution success (catches runtime errors)

Self-healing: on failure, feeds error context back to SQL Agent
for automatic correction (up to MAX_HEAL_RETRIES attempts).
"""

import re
import logging
from dataclasses import dataclass, field

import sqlparse
from database.sql_client import sql_client
from agents.sql_agent import SQLAgent, SQLResult, FORBIDDEN_KEYWORDS, FORBIDDEN_PATTERNS
from config import settings

log = logging.getLogger("bashira.validator")

# BM25 index for anti-hallucination - loaded lazily
_bm25_index = None

def _get_bm25_index():
    """Get or create BM25 index for validation."""
    global _bm25_index
    if _bm25_index is None:
        from retrieval.bm25_index import ColumnBM25Index
        _bm25_index = ColumnBM25Index(settings.columns_csv_path)
        log.info("BM25 index loaded for validation")
    return _bm25_index


# ── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of SQL validation."""
    is_valid: bool
    security_passed: bool
    schema_passed: bool
    invalid_columns: list[str] = field(default_factory=list)
    invalid_tables: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Final execution result including any self-healing history."""
    sql_query: str
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    total_rows: int = 0
    truncated: bool = False
    error: str | None = None
    healed: bool = False
    heal_attempts: int = 0
    validation: ValidationResult | None = None


# ── SQL Parsing ──────────────────────────────────────────────────────────

def extract_identifiers(sql: str) -> tuple[list[str], list[str]]:
    """
    Extract table and column identifiers from SQL using sqlparse.
    Returns (tables, columns).
    """
    tables = set()
    columns = set()

    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return [], []

        statement = parsed[0]
        tokens = list(statement.flatten())

        # State machine to track context
        after_from = False
        after_join = False
        after_select = False
        after_dot = False
        skip_cte_name = False  # Skip CTE name after WITH

        for i, token in enumerate(tokens):
            ttype = str(token.ttype)
            value = token.value.strip()

            if not value or value in (',', '(', ')', '*', '='):
                continue

            upper = value.upper()

            if upper == 'SELECT':
                after_select = True
                after_from = False
                after_join = False
                skip_cte_name = False
                continue
            elif upper == 'WITH':
                skip_cte_name = True  # Next identifier is CTE name
                after_from = False
                after_join = False
                continue
            elif upper in ('FROM', 'INTO'):
                after_from = True
                after_select = False
                after_join = False
                skip_cte_name = False
                continue
            elif upper in ('JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'CROSS'):
                after_join = True
                after_from = False
                after_select = False
                skip_cte_name = False
                continue
            elif upper in ('WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT',
                          'ON', 'AND', 'OR', 'SET',
                          'NOT', 'NULL', 'IS', 'IN', 'BETWEEN',
                          'LIKE', 'EXISTS', 'CASE', 'WHEN', 'THEN',
                          'ELSE', 'END', 'CAST', 'VARCHAR', 'INT',
                          'FLOAT', 'DECIMAL', 'TOP', 'DESC', 'ASC',
                          'UNION', 'ALL', 'OVER',
                          'PARTITION', 'ROWS', 'RANGE', 'PRECEDING',
                          'FOLLOWING', 'CURRENT', 'ROW', 'UNBOUNDED'):
                after_from = False
                after_join = False
                after_select = False
                skip_cte_name = False
                continue
            
            # DISTINCT, COUNT, SUM, AVG, MAX, MIN, AS should NOT reset after_select
            # They are part of the SELECT clause
            
            # Skip CTE name after WITH
            if skip_cte_name:
                skip_cte_name = False
                continue

            # Skip numbers, strings, operators
            if 'Literal' in ttype or 'Operator' in ttype:
                continue
            if 'Keyword' in ttype:
                continue

            # Clean brackets
            clean = value.strip('[]"\'`')
            if not clean:
                continue
            
            # Skip table aliases (containing . like w.column)
            if '.' in clean:
                continue

            if after_from or after_join:
                tables.add(clean)
                after_from = False
                after_join = False
            
            # Extract columns from SELECT clause (after_select is True)
            if after_select:
                # Skip single chars (like 'w'), punctuation, and aggregation functions
                if len(clean) > 1 and clean not in (',',) and clean.upper() not in ('DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'AS'):
                    columns.add(clean)

    except Exception as e:
        log.warning("SQL parsing failed: %s", e)

    # Extract CTE names to filter out later
    cte_names = set()
    for match in re.finditer(r'WITH\s+(\w+)\s+AS', sql, re.IGNORECASE):
        cte_names.add(match.group(1).lower())
    
    # Remove CTE names from tables
    tables = {t for t in tables if t.lower() not in cte_names}

    # Fallback: regex-based extraction
    # Extract FROM/JOIN table names, handling brackets and schemas
    # Matches: FROM Table, FROM [Table], FROM dbo.Table, FROM [dbo].[Table]
    for match in re.finditer(r'(?:FROM|JOIN)\s+((?:\[[^\]]+\]|[\w\.]+))', sql, re.IGNORECASE):
        full_name = match.group(1).strip()
        # Handle [dbo].[Table] or dbo.Table or [Table]
        # Split by dot and remove brackets from each part
        parts = [p.strip('[]') for p in full_name.split('.')]
        table = parts[-1] # Take the last part as the table name for validation
        # Skip if it's a CTE name
        if table and table.upper() not in ('SELECT', 'WHERE') and table.lower() not in cte_names:
            tables.add(table)

    return list(tables), list(columns)


# ── Validator Agent ──────────────────────────────────────────────────────

class ValidatorAgent:
    """
    Validates SQL queries and executes with self-healing.
    
    Validation pipeline:
      1. Security check (forbidden keywords/patterns)
      2. Schema check (INFORMATION_SCHEMA validation)
      3. Execution (catch runtime errors)
      4. Self-heal on failure (re-prompt SQL Agent with error context)
    """

    def __init__(self, sql_agent: SQLAgent):
        self._sql_agent = sql_agent

    def validate_sql(self, sql: str) -> ValidationResult:
        """
        Validate SQL for security and schema correctness.
        Does NOT execute the query.
        """
        errors = []

        # ── 1. Security Check ────────────────────────────────────────────
        security_passed = True
        sql_upper = sql.upper().strip()

        # Must start with SELECT or WITH
        if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
            security_passed = False
            errors.append("Query must start with SELECT or WITH")

        # Forbidden keywords
        for kw in FORBIDDEN_KEYWORDS:
            if re.search(rf'\b{kw}\b', sql_upper):
                security_passed = False
                errors.append(f"Forbidden keyword detected: {kw}")

        # Forbidden patterns
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in sql:
                security_passed = False
                errors.append(f"Forbidden pattern detected: '{pattern}'")

        # ── 2. Schema Check ──────────────────────────────────────────────
        schema_passed = True
        invalid_columns = []
        invalid_tables = []

        tables, columns = extract_identifiers(sql)
        tables = [t.replace('dbo.', '') for t in tables]
        
        # ── ANTI-HALLUCINATION: BM25 Schema Check ──
        bm25_ok = True
        bm25_errors = []
        
        try:
            bm25 = _get_bm25_index()
            valid_tables_bm25 = set()
            
            for doc in bm25._documents:
                valid_tables_bm25.add(doc['tableName'].lower())
            
            for tbl in tables:
                tbl_lower = tbl.lower()
                if tbl_lower not in valid_tables_bm25:
                    bm25_ok = False
                    bm25_errors.append(f"Table '{tbl}' not in schema")
                            
        except Exception as e:
            log.warning(f"BM25 validation failed: {e}")
        
        # ── Database Schema Check ──
        db_invalid_tables = []
        db_invalid_columns = []
        if sql_client.is_connected and (tables or columns):
            validation = sql_client.validate_identifiers(
                columns=list(columns), tables=tables
            )
            db_invalid_tables = validation.get("invalid_tables", [])
            db_invalid_columns = validation.get("invalid_columns", [])
        
        # ── COMBINE: Either BM25 or DB validation fails = FAIL ──
        all_invalid_tables = list(set(bm25_errors + db_invalid_tables))
        all_invalid_columns = db_invalid_columns
        
        if not bm25_ok or db_invalid_tables:
            schema_passed = False
            errors.append(f"Invalid tables: {', '.join(all_invalid_tables)}")
            invalid_tables = all_invalid_tables
        
        if all_invalid_columns:
            schema_passed = False
            errors.append(f"Invalid columns: {', '.join(all_invalid_columns)}")
            invalid_columns = all_invalid_columns

        return ValidationResult(
            is_valid=security_passed and schema_passed,
            security_passed=security_passed,
            schema_passed=schema_passed,
            invalid_columns=invalid_columns,
            invalid_tables=invalid_tables,
            errors=errors,
        )

    def validate_and_execute(
        self,
        sql: str,
        schema_context: str,
        original_question: str,
        query_type: str = "single_table",
    ) -> ExecutionResult:
        """
        Validate, execute, and self-heal SQL queries.
        
        Self-healing loop (upto MAX_HEAL_RETRIES):
          - If validation fails -> re-prompt with validation errors
          - If execution fails -> re-prompt with SQL Server error
        """
        # Auto-fix: strip dbo. prefix from SQL
        import re
        current_sql = re.sub(r'\[?dbo\]\.?', '', sql, flags=re.IGNORECASE)
        
        heal_attempts = 0
        max_retries = settings.MAX_HEAL_RETRIES

        for attempt in range(max_retries + 1):
            # ── Validate ─────────────────────────────────────────────────
            validation = self.validate_sql(current_sql)

            if not validation.is_valid:
                if attempt < max_retries:
                    log.warning("Validation failed (attempt %d/%d): %s",
                               attempt + 1, max_retries, validation.errors)
                    # Self-heal: re-generate with error context
                    error_context = (
                        f"The previous SQL query was invalid. Errors: "
                        f"{'; '.join(validation.errors)}. "
                        f"Invalid tables: {validation.invalid_tables}. "
                        f"Please fix the query using ONLY the provided schema."
                    )
                    heal_result = self._sql_agent(
                        neo4j_schema_context=schema_context + f"\n\nERROR CONTEXT: {error_context}",
                        user_question=original_question,
                        query_type=query_type,
                    )
                    current_sql = heal_result.sql_query
                    heal_attempts += 1
                    continue
                else:
                    return ExecutionResult(
                        sql_query=current_sql,
                        error=f"Validation failed after {max_retries} retries: "
                              f"{'; '.join(validation.errors)}",
                        heal_attempts=heal_attempts,
                        validation=validation,
                    )

            # ── Execute ──────────────────────────────────────────────────
            if not sql_client.is_connected:
                return ExecutionResult(
                    sql_query=current_sql,
                    error="SQL Server not connected",
                    validation=validation,
                )

            result = sql_client.execute_query(current_sql)

            if result.get("error"):
                if attempt < max_retries:
                    log.warning("SQL execution failed (attempt %d/%d): %s",
                               attempt + 1, max_retries, result["error"])
                    # Self-heal: re-generate with execution error
                    heal_result = self._sql_agent(
                        neo4j_schema_context=(
                            schema_context +
                            f"\n\nPREVIOUS SQL ERROR: {result['error']}\n"
                            f"FAILED SQL: {current_sql}\n"
                            f"Fix the query. Use ONLY columns from the schema above."
                        ),
                        user_question=original_question,
                        query_type=query_type,
                    )
                    current_sql = heal_result.sql_query
                    heal_attempts += 1
                    continue
                else:
                    return ExecutionResult(
                        sql_query=current_sql,
                        error=f"Execution failed after {max_retries} retries: "
                              f"{result['error']}",
                        heal_attempts=heal_attempts,
                        validation=validation,
                    )

            # ── Success ──────────────────────────────────────────────────
            return ExecutionResult(
                sql_query=current_sql,
                columns=result["columns"],
                rows=result["rows"],
                total_rows=result["total_rows"],
                truncated=result["truncated"],
                healed=heal_attempts > 0,
                heal_attempts=heal_attempts,
                validation=validation,
            )

        # Should not reach here, but safety net
        return ExecutionResult(
            sql_query=current_sql,
            error="Unexpected: exhausted all attempts",
            heal_attempts=heal_attempts,
        )
