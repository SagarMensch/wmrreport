import csv
import datetime
import io
import logging
import threading
import time
from typing import Any

from database.sql_client import sql_client

log = logging.getLogger("bashira.data_integrity")


RULES: dict[str, dict[str, Any]] = {
    "TD01": {
        "code": "TD-01",
        "name": "Required Quantity Exceeded",
        "source": "task_daily",
        "source_label": "Task Daily",
        "severity": "high",
        "category": "Quantity logic",
        "summary": "Linked daily records where required quantity is greater than recorded data quantity.",
        "expected": "Recorded data quantity should not be lower than the required quantity on a linked daily capture row.",
        "recommendation": "Review the daily quantity capture and confirm whether required or data_qty is incorrect.",
        "client_rule": "Task_daily | If for a particular action_on, URL is available check required is more than data_qty.",
        "technical_logic": "url is present and TRY_CAST(required AS FLOAT) > TRY_CAST(data_qty AS FLOAT).",
    },
    "TD02": {
        "code": "TD-02",
        "name": "Daily Execution Fields Missing",
        "source": "task_daily",
        "source_label": "Task Daily",
        "severity": "critical",
        "category": "Missing data",
        "summary": "Linked daily records missing quantity, employee, equipment, hours, or PH name values.",
        "expected": "Linked daily capture rows should contain quantity, employees, equipment, hours, and PH name with no negative numeric values.",
        "recommendation": "Complete the missing operational capture fields before the row is used downstream.",
        "client_rule": "Task_daily | If for a particular action_on, URL is available check data_qty, data_employee, data_equipment, data_hours, Data_ph_name are available and none are negative.",
        "technical_logic": "url is present and one or more of data_qty, data_employees, daily_equipment_ids, data_hours, or daily_ph_name is blank, null, or negative where numeric.",
    },
    "TD03": {
        "code": "TD-03",
        "name": "Completed Without Actual End",
        "source": "task_daily",
        "source_label": "Task Daily",
        "severity": "critical",
        "category": "Completion logic",
        "summary": "Linked daily rows marked completed in task_daily.completed without an actual end date.",
        "expected": "If task_daily.completed is true on a linked daily row, actual_end must be populated.",
        "recommendation": "Backfill actual_end or correct the populated completed flag on the live task_daily row.",
        "client_rule": "Task_daily | If for a particular action_on, URL is available check is Data_completed = true and actual_end available.",
        "technical_logic": "url is present, TRY_CAST(completed AS INT) = 1, and actual_end is null.",
    },
    "ATP01": {
        "code": "ATP-01",
        "name": "Actual Duration Exceeds Target",
        "source": "ActivityTaskPlan",
        "source_label": "Activity Task Plan",
        "severity": "medium",
        "category": "Date logic",
        "summary": "Planned tasks where actual duration is longer than target duration.",
        "expected": "Actual duration should not exceed the target duration for the same task code.",
        "recommendation": "Validate target dates, actual dates, and whether the task is legitimately delayed.",
        "client_rule": "Task_plan | If for a particular code, is the count of days between actual_start and actual_end more than target_start and target_end.",
        "technical_logic": "DATEDIFF(DAY, actual_start, actual_end) > DATEDIFF(DAY, target_start, target_end).",
    },
    "ATP02": {
        "code": "ATP-02",
        "name": "Actual Quantity Exceeds Forecast",
        "source": "ActivityTaskPlan",
        "source_label": "Activity Task Plan",
        "severity": "medium",
        "category": "Quantity logic",
        "summary": "Planned tasks where actual quantity is greater than forecast quantity.",
        "expected": "Actual quantity should not exceed forecast quantity without an approved business reason.",
        "recommendation": "Review task quantity capture and confirm whether the forecast or actual quantity is incorrect.",
        "client_rule": "Task_plan | If for a particular code, is the qtyactual more than qtyforacst.",
        "technical_logic": "TRY_CAST(qtyactual AS FLOAT) > TRY_CAST(qtyforacst AS FLOAT).",
    },
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "clear": 4}


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


