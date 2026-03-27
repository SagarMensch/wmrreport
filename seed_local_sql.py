"""
Seed Local Microsoft SQL Server with Sample CSVs
================================================
This script reads the 14 sample CSV files and loads them directly into your
local Microsoft SQL Server (the same one you access via SSMS).

It creates a database called 'AppMasterDB' and builds all the tables automatically.
This perfectly mimics the production environment so you can test the pipeline locally.

Run with: python seed_local_sql.py
"""

import os
import urllib
import logging
import pandas as pd
import pyodbc
from sqlalchemy import create_engine
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ── Configuration ────────────────────────────────────────────────────────

CSV_DIR = r"C:\Users\sagar\Downloads\sample_data\sample_data"
DB_NAME = "AppMasterDB"

# Standard local SQL Server instances (SSMS defaults)
LOCAL_SERVERS = [
    r"localhost\SQLEXPRESS",
    r".\SQLEXPRESS",
    r"localhost",
    r"(localdb)\MSSQLLocalDB"
]

CSV_FILES = [
    "sample_ActivityTaskPlan.csv",
    "sample_Employee.csv",
    "sample_Job_Progress_Report_GB.csv",
    "sample_PH_PRODUCTIVITY_WEEKLY_REPORT.csv",
    "sample_ProjectIDs.csv",
    "sample_Revenue.csv",
    "sample_SAP_DRILLING_SEQUENCE.csv",
    "sample_task_daily.csv",
    "sample_WBS_Master_Tracker_.csv",
    "sample_WellMonitoringReport.csv",
    "sample_WellMonitoringReport_Latest.csv",
    "sample_WellMonitoringReport_Staged.csv",
    "sample_WMR_Full.csv",
    "schema_metadata.csv"
]

def try_create_database() -> str | None:
    """Find a working local SQL Server and create the AppMasterDB database."""
    working_server = None
    
    for server in LOCAL_SERVERS:
        logging.info(f"Attempting to connect to local MS SQL Server: {server}")
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={server};"
            "DATABASE=master;"
            "Trusted_Connection=yes;"
            "Encrypt=Optional;"
            "TrustServerCertificate=yes;"
        )
        try:
            # Must connect with autocommit=True to run CREATE DATABASE
            conn = pyodbc.connect(conn_str, autocommit=True, timeout=3)
            cursor = conn.cursor()
            
            # Check if AppMasterDB exists
            cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{DB_NAME}'")
            if not cursor.fetchone():
                logging.info(f"Database '{DB_NAME}' not found. Creating it now...")
                cursor.execute(f"CREATE DATABASE {DB_NAME}")
                logging.info(f"✓ Created database '{DB_NAME}' successfully.")
            else:
                logging.info(f"✓ Database '{DB_NAME}' already exists.")
                
            conn.close()
            working_server = server
            break
            
        except Exception as e:
            logging.debug(f"Failed to connect to {server}: {e}")
            continue
            
    return working_server


def load_csvs_to_sql(server: str):
    """Load all 14 CSV files into AppMasterDB using SQLAlchemy."""
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={DB_NAME};"
        "Trusted_Connection=yes;"
        "Encrypt=Optional;"
        "TrustServerCertificate=yes;"
    )
    
    params = urllib.parse.quote_plus(conn_str)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", fast_executemany=True)
    
    logging.info(f"\nConnected to MS SQL Server: {server} -> {DB_NAME}")
    logging.info("Starting data import...\n")
    
    for filename in CSV_FILES:
        filepath = os.path.join(CSV_DIR, filename)
        if not os.path.exists(filepath):
            logging.warning(f"File not found: {filepath}")
            continue
            
        # Clean table name
        table_name = filename.replace("sample_", "").replace(".csv", "")
        
        logging.info(f"Processing '{filename}' -> Table '{table_name}'")
        try:
            # Read CSV
            df = pd.read_csv(filepath)
            
            # Clean column names
            df.columns = df.columns.astype(str).str.strip()
            
            # Replace NaN with None for SQL NULL
            df = df.replace({np.nan: None})
            
            # Write to MS SQL Server
            # if_exists="replace" will DROP the table if it exists and CREATE a new one
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            logging.info(f"  ✓ Imported {len(df)} rows into '{table_name}'")
            
        except Exception as e:
            logging.error(f"  ✗ Failed to import {filename}: {e}")

    logging.info("\n" + "=" * 60)
    logging.info("IMPORT COMPLETE")
    logging.info("=" * 60)
    print(f"\nAll data is now available in SSMS under Server: '{server}' Database: '{DB_NAME}'")


def main():
    print("=" * 60)
    print("  SEEDING LOCAL MICROSOFT SQL SERVER")
    print("  Creating AppMasterDB and importing all 14 CSV tables")
    print("=" * 60)
    
    server = try_create_database()
    
    if not server:
        logging.error("Could not reach any local Microsoft SQL Server instance.")
        logging.info("Please ensure SQL Server is running locally (check Services -> SQL Server).")
        return
        
    load_csvs_to_sql(server)
    
    print("\n" + "=" * 60)
    print("  UPDATE YOUR .ENV FILE TO USE LOCAL DB")
    print("=" * 60)
    print("Open your .env file and change the connection settings to:")
    print()
    print(f"SQL_SERVER={server}")
    print(f"SQL_DATABASE={DB_NAME}")
    print("SQL_USERNAME=")
    print("SQL_PASSWORD=")
    print("SQL_TRUSTED_CONNECTION=True")
    print()
    print("Once you do this, the pipeline will test perfectly!")


if __name__ == "__main__":
    main()
