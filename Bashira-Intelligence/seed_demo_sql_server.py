"""
Seed a local SQL Server demo database for Bashira Intelligence.

Purpose:
- create a local database with the same table names the app expects
- load the freshest local extracts where available
- backfill missing tables from the sample_data pack
- create remaining schema-only tables from actual_schema.json so code does not break

Default target database is ATNM_Dev so the existing app config can keep the same
database name and only the SQL server host needs to be switched to local.
"""

from __future__ import annotations

import json
import logging
import os
import urllib
from pathlib import Path

import numpy as np
import pandas as pd
import pyodbc
from sqlalchemy import create_engine


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bashira.seed_demo_sql")


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "actual_schema.json"
SAMPLE_DIR = Path(r"C:\Users\sagar\Downloads\sample_data\sample_data")
KAGGLE_INPUTS = BASE_DIR / "kaggle_decision_studio" / "inputs"
PREDICTION_DATA = BASE_DIR / "prediction_data"

DB_NAME = os.environ.get("DEMO_SQL_DATABASE", "ATNM_Dev")
LOCAL_SERVERS = [
    os.environ.get("DEMO_SQL_SERVER", "").strip(),
    r"localhost\SQLEXPRESS",
    r".\SQLEXPRESS",
    r"(localdb)\MSSQLLocalDB",
    r"localhost",
]
LOCAL_SERVERS = [server for server in LOCAL_SERVERS if server]

REAL_OR_SAMPLE_SOURCES: dict[str, Path] = {
    "ActivityTaskPlan": SAMPLE_DIR / "sample_ActivityTaskPlan.csv",
    "Employee": SAMPLE_DIR / "sample_Employee.csv",
    "Job_Progress_Report_GB": SAMPLE_DIR / "sample_Job_Progress_Report_GB.csv",
    "PH_PRODUCTIVITY_WEEKLY_REPORT": SAMPLE_DIR / "sample_PH_PRODUCTIVITY_WEEKLY_REPORT.csv",
    "ProjectIDs": SAMPLE_DIR / "sample_ProjectIDs.csv",
    "Revenue": SAMPLE_DIR / "sample_Revenue.csv",
    "SAP_DRILLING_SEQUENCE": SAMPLE_DIR / "sample_SAP_DRILLING_SEQUENCE.csv",
    "task_daily": SAMPLE_DIR / "sample_task_daily.csv",
    "WBS_Master_Tracker_": SAMPLE_DIR / "sample_WBS_Master_Tracker_.csv",
    "WellMonitoringReport": SAMPLE_DIR / "sample_WellMonitoringReport.csv",
    "WellMonitoringReport_Staged": SAMPLE_DIR / "sample_WellMonitoringReport_Staged.csv",
    "WMR_Full": SAMPLE_DIR / "sample_WMR_Full.csv",
}

EXTRA_TABLE_SOURCES: dict[str, Path] = {
    "Job_Progress_PlanSnapshot": KAGGLE_INPUTS / "plan_snapshot.csv",
}


TYPE_MAP = {
    "bigint": "BIGINT NULL",
    "int": "INT NULL",
    "tinyint": "TINYINT NULL",
    "float": "FLOAT NULL",
    "decimal": "DECIMAL(18,6) NULL",
    "date": "DATE NULL",
    "datetime": "DATETIME2 NULL",
    "datetime2": "DATETIME2 NULL",
    "bit": "BIT NULL",
    "varchar": "NVARCHAR(MAX) NULL",
    "nvarchar": "NVARCHAR(MAX) NULL",
}


def quote_ident(name: str) -> str:
    return f"[{name.replace(']', ']]')}]"


def load_schema() -> dict[str, list[dict[str, str]]]:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def try_create_database() -> str:
    for server in LOCAL_SERVERS:
        log.info("Attempting local SQL Server: %s", server)
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={server};"
            "DATABASE=master;"
            "Trusted_Connection=yes;"
            "Encrypt=Optional;"
            "TrustServerCertificate=yes;"
        )
        try:
            conn = pyodbc.connect(conn_str, autocommit=True, timeout=5)
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{DB_NAME}'")
            if not cursor.fetchone():
                log.info("Creating local database %s", DB_NAME)
                cursor.execute(f"CREATE DATABASE {quote_ident(DB_NAME)}")
            else:
                log.info("Database %s already exists", DB_NAME)
            conn.close()
            return server
        except Exception as exc:
            log.debug("Connection failed on %s: %s", server, exc)
    raise RuntimeError("Could not reach any local SQL Server instance. Open SSMS and confirm a local instance is running.")