class DataIntegrityService:
    def __init__(self) -> None:
        self._cache: dict[str, Any] | None = None
        self._cache_built_at = 0.0
        self._lock = threading.Lock()
        self._ttl_seconds = 120

    def _resolve_task_daily_context(self) -> dict[str, Any]:
        query = """
        SELECT
            COUNT(*) AS total_rows,
            SUM(CASE WHEN NULLIF(LTRIM(RTRIM([url])), '') IS NOT NULL THEN 1 ELSE 0 END) AS url_linked_rows,
            SUM(
                CASE
                    WHEN [ActionOn] IS NOT NULL
                     AND NULLIF(LTRIM(RTRIM(CAST([task_code] AS NVARCHAR(MAX)))), '') IS NOT NULL
                     AND NULLIF(LTRIM(RTRIM(CAST([project_id] AS NVARCHAR(MAX)))), '') IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS operational_rows
        FROM task_daily
        """
        result = sql_client.execute_query(query, max_rows=5)
        rows = result.get("rows", [])
        row = rows[0] if rows else [0, 0, 0]
        total_rows = int(row[0] or 0)
        url_linked_rows = int(row[1] or 0)
        operational_rows = int(row[2] or 0)
        fallback_active = url_linked_rows == 0 and operational_rows > 0

        if fallback_active:
            return {
                "mode": "sample_operational",
                "label": "Local sample operational mode",
                "note": (
                    "No URL-linked task_daily rows exist in the local export, so "
                    "task_daily rules are evaluated on operational rows with "
                    "ActionOn, task_code, and project_id."
                ),
                "basis_label": "Operational task_daily rows",
                "basis_detail": "ActionOn + task_code + project_id",
                "link_filter_sql": (
                    "[ActionOn] IS NOT NULL "
                    "AND NULLIF(LTRIM(RTRIM(CAST([task_code] AS NVARCHAR(MAX)))), '') IS NOT NULL "
                    "AND NULLIF(LTRIM(RTRIM(CAST([project_id] AS NVARCHAR(MAX)))), '') IS NOT NULL"
                ),
                "total_rows": total_rows,
                "applicable_rows": operational_rows,
                "url_linked_rows": url_linked_rows,
                "operational_rows": operational_rows,
                "fallback_active": True,
            }

        return {
            "mode": "url_linked",
            "label": "URL-linked client mode",
            "note": (
                "Task_daily rules are evaluated only on rows with a populated URL, "
                "matching the client rule wording."
            ),
            "basis_label": "URL-linked task_daily rows",
            "basis_detail": "Populated url",
            "link_filter_sql": "NULLIF(LTRIM(RTRIM([url])), '') IS NOT NULL",
            "total_rows": total_rows,
            "applicable_rows": url_linked_rows,
            "url_linked_rows": url_linked_rows,
            "operational_rows": operational_rows,
            "fallback_active": False,
        }

    def build_workspace(self, force_refresh: bool = False) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            if (
                not force_refresh
                and self._cache is not None
                and (now - self._cache_built_at) < self._ttl_seconds
            ):
                return self._with_cache_age(self._cache, now - self._cache_built_at)

            sql_client.connect()
            generated_at = datetime.datetime.now().isoformat()

            table_scope = self._fetch_table_scope()
            task_daily_context = self._resolve_task_daily_context()
            rule_counts = self._fetch_rule_counts(task_daily_context)
            exceptions = self._fetch_exceptions(task_daily_context)

            payload = {
                "generated_at": generated_at,
                "workspace_name": "Data Integrity",
                "objective": "Live exception checks on operational execution data.",
                "summary": self._build_summary(table_scope, rule_counts),
                "source_cards": self._build_source_cards(rule_counts, table_scope),
                "rule_cards": self._build_rule_cards(rule_counts, task_daily_context),
                "rule_views": self._build_rule_views(rule_counts),
                "exceptions": exceptions,
                "primary_focus": self._build_primary_focus(rule_counts),
                "table_scope": table_scope,
                "activation_context": {
                    "task_daily": {
                        key: value
                        for key, value in task_daily_context.items()
                        if key != "link_filter_sql"
                    }
                },
            }
            self._cache = payload
            self._cache_built_at = now
            return self._with_cache_age(payload, 0)

    def _with_cache_age(self, payload: dict[str, Any], cache_age_seconds: float) -> dict[str, Any]:
        cloned = dict(payload)
        cloned["cache_age_seconds"] = int(cache_age_seconds)
        return cloned

    def _fetch_table_scope(self) -> dict[str, Any]:
        query = """
        SELECT 'task_daily' AS source_table, COUNT(*) AS row_count
        FROM task_daily
        UNION ALL
        SELECT 'ActivityTaskPlan' AS source_table, COUNT(*) AS row_count
        FROM ActivityTaskPlan
        """
        result = sql_client.execute_query(query, max_rows=10)
        scope: dict[str, Any] = {
            "task_daily": {"source": "task_daily", "label": "Task Daily", "row_count": 0},
            "ActivityTaskPlan": {
                "source": "ActivityTaskPlan",
                "label": "Activity Task Plan",
                "row_count": 0,
            },
        }
        for row in result.get("rows", []):
            scope[row[0]]["row_count"] = int(row[1])
        return scope

    def _fetch_rule_counts(self, task_daily_context: dict[str, Any]) -> dict[str, int]:
        task_daily_filter = task_daily_context["link_filter_sql"]
        query = f"""
        SELECT 'TD01' AS rule_code, COUNT(*) AS exception_count
        FROM task_daily
        WHERE {task_daily_filter}
          AND TRY_CAST([required] AS FLOAT) > TRY_CAST([data_qty] AS FLOAT)
        UNION ALL
        SELECT 'TD02', COUNT(*)
        FROM task_daily
        WHERE {task_daily_filter}
          AND (
                [data_qty] IS NULL OR TRY_CAST([data_qty] AS FLOAT) < 0 OR
                NULLIF(LTRIM(RTRIM(CAST([data_employees] AS NVARCHAR(MAX)))), '') IS NULL OR TRY_CAST([data_employees] AS FLOAT) < 0 OR
                NULLIF(LTRIM(RTRIM(CAST([daily_equipment_ids] AS NVARCHAR(MAX)))), '') IS NULL OR
                [data_hours] IS NULL OR TRY_CAST([data_hours] AS FLOAT) < 0 OR
                NULLIF(LTRIM(RTRIM(CAST([daily_ph_name] AS NVARCHAR(MAX)))), '') IS NULL
              )
        UNION ALL
        SELECT 'TD03', COUNT(*)
        FROM task_daily
        WHERE {task_daily_filter}
          AND TRY_CAST([completed] AS INT) = 1
          AND [actual_end] IS NULL
        UNION ALL
        SELECT 'ATP01', COUNT(*)
        FROM ActivityTaskPlan
        WHERE [actual_start] IS NOT NULL AND [actual_end] IS NOT NULL
          AND [target_start] IS NOT NULL AND [target_end] IS NOT NULL
          AND DATEDIFF(DAY, [actual_start], [actual_end]) > DATEDIFF(DAY, [target_start], [target_end])
        UNION ALL
        SELECT 'ATP02', COUNT(*)
        FROM ActivityTaskPlan
        WHERE TRY_CAST([qtyactual] AS FLOAT) > TRY_CAST([qtyforacst] AS FLOAT)
        """
        result = sql_client.execute_query(query, max_rows=20)
        counts = {code: 0 for code in RULES}
        for row in result.get("rows", []):
            counts[row[0]] = int(row[1])
        return counts

    def _fetch_exceptions(self, task_daily_context: dict[str, Any]) -> list[dict[str, Any]]:
        exceptions: list[dict[str, Any]] = []
        exceptions.extend(self._fetch_td01(task_daily_context))
        exceptions.extend(self._fetch_td02(task_daily_context))
        exceptions.extend(self._fetch_td03(task_daily_context))
        exceptions.extend(self._fetch_atp01())
        exceptions.extend(self._fetch_atp02())
        exceptions.sort(
            key=lambda item: (
                SEVERITY_ORDER.get(item["severity"], 9),
                item.get("record_date") or "",
            ),
            reverse=False,
        )
        return exceptions[:200]

    def _normalize_rule_id(self, rule_id: str) -> str:
        normalized = str(rule_id or "").upper().replace("-", "").strip()
        if normalized not in RULES:
            raise ValueError(f"Unsupported rule id: {rule_id}")
        return normalized

    def _safe_date(self, value: str | None) -> str | None:
        if not value:
            return None
        return datetime.date.fromisoformat(str(value)[:10]).isoformat()

    def _rule_view_definition(self, rule_id: str, task_daily_context: dict[str, Any]) -> dict[str, Any]:
        task_daily_filter = task_daily_context["link_filter_sql"]
        task_daily_basis = (
            f"{task_daily_context['basis_label']} "
            f"({task_daily_context['basis_detail']})"
        )
        if rule_id == "TD01":
            return {
                "columns": ["id", "ActionOn", "task_code", "well_id", "project_id", "required", "data_qty", "shortfall_qty", "url"],
                "select_sql": """
SELECT
    [id],
    [ActionOn],
    [task_code],
    [well_id],
    [project_id],
    [required],
    [data_qty],
    TRY_CAST([required] AS FLOAT) - TRY_CAST([data_qty] AS FLOAT) AS shortfall_qty,
    [url]
FROM task_daily
                """,
                "where_sql": f"""
{task_daily_filter}
AND TRY_CAST([required] AS FLOAT) > TRY_CAST([data_qty] AS FLOAT)
                """,
                "order_sql": "[ActionOn] DESC, shortfall_qty DESC, [id] DESC",
                "date_column": "[ActionOn]",
                "date_field_label": "ActionOn",
                "note": "This view shows linked daily rows where required quantity is greater than the recorded quantity on the same captured row.",
                "evaluation_basis": task_daily_basis,
            }
        if rule_id == "TD02":
            return {
                "columns": ["id", "ActionOn", "task_code", "well_id", "project_id", "data_qty", "data_employees", "daily_equipment_ids", "data_hours", "daily_ph_name", "url"],
                "select_sql": """
SELECT
    [id],
    [ActionOn],
    [task_code],
    [well_id],
    [project_id],
    [data_qty],
    [data_employees],
    [daily_equipment_ids],
    [data_hours],
    [daily_ph_name],
    [url]
FROM task_daily
                """,
                "where_sql": f"""
{task_daily_filter}
AND (
      [data_qty] IS NULL OR TRY_CAST([data_qty] AS FLOAT) < 0 OR
      NULLIF(LTRIM(RTRIM(CAST([data_employees] AS NVARCHAR(MAX)))), '') IS NULL OR TRY_CAST([data_employees] AS FLOAT) < 0 OR
      NULLIF(LTRIM(RTRIM(CAST([daily_equipment_ids] AS NVARCHAR(MAX)))), '') IS NULL OR
      [data_hours] IS NULL OR TRY_CAST([data_hours] AS FLOAT) < 0 OR
      NULLIF(LTRIM(RTRIM(CAST([daily_ph_name] AS NVARCHAR(MAX)))), '') IS NULL
    )
                """,
                "order_sql": "[ActionOn] DESC, [id] DESC",
                "date_column": "[ActionOn]",
                "date_field_label": "ActionOn",
                "note": "This view isolates linked daily captures where one or more required execution fields are blank or numerically invalid.",
                "evaluation_basis": task_daily_basis,
            }
        if rule_id == "TD03":
            return {
                "columns": ["id", "ActionOn", "task_code", "well_id", "project_id", "completed", "actual_end", "url"],
                "select_sql": """
SELECT
    [id],
    [ActionOn],
    [task_code],
    [well_id],
    [project_id],
    [completed],
    [actual_end],
    [url]
FROM task_daily
                """,
                "where_sql": f"""
{task_daily_filter}
AND TRY_CAST([completed] AS INT) = 1
AND [actual_end] IS NULL
                """,
                "order_sql": "[ActionOn] DESC, [id] DESC",
                "date_column": "[ActionOn]",
                "date_field_label": "ActionOn",
                "note": "This view uses task_daily.completed as the active completion flag because daily_completed is not populated in the live table.",
                "evaluation_basis": task_daily_basis,
            }
        if rule_id == "ATP01":
            return {
                "columns": ["row_id", "code", "Well_ID", "project_id", "target_start", "target_end", "actual_start", "actual_end", "target_days", "actual_days", "variance_days"],
                "select_sql": """
SELECT
    [row_id],
    [code],
    [Well_ID],
    [project_id],
    [target_start],
    [target_end],
    [actual_start],
    [actual_end],
    DATEDIFF(DAY, [target_start], [target_end]) AS target_days,
    DATEDIFF(DAY, [actual_start], [actual_end]) AS actual_days,
    DATEDIFF(DAY, [actual_start], [actual_end]) - DATEDIFF(DAY, [target_start], [target_end]) AS variance_days
FROM ActivityTaskPlan
                """,
                "where_sql": """
[actual_start] IS NOT NULL AND [actual_end] IS NOT NULL
AND [target_start] IS NOT NULL AND [target_end] IS NOT NULL
AND DATEDIFF(DAY, [actual_start], [actual_end]) > DATEDIFF(DAY, [target_start], [target_end])
                """,
                "order_sql": "variance_days DESC, [updated_at] DESC",
                "date_column": "[actual_end]",
                "date_field_label": "actual_end",
                "note": "This view shows plan rows where actual task duration is longer than the original target duration for the same code.",
                "evaluation_basis": "ActivityTaskPlan rows with populated actual and target dates",
            }
        if rule_id == "ATP02":
            return {
                "columns": ["row_id", "code", "Well_ID", "project_id", "updated_at", "qtyforacst", "qtyactual", "qty_delta"],
                "select_sql": """
SELECT
    [row_id],
    [code],
    [Well_ID],
    [project_id],
    [updated_at],
    [qtyforacst],
    [qtyactual],
    TRY_CAST([qtyactual] AS FLOAT) - TRY_CAST([qtyforacst] AS FLOAT) AS qty_delta
FROM ActivityTaskPlan
                """,
                "where_sql": """
TRY_CAST([qtyactual] AS FLOAT) > TRY_CAST([qtyforacst] AS FLOAT)
                """,
                "order_sql": "qty_delta DESC, [updated_at] DESC",
                "date_column": "[updated_at]",
                "date_field_label": "updated_at",
                "note": "This view surfaces plan rows where actual quantity is higher than forecast quantity for the same task code.",
                "evaluation_basis": "ActivityTaskPlan rows with comparable qtyactual and qtyforacst",
            }
        raise ValueError(f"Unsupported rule id: {rule_id}")

    def _rule_view_failed_fields(self, rule_id: str, values: dict[str, Any]) -> list[str]:
        if rule_id == "TD01":
            return ["required", "data_qty", "shortfall_qty"]
        if rule_id == "TD03":
            return ["completed", "actual_end"]
        if rule_id == "ATP01":
            return ["target_start", "target_end", "actual_start", "actual_end", "variance_days"]
        if rule_id == "ATP02":
            return ["qtyforacst", "qtyactual", "qty_delta"]
        if rule_id == "TD02":
            failed_fields: list[str] = []
            data_qty = _to_float(values.get("data_qty"))
            data_employees = _to_float(values.get("data_employees"))
            data_hours = _to_float(values.get("data_hours"))
            if data_qty is None or data_qty < 0:
                failed_fields.append("data_qty")
            if _blank(values.get("data_employees")) or (data_employees is not None and data_employees < 0):
                failed_fields.append("data_employees")
            if _blank(values.get("daily_equipment_ids")):
                failed_fields.append("daily_equipment_ids")
            if data_hours is None or data_hours < 0:
                failed_fields.append("data_hours")
            if _blank(values.get("daily_ph_name")):
                failed_fields.append("daily_ph_name")
            return failed_fields
        return []

    def _build_rule_date_clause(self, date_column: str | None, date_from: str | None, date_to: str | None) -> str:
        if not date_column:
            return ""
        clauses: list[str] = []
        if date_from:
            clauses.append(f"CAST({date_column} AS DATE) >= '{date_from}'")
        if date_to:
            clauses.append(f"CAST({date_column} AS DATE) <= '{date_to}'")
        if not clauses:
            return ""
        return " AND " + " AND ".join(clauses)

    def _single_value(self, sql: str) -> Any:
        result = sql_client.execute_query(sql, max_rows=5)
        rows = result.get("rows", [])
        if not rows:
            return None
        return rows[0][0] if rows[0] else None

    def fetch_rule_view(
        self,
        rule_id: str,
        page: int = 1,
        page_size: int = 60,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        normalized_rule = self._normalize_rule_id(rule_id)
        page = max(1, int(page or 1))
        page_size = max(1, min(int(page_size or 60), 500))
        parsed_date_from = self._safe_date(date_from) if date_from else None
        parsed_date_to = self._safe_date(date_to) if date_to else None

        task_daily_context = self._resolve_task_daily_context()
        definition = self._rule_view_definition(normalized_rule, task_daily_context)
        where_sql = definition["where_sql"].strip()
        date_column = definition.get("date_column")
        date_clause = self._build_rule_date_clause(
            date_column,
            parsed_date_from,
            parsed_date_to,
        )

        base_total_sql = f"""
SELECT COUNT(*)
FROM ({definition["select_sql"].strip()}) AS base
WHERE {where_sql};
        """
        filtered_total_sql = f"""
SELECT COUNT(*)
FROM ({definition["select_sql"].strip()}) AS base
WHERE {where_sql}{date_clause};
        """
        available_range = {"min": None, "max": None}
        if date_column:
            range_sql = f"""
SELECT
    CONVERT(varchar(10), MIN(CAST({date_column} AS DATE)), 23) AS min_date,
    CONVERT(varchar(10), MAX(CAST({date_column} AS DATE)), 23) AS max_date
FROM ({definition["select_sql"].strip()}) AS base
WHERE {where_sql};
            """
            range_result = sql_client.execute_query(range_sql, max_rows=5)
            range_rows = range_result.get("rows", [])
            if range_rows:
                available_range = {"min": range_rows[0][0], "max": range_rows[0][1]}

        base_total = int(self._single_value(base_total_sql) or 0)
        filtered_total = int(self._single_value(filtered_total_sql) or 0)
        offset = max(0, (page - 1) * page_size)
        if filtered_total and offset >= filtered_total:
            page = max(1, ((filtered_total - 1) // page_size) + 1)
            offset = max(0, (page - 1) * page_size)

        paged_sql = f"""
{definition["select_sql"].strip()}
WHERE {where_sql}{date_clause}
ORDER BY {definition["order_sql"]}
OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY;
        """
        result = sql_client.execute_query(paged_sql, max_rows=page_size + 5)
        rows = []
        for row in result.get("rows", []):
            values = dict(zip(definition["columns"], row))
            rows.append(
                {
                    "values": values,
                    "failed_fields": self._rule_view_failed_fields(normalized_rule, values),
                }
            )

        page_start = offset + 1 if filtered_total else 0
        page_end = offset + len(rows)
        meta = RULES[normalized_rule]
        return {
            "id": normalized_rule,
            "rule_code": meta["code"],
            "title": meta["name"],
            "source": meta["source"],
            "source_label": meta["source_label"],
            "severity": "clear" if filtered_total == 0 else meta["severity"],
            "client_rule": meta["client_rule"],
            "technical_logic": meta["technical_logic"],
            "evaluation_basis": definition.get("evaluation_basis"),
            "expected": meta["expected"],
            "recommendation": meta["recommendation"],
            "base_total_violations": base_total,
            "total_violations": filtered_total,
            "showing_rows": len(rows),
            "page": page,
            "page_size": page_size,
            "page_start": page_start,
            "page_end": page_end,
            "has_prev_page": page > 1,
            "has_next_page": page_end < filtered_total,
            "date_field": definition.get("date_field_label"),
            "available_date_range": available_range,
            "date_from": parsed_date_from,
            "date_to": parsed_date_to,
            "sql": paged_sql.strip(),
            "columns": definition["columns"],
            "rows": rows,
            "note": definition["note"],
        }

    def export_rule_view_csv(
        self,
        rule_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> str:
        normalized_rule = self._normalize_rule_id(rule_id)
        parsed_date_from = self._safe_date(date_from) if date_from else None
        parsed_date_to = self._safe_date(date_to) if date_to else None
        definition = self._rule_view_definition(
            normalized_rule,
            self._resolve_task_daily_context(),
        )
        where_sql = definition["where_sql"].strip()
        date_clause = self._build_rule_date_clause(
            definition.get("date_column"),
            parsed_date_from,
            parsed_date_to,
        )
        export_sql = f"""
{definition["select_sql"].strip()}
WHERE {where_sql}{date_clause}
ORDER BY {definition["order_sql"]};
        """
        result = sql_client.execute_query(export_sql, max_rows=50000)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(definition["columns"])
        for row in result.get("rows", []):
            writer.writerow(["" if value is None else value for value in row])
        return buffer.getvalue()

    def _build_rule_views(self, rule_counts: dict[str, int]) -> dict[str, Any]:
        return {
            rule_id: self.fetch_rule_view(rule_id, page=1, page_size=60)
            for rule_id in RULES
        }


    def _rule_view_shell(
        self,
        rule_id: str,
        total_violations: int,
        sql: str,
        columns: list[str],
        rows: list[dict[str, Any]],
        note: str,
    ) -> dict[str, Any]:
        meta = RULES[rule_id]
        return {
            "id": rule_id,
            "rule_code": meta["code"],
            "title": meta["name"],
            "source": meta["source"],
            "source_label": meta["source_label"],
            "severity": "clear" if total_violations == 0 else meta["severity"],
            "client_rule": meta["client_rule"],
            "technical_logic": meta["technical_logic"],
            "expected": meta["expected"],
            "recommendation": meta["recommendation"],
            "total_violations": total_violations,
            "showing_rows": len(rows),
            "sql": sql.strip(),
            "columns": columns,
            "rows": rows,
            "note": note,
        }

    def _fetch_rule_view_td01(self, total_violations: int) -> dict[str, Any]:
        sql = """
SELECT TOP 60
    [id],
    [ActionOn],
    [task_code],
    [well_id],
    [project_id],
    [required],
    [data_qty],
    TRY_CAST([required] AS FLOAT) - TRY_CAST([data_qty] AS FLOAT) AS shortfall_qty,
    [url]
FROM task_daily
WHERE NULLIF(LTRIM(RTRIM([url])), '') IS NOT NULL
  AND TRY_CAST([required] AS FLOAT) > TRY_CAST([data_qty] AS FLOAT)
ORDER BY [ActionOn] DESC, shortfall_qty DESC;
        """
        result = sql_client.execute_query(sql, max_rows=80)
        columns = ["id", "ActionOn", "task_code", "well_id", "project_id", "required", "data_qty", "shortfall_qty", "url"]
        rows = []
        for row in result.get("rows", []):
            values = dict(zip(columns, row))
            rows.append({"values": values, "failed_fields": ["required", "data_qty", "shortfall_qty"]})
        return self._rule_view_shell(
            "TD01",
            total_violations,
            sql,
            columns,
            rows,
            "This view shows linked daily rows where required quantity is greater than the recorded quantity on the same captured row.",
        )

    def _fetch_rule_view_td02(self, total_violations: int) -> dict[str, Any]:
        sql = """
SELECT TOP 60
    [id],
    [ActionOn],
    [task_code],
    [well_id],
    [project_id],
    [data_qty],
    [data_employees],
    [daily_equipment_ids],
    [data_hours],
    [daily_ph_name],
    [url]
FROM task_daily
WHERE NULLIF(LTRIM(RTRIM([url])), '') IS NOT NULL
  AND (
        [data_qty] IS NULL OR TRY_CAST([data_qty] AS FLOAT) < 0 OR
        NULLIF(LTRIM(RTRIM(CAST([data_employees] AS NVARCHAR(MAX)))), '') IS NULL OR TRY_CAST([data_employees] AS FLOAT) < 0 OR
        NULLIF(LTRIM(RTRIM(CAST([daily_equipment_ids] AS NVARCHAR(MAX)))), '') IS NULL OR
        [data_hours] IS NULL OR TRY_CAST([data_hours] AS FLOAT) < 0 OR
        NULLIF(LTRIM(RTRIM(CAST([daily_ph_name] AS NVARCHAR(MAX)))), '') IS NULL
      )
ORDER BY [ActionOn] DESC, [id] DESC;
        """
        result = sql_client.execute_query(sql, max_rows=80)
        columns = ["id", "ActionOn", "task_code", "well_id", "project_id", "data_qty", "data_employees", "daily_equipment_ids", "data_hours", "daily_ph_name", "url"]
        rows = []
        for row in result.get("rows", []):
            values = dict(zip(columns, row))
            failed_fields: list[str] = []
            data_qty = _to_float(values["data_qty"])
            data_employees = _to_float(values["data_employees"])
            data_hours = _to_float(values["data_hours"])
            if data_qty is None or data_qty < 0:
                failed_fields.append("data_qty")
            if _blank(values["data_employees"]) or (data_employees is not None and data_employees < 0):
                failed_fields.append("data_employees")
            if _blank(values["daily_equipment_ids"]):
                failed_fields.append("daily_equipment_ids")
            if data_hours is None or data_hours < 0:
                failed_fields.append("data_hours")
            if _blank(values["daily_ph_name"]):
                failed_fields.append("daily_ph_name")
            rows.append({"values": values, "failed_fields": failed_fields})
        return self._rule_view_shell(
            "TD02",
            total_violations,
            sql,
            columns,
            rows,
            "This view isolates linked daily captures where one or more required execution fields are blank or numerically invalid.",
        )

    def _fetch_rule_view_td03(self, total_violations: int) -> dict[str, Any]:
        sql = """
SELECT TOP 60
    [id],
    [ActionOn],
    [task_code],
    [well_id],
    [project_id],
    [completed],
    [actual_end],
    [url]
FROM task_daily
WHERE NULLIF(LTRIM(RTRIM([url])), '') IS NOT NULL
  AND TRY_CAST([completed] AS INT) = 1
  AND [actual_end] IS NULL
ORDER BY [ActionOn] DESC, [id] DESC;
        """
        result = sql_client.execute_query(sql, max_rows=80)
        columns = ["id", "ActionOn", "task_code", "well_id", "project_id", "completed", "actual_end", "url"]
        rows = []
        for row in result.get("rows", []):
            values = dict(zip(columns, row))
            rows.append({"values": values, "failed_fields": ["completed", "actual_end"]})
        return self._rule_view_shell(
            "TD03",
            total_violations,
            sql,
            columns,
            rows,
            "This view uses task_daily.completed as the active completion flag because daily_completed is not populated in the live table.",
        )

    def _fetch_rule_view_atp01(self, total_violations: int) -> dict[str, Any]:
        sql = """
SELECT TOP 60
    [row_id],
    [code],
    [Well_ID],
    [project_id],
    [target_start],
    [target_end],
    [actual_start],
    [actual_end],
    DATEDIFF(DAY, [target_start], [target_end]) AS target_days,
    DATEDIFF(DAY, [actual_start], [actual_end]) AS actual_days,
    DATEDIFF(DAY, [actual_start], [actual_end]) - DATEDIFF(DAY, [target_start], [target_end]) AS variance_days
FROM ActivityTaskPlan
WHERE [actual_start] IS NOT NULL AND [actual_end] IS NOT NULL
  AND [target_start] IS NOT NULL AND [target_end] IS NOT NULL
  AND DATEDIFF(DAY, [actual_start], [actual_end]) > DATEDIFF(DAY, [target_start], [target_end])
ORDER BY variance_days DESC, [updated_at] DESC;
        """
        result = sql_client.execute_query(sql, max_rows=80)
        columns = ["row_id", "code", "Well_ID", "project_id", "target_start", "target_end", "actual_start", "actual_end", "target_days", "actual_days", "variance_days"]
        rows = []
        for row in result.get("rows", []):
            values = dict(zip(columns, row))
            rows.append({"values": values, "failed_fields": ["target_start", "target_end", "actual_start", "actual_end", "variance_days"]})
        return self._rule_view_shell(
            "ATP01",
            total_violations,
            sql,
            columns,
            rows,
            "This view shows plan rows where actual task duration is longer than the original target duration for the same code.",
        )

    def _fetch_rule_view_atp02(self, total_violations: int) -> dict[str, Any]:
        sql = """
SELECT TOP 60
    [row_id],
    [code],
    [Well_ID],
    [project_id],
    [qtyforacst],
    [qtyactual],
    TRY_CAST([qtyactual] AS FLOAT) - TRY_CAST([qtyforacst] AS FLOAT) AS qty_delta
FROM ActivityTaskPlan
WHERE TRY_CAST([qtyactual] AS FLOAT) > TRY_CAST([qtyforacst] AS FLOAT)
ORDER BY qty_delta DESC, [updated_at] DESC;
        """
        result = sql_client.execute_query(sql, max_rows=80)
        columns = ["row_id", "code", "Well_ID", "project_id", "qtyforacst", "qtyactual", "qty_delta"]
        rows = []
        for row in result.get("rows", []):
            values = dict(zip(columns, row))
            rows.append({"values": values, "failed_fields": ["qtyforacst", "qtyactual", "qty_delta"]})
        return self._rule_view_shell(
            "ATP02",
            total_violations,
            sql,
            columns,
            rows,
            "This view surfaces plan rows where actual quantity is higher than forecast quantity for the same task code.",
        )

    def _fetch_td01(self, task_daily_context: dict[str, Any]) -> list[dict[str, Any]]:
        task_daily_filter = task_daily_context["link_filter_sql"]
        query = f"""
        SELECT TOP 40
            [id],
            [task_code],
            [well_id],
            [project_id],
            [ActionOn],
            [required],
            [data_qty],
            [url]
        FROM task_daily
        WHERE {task_daily_filter}
          AND TRY_CAST([required] AS FLOAT) > TRY_CAST([data_qty] AS FLOAT)
        ORDER BY [ActionOn] DESC, TRY_CAST([required] AS FLOAT) - TRY_CAST([data_qty] AS FLOAT) DESC
        """
        result = sql_client.execute_query(query, max_rows=50)
        items: list[dict[str, Any]] = []
        for row in result.get("rows", []):
            required = _to_float(row[5]) or 0.0
            data_qty = _to_float(row[6]) or 0.0
            gap = required - data_qty
            items.append(
                self._build_exception(
                    rule_code="TD01",
                    key=str(row[1]),
                    record_id=f"task_daily:{row[0]}",
                    record_date=row[4],
                    title="Required quantity is greater than recorded quantity",
                    summary=f"{gap:.2f} quantity units are still unaccounted for on this linked daily row.",
                    failed_fields=["required", "data_qty"],
                    values={
                        "row_id": row[0],
                        "task_code": row[1],
                        "well_id": row[2],
                        "project_id": row[3],
                        "action_on": row[4],
                        "required": row[5],
                        "data_qty": row[6],
                    },
                    action_url=row[7],
                )
            )
        return items

    def _fetch_td02(self, task_daily_context: dict[str, Any]) -> list[dict[str, Any]]:
        task_daily_filter = task_daily_context["link_filter_sql"]
        query = f"""
        SELECT TOP 60
            [id],
            [task_code],
            [well_id],
            [project_id],
            [ActionOn],
            [data_qty],
            [data_employees],
            [daily_equipment_ids],
            [data_hours],
            [daily_ph_name],
            [url]
        FROM task_daily
        WHERE {task_daily_filter}
          AND (
                [data_qty] IS NULL OR TRY_CAST([data_qty] AS FLOAT) < 0 OR
                NULLIF(LTRIM(RTRIM(CAST([data_employees] AS NVARCHAR(MAX)))), '') IS NULL OR TRY_CAST([data_employees] AS FLOAT) < 0 OR
                NULLIF(LTRIM(RTRIM(CAST([daily_equipment_ids] AS NVARCHAR(MAX)))), '') IS NULL OR
                [data_hours] IS NULL OR TRY_CAST([data_hours] AS FLOAT) < 0 OR
                NULLIF(LTRIM(RTRIM(CAST([daily_ph_name] AS NVARCHAR(MAX)))), '') IS NULL
              )
        ORDER BY [ActionOn] DESC, [id] DESC
        """
        result = sql_client.execute_query(query, max_rows=80)
        items: list[dict[str, Any]] = []
        for row in result.get("rows", []):
            failed_fields: list[str] = []
            data_qty = _to_float(row[5])
            data_employees_num = _to_float(row[6])
            data_hours = _to_float(row[8])
            if data_qty is None or data_qty < 0:
                failed_fields.append("data_qty")
            if _blank(row[6]) or (data_employees_num is not None and data_employees_num < 0):
                failed_fields.append("data_employees")
            if _blank(row[7]):
                failed_fields.append("daily_equipment_ids")
            if data_hours is None or data_hours < 0:
                failed_fields.append("data_hours")
            if _blank(row[9]):
                failed_fields.append("daily_ph_name")
            items.append(
                self._build_exception(
                    rule_code="TD02",
                    key=str(row[1]),
                    record_id=f"task_daily:{row[0]}",
                    record_date=row[4],
                    title="Linked daily row is missing required execution capture",
                    summary=f"Missing or invalid fields: {', '.join(failed_fields)}.",
                    failed_fields=failed_fields,
                    values={
                        "row_id": row[0],
                        "task_code": row[1],
                        "well_id": row[2],
                        "project_id": row[3],
                        "action_on": row[4],
                        "data_qty": row[5],
                        "data_employees": row[6],
                        "daily_equipment_ids": row[7],
                        "data_hours": row[8],
                        "daily_ph_name": row[9],
                    },
                    action_url=row[10],
                )
            )
        return items

    def _fetch_td03(self, task_daily_context: dict[str, Any]) -> list[dict[str, Any]]:
        task_daily_filter = task_daily_context["link_filter_sql"]
        query = f"""
        SELECT TOP 40
            [id],
            [task_code],
            [well_id],
            [project_id],
            [ActionOn],
            [completed],
            [actual_end],
            [url]
        FROM task_daily
        WHERE {task_daily_filter}
          AND TRY_CAST([completed] AS INT) = 1
          AND [actual_end] IS NULL
        ORDER BY [ActionOn] DESC, [id] DESC
        """
        result = sql_client.execute_query(query, max_rows=50)
        items: list[dict[str, Any]] = []
        for row in result.get("rows", []):
            items.append(
                self._build_exception(
                    rule_code="TD03",
                    key=str(row[1]),
                    record_id=f"task_daily:{row[0]}",
                    record_date=row[4],
                    title="Completed daily row is missing actual end",
                    summary="The row is marked completed in task_daily.completed, but actual_end is not populated.",
                    failed_fields=["completed", "actual_end"],
                    values={
                        "row_id": row[0],
                        "task_code": row[1],
                        "well_id": row[2],
                        "project_id": row[3],
                        "action_on": row[4],
                        "completed": row[5],
                        "actual_end": row[6],
                    },
                    action_url=row[7],
                )
            )
        return items

    def _fetch_atp01(self) -> list[dict[str, Any]]:
        query = """
        SELECT TOP 40
            [row_id],
            [code],
            [Well_ID],
            [project_id],
            [actual_start],
            [actual_end],
            [target_start],
            [target_end],
            DATEDIFF(DAY, [target_start], [target_end]) AS target_days,
            DATEDIFF(DAY, [actual_start], [actual_end]) AS actual_days
        FROM ActivityTaskPlan
        WHERE [actual_start] IS NOT NULL AND [actual_end] IS NOT NULL
          AND [target_start] IS NOT NULL AND [target_end] IS NOT NULL
          AND DATEDIFF(DAY, [actual_start], [actual_end]) > DATEDIFF(DAY, [target_start], [target_end])
        ORDER BY DATEDIFF(DAY, [actual_start], [actual_end]) - DATEDIFF(DAY, [target_start], [target_end]) DESC, [updated_at] DESC
        """
        result = sql_client.execute_query(query, max_rows=50)
        items: list[dict[str, Any]] = []
        for row in result.get("rows", []):
            target_days = int(row[8] or 0)
            actual_days = int(row[9] or 0)
            variance = actual_days - target_days
            items.append(
                self._build_exception(
                    rule_code="ATP01",
                    key=str(row[1]),
                    record_id=f"ActivityTaskPlan:{row[0]}",
                    record_date=row[5],
                    title="Actual duration is longer than target duration",
                    summary=f"Actual duration is {variance} day(s) longer than target.",
                    failed_fields=["actual_start", "actual_end", "target_start", "target_end"],
                    values={
                        "row_id": row[0],
                        "code": row[1],
                        "well_id": row[2],
                        "project_id": row[3],
                        "actual_start": row[4],
                        "actual_end": row[5],
                        "target_start": row[6],
                        "target_end": row[7],
                        "target_days": target_days,
                        "actual_days": actual_days,
                    },
                )
            )
        return items

    def _fetch_atp02(self) -> list[dict[str, Any]]:
        query = """
        SELECT TOP 40
            [row_id],
            [code],
            [Well_ID],
            [project_id],
            [qtyactual],
            [qtyforacst]
        FROM ActivityTaskPlan
        WHERE TRY_CAST([qtyactual] AS FLOAT) > TRY_CAST([qtyforacst] AS FLOAT)
        ORDER BY TRY_CAST([qtyactual] AS FLOAT) - TRY_CAST([qtyforacst] AS FLOAT) DESC, [updated_at] DESC
        """
        result = sql_client.execute_query(query, max_rows=50)
        items: list[dict[str, Any]] = []
        for row in result.get("rows", []):
            qtyactual = _to_float(row[4]) or 0.0
            qtyforacst = _to_float(row[5]) or 0.0
            items.append(
                self._build_exception(
                    rule_code="ATP02",
                    key=str(row[1]),
                    record_id=f"ActivityTaskPlan:{row[0]}",
                    record_date=None,
                    title="Actual quantity is greater than forecast quantity",
                    summary=f"Actual quantity exceeds forecast by {qtyactual - qtyforacst:.2f}.",
                    failed_fields=["qtyactual", "qtyforacst"],
                    values={
                        "row_id": row[0],
                        "code": row[1],
                        "well_id": row[2],
                        "project_id": row[3],
                        "qtyactual": row[4],
                        "qtyforacst": row[5],
                    },
                )
            )
        return items

    def _build_summary(self, table_scope: dict[str, Any], rule_counts: dict[str, int]) -> dict[str, Any]:
        open_exceptions = sum(rule_counts.values())
        missing_data = rule_counts["TD02"] + rule_counts["TD03"]
        logic_violations = rule_counts["TD01"] + rule_counts["ATP01"] + rule_counts["ATP02"]
        return {
            "open_exceptions": open_exceptions,
            "critical": rule_counts["TD02"] + rule_counts["TD03"],
            "missing_data": missing_data,
            "logic_violations": logic_violations,
            "task_daily_rows": table_scope["task_daily"]["row_count"],
            "activity_task_plan_rows": table_scope["ActivityTaskPlan"]["row_count"],
        }

    def _build_source_cards(self, rule_counts: dict[str, int], table_scope: dict[str, Any]) -> list[dict[str, Any]]:
        task_daily_hits = rule_counts["TD01"] + rule_counts["TD02"] + rule_counts["TD03"]
        atp_hits = rule_counts["ATP01"] + rule_counts["ATP02"]
        return [
            {
                "id": "all",
                "label": "All Sources",
                "exception_count": task_daily_hits + atp_hits,
                "row_count": table_scope["task_daily"]["row_count"] + table_scope["ActivityTaskPlan"]["row_count"],
            },
            {
                "id": "task_daily",
                "label": "Task Daily",
                "exception_count": task_daily_hits,
                "row_count": table_scope["task_daily"]["row_count"],
            },
            {
                "id": "ActivityTaskPlan",
                "label": "Activity Task Plan",
                "exception_count": atp_hits,
                "row_count": table_scope["ActivityTaskPlan"]["row_count"],
            },
        ]

    def _build_rule_cards(
        self,
        rule_counts: dict[str, int],
        task_daily_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        cards = []
        for rule_key, meta in RULES.items():
            count = rule_counts[rule_key]
            if meta["source"] == "task_daily":
                evaluation_basis = (
                    f"{task_daily_context['basis_label']} | "
                    f"{task_daily_context['applicable_rows']:,} applicable rows"
                )
            elif rule_key == "ATP01":
                evaluation_basis = "Actual and target date pairs on ActivityTaskPlan"
            else:
                evaluation_basis = "Comparable quantity pairs on ActivityTaskPlan"
            cards.append(
                {
                    "id": rule_key,
                    "rule_code": meta["code"],
                    "title": meta["name"],
                    "source": meta["source"],
                    "source_label": meta["source_label"],
                    "severity": "clear" if count == 0 else meta["severity"],
                    "category": meta["category"],
                    "summary": meta["summary"],
                    "exception_count": count,
                    "status_label": "Clear" if count == 0 else "Open",
                    "evaluation_basis": evaluation_basis,
                }
            )
        return cards

    def _build_primary_focus(self, rule_counts: dict[str, int]) -> dict[str, Any]:
        worst_rule = max(RULES, key=lambda key: rule_counts.get(key, 0))
        meta = RULES[worst_rule]
        return {
            "rule": meta["code"],
            "title": meta["name"],
            "source_label": meta["source_label"],
            "severity": meta["severity"] if rule_counts.get(worst_rule, 0) else "clear",
            "exception_count": rule_counts.get(worst_rule, 0),
            "message": (
                f"Primary pressure is {meta['name'].lower()} in {meta['source_label']}: "
                f"{rule_counts.get(worst_rule, 0):,} live rows currently fail this rule."
            ),
        }

    def _build_exception(
        self,
        rule_code: str,
        key: str,
        record_id: str,
        record_date: Any,
        title: str,
        summary: str,
        failed_fields: list[str],
        values: dict[str, Any],
        action_url: str | None = None,
    ) -> dict[str, Any]:
        meta = RULES[rule_code]
        return {
            "id": f"{rule_code}:{record_id}",
            "rule_id": rule_code,
            "rule_code": meta["code"],
            "rule_title": meta["name"],
            "source": meta["source"],
            "source_label": meta["source_label"],
            "severity": meta["severity"],
            "category": meta["category"],
            "key": key,
            "record_id": record_id,
            "record_date": record_date,
            "title": title,
            "summary": summary,
            "failed_fields": failed_fields,
            "expected": meta["expected"],
            "recommendation": meta["recommendation"],
            "values": values,
            "action_url": action_url,
        }
