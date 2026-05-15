import pandas as pd
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

conn_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={os.getenv('SQL_SERVER')};DATABASE={os.getenv('SQL_DATABASE')};Trusted_Connection=yes;"
try:
    conn = pyodbc.connect(conn_string, timeout=5)
    df = pd.read_sql("SELECT count(*) as total_rows, count(distinct pdo_well_id) as total_wells FROM WMR_Full", conn)
    print(df)
    
except Exception as e:
    print(f"Error: {e}")