def build_engine(server: str):
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={DB_NAME};"
        "Trusted_Connection=yes;"
        "Encrypt=Optional;"
        "TrustServerCertificate=yes;"
    )
    params = urllib.parse.quote_plus(conn_str)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}", fast_executemany=True)


def read_csv_any(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df.columns = df.columns.astype(str).str.strip()
    return df.replace({np.nan: None})


def create_schema_only_table(conn: pyodbc.Connection, table_name: str, columns: list[dict[str, str]]) -> None:
    cursor = conn.cursor()
    cursor.execute(
        f"""
IF OBJECT_ID(N'dbo.{table_name}', N'U') IS NOT NULL
    DROP TABLE dbo.{quote_ident(table_name)};
"""
    )
    column_sql = []
    for column in columns:
        col_name = quote_ident(column["name"])
        sql_type = TYPE_MAP.get(str(column.get("type", "varchar")).lower(), "NVARCHAR(MAX) NULL")
        column_sql.append(f"{col_name} {sql_type}")
    create_sql = f"CREATE TABLE dbo.{quote_ident(table_name)} ({', '.join(column_sql)});"
    cursor.execute(create_sql)
    conn.commit()
    cursor.close()


def rebuild_wmr_latest_from_main(conn: pyodbc.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
IF OBJECT_ID(N'dbo.[WellMonitoringReport_Latest]', N'U') IS NOT NULL
    DROP TABLE dbo.[WellMonitoringReport_Latest];

SELECT *
INTO dbo.[WellMonitoringReport_Latest]
FROM dbo.[WellMonitoringReport]
WHERE [Week_Number] = (
    SELECT MAX([Week_Number])
    FROM dbo.[WellMonitoringReport]
);
"""
    )
    conn.commit()
    cursor.close()


def seed_database(server: str) -> None:
    schema = load_schema()
    engine = build_engine(server)
    raw_conn = pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={DB_NAME};"
        "Trusted_Connection=yes;"
        "Encrypt=Optional;"
        "TrustServerCertificate=yes;",
        autocommit=False,
        timeout=15,
    )

    imported_tables: list[str] = []
    empty_tables: list[str] = []

    for table_name, columns in schema.items():
        source = REAL_OR_SAMPLE_SOURCES.get(table_name)
        if source and source.exists():
            log.info("Loading %s from %s", table_name, source)
            df = read_csv_any(source)
            df.to_sql(table_name, engine, schema="dbo", if_exists="replace", index=False)
            imported_tables.append(table_name)
        else:
            log.info("Creating empty schema-only table %s", table_name)
            create_schema_only_table(raw_conn, table_name, columns)
            empty_tables.append(table_name)

    for table_name, source in EXTRA_TABLE_SOURCES.items():
        if source.exists():
            log.info("Loading extra table %s from %s", table_name, source)
            df = read_csv_any(source)
            df.to_sql(table_name, engine, schema="dbo", if_exists="replace", index=False)
            if table_name not in imported_tables:
                imported_tables.append(table_name)
            empty_tables = [name for name in empty_tables if name != table_name]

    if "WellMonitoringReport" in imported_tables:
        log.info("Rebuilding WellMonitoringReport_Latest from WellMonitoringReport latest Week_Number")
        rebuild_wmr_latest_from_main(raw_conn)
        if "WellMonitoringReport_Latest" not in imported_tables:
            imported_tables.append("WellMonitoringReport_Latest")
        empty_tables = [name for name in empty_tables if name != "WellMonitoringReport_Latest"]

    raw_conn.close()

    log.info("============================================================")
    log.info("DEMO DATABASE READY")
    log.info("============================================================")
    log.info("Server: %s", server)
    log.info("Database: %s", DB_NAME)
    log.info("Imported tables: %s", ", ".join(imported_tables))
    log.info("Schema-only empty tables: %s", ", ".join(empty_tables))
    print()
    print("Update your .env for tomorrow's local demo:")
    print(f"SQL_SERVER={server}")
    print(f"SQL_DATABASE={DB_NAME}")
    print("SQL_TRUSTED_CONNECTION=True")
    print("SQL_USER=")
    print("SQL_PASSWORD=")


def main() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Missing schema file: {SCHEMA_PATH}")
    if not SAMPLE_DIR.exists():
        raise FileNotFoundError(f"Missing sample data directory: {SAMPLE_DIR}")

    server = try_create_database()
    seed_database(server)


if __name__ == "__main__":
    main()
