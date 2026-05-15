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

CSV_DIR = r"C:\Users\sagar\Downloads\Bashira-Intelligence (2)\Bashira-Intelligence\prediction_data"
DB_NAME = "AppMasterDB"

# Standard local SQL Server instances (SSMS defaults)
LOCAL_SERVERS = [
    r"localhost\SQLEXPRESS",
    r".\SQLEXPRESS",
    r"localhost",
    r"(localdb)\MSSQLLocalDB"
]

CSV_FILES = [
    "ag_predictions.csv",
    "job_progress_gb.csv",
    "ph_productivity.csv",
    "risk_scores.csv",
    "survival_predictions.csv",
    "wmr_full_history.csv",
    "wmr_latest.csv"
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
            
        table_mapping = {
            "ag_predictions.csv": "Ag_Predictions",
            "job_progress_gb.csv": "Job_Progress_Report_GB",
            "ph_productivity.csv": "PH_PRODUCTIVITY_WEEKLY_REPORT",
            "risk_scores.csv": "Risk_Scores",
            "survival_predictions.csv": "Survival_Predictions",
            "wmr_full_history.csv": "WMR_Full",
            "wmr_latest.csv": "WellMonitoringReport_Latest"
        }
        
        table_name = table_mapping.get(filename, filename.replace(".csv", ""))
        
        logging.info(f"Processing '{filename}' -> Table '{table_name}'")
        try:
            # Read CSV
            df = pd.read_csv(filepath, low_memory=False)
            
            # Clean column names
            df.columns = df.columns.astype(str).str.strip()
            
            # Specialized date conversions for WMR_Full so SQL Server doesn't reject them
            if table_name == "WMR_Full":
                for col in ["Week_Number", "engineering_actual_start_date", "actual_start_date", "actual_rig_on_date", "actual_rig_off_date", "exp.rig_off_location_sap_data", "flaf_issue_date", "date_-_material_available_at_site"]:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
            
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
