from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyodbc

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import settings


EXPORT_QUERIES: dict[str, str] = {
    "wmr_full.csv": "SELECT * FROM WMR_Full",
    "wmr_latest.csv": "SELECT * FROM WellMonitoringReport",
    "plan_snapshot.csv": "SELECT * FROM Job_Progress_PlanSnapshot",
    "job_progress_report_gb.csv": "SELECT * FROM Job_Progress_Report_GB",
    "sap_drilling_sequence.csv": "SELECT * FROM SAP_DRILLING_SEQUENCE",
}


def export_query(conn: pyodbc.Connection, sql: str, path: Path) -> int:
    df = pd.read_sql_query(sql, conn)
    df.to_csv(path, index=False)
    return len(df)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the Decision Studio Kaggle input package from live SQL Server."
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "inputs"),
        help="Directory where CSV inputs should be written.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "database": settings.SQL_DATABASE,
        "server": settings.SQL_SERVER,
        "files": {},
    }

    with pyodbc.connect(settings.sql_connection_string, timeout=30) as conn:
        for filename, sql in EXPORT_QUERIES.items():
            path = output_dir / filename
            row_count = export_query(conn, sql, path)
            manifest["files"][filename] = {
                "rows": row_count,
                "query": sql,
            }
            print(f"[exported] {filename}: {row_count:,} rows")

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[saved] {manifest_path}")


if __name__ == "__main__":
    main()
