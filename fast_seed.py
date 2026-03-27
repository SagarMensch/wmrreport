"""
FAST Neo4j Seeding - Batch operations
"""
import csv
import os
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

URI = "neo4j+s://4ba6a45a.databases.neo4j.io"
USERNAME = "4ba6a45a"
PASSWORD = "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s"
DATABASE = "4ba6a45a"

def main():
    print("FAST NEO4J SEEDING")
    
    # Load CSV
    print("[1] Loading CSV...")
    columns_data = []
    with open('columns_atnm_dev.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('columnName') and row.get('tableName'):
                columns_data.append({
                    'columnName': row['columnName'].strip(),
                    'tableName': row['tableName'].strip(),
                    'description': row.get('description', '').strip() or f"{row['tableName']} - {row['columnName']}",
                })
    print(f"   {len(columns_data)} columns")
    
    # Get unique tables
    tables = list(set(c['tableName'] for c in columns_data))
    print(f"   {len(tables)} tables")
    
    # Load MiniLM
    print("[2] Loading MiniLM...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = embedding_model.encode([c['description'] for c in columns_data], show_progress_bar=True).tolist()
    print(f"   {len(embeddings)} embeddings generated")
    
    # Connect
    print("[3] Connecting to Neo4j...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    print("   Connected")
    
    with driver.session(database=DATABASE) as session:
        # Clear
        print("[4] Clearing...")
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create Table nodes - BATCH
        print("[5] Creating Tables...")
        session.run("""
            UNWIND $tables AS t
            MERGE (table:Table {name: t})
            SET table.description = 'Table: ' + t
        """, tables=tables)
        
        # Add embeddings to columns - BATCH
        print("[6] Creating Columns with Embeddings...")
        for i in range(0, len(columns_data), 100):
            batch = columns_data[i:i+100]
            emb_batch = embeddings[i:i+100]
            
            session.run("""
                UNWIND $data AS d
                MERGE (c:Column {name: d.name, tableName: d.table})
                SET c.description = d.desc, c.embedding = d.emb
            """, data=[
                {'name': c['columnName'], 'table': c['tableName'], 'desc': c['description'], 'emb': emb_batch[j]}
                for j, c in enumerate(batch)
            ])
            print(f"   {min(i+100, len(columns_data))}/{len(columns_data)}")
        
        # Link columns to tables - BATCH
        print("[7] Linking Columns to Tables...")
        session.run("""
            MATCH (c:Column), (t:Table {name: c.tableName})
            MERGE (t)-[:HAS_COLUMN]->(c)
        """)
        
        # Create Well hub
        print("[8] Creating Well hub...")
        session.run("MERGE (w:Well {wellId: '__MASTER__'})")
        
        # Link well tables
        well_tables = ["WellMonitoringReport", "WellMonitoringReport_Latest", "WMR_Full"]
        for table in well_tables:
            session.run("""
                MATCH (t:Table {name: $table})
                MATCH (w:Well {wellId: '__MASTER__'})
                MERGE (t)-[:REFERENCES_WELL {via: 'pdo_well_id'}]->(w)
            """, table=table)
        
        # Create JOINs
        joins = [
            ("WellMonitoringReport", "pdo_well_id", "WMR_Full", "pdo_well_id", "MIRRORS"),
            ("WellMonitoringReport", "pdo_well_id", "WellMonitoringReport_Latest", "pdo_well_id", "MIRRORS"),
            ("WellMonitoringReport", "well_name_after_spud", "SAP_DRILLING_SEQUENCE", "Well_Name", "HAS_SAP"),
            ("WellMonitoringReport", "pdo_well_id", "Job_Progress_Report_GB", "Well ID", "HAS_JOB_PROGRESS"),
            ("WellMonitoringReport", "pdo_well_id", "Revenue", "well_id", "HAS_REVENUE"),
            ("WellMonitoringReport", "rig_no", "crews", "Code", "ASSIGNED_CREW"),
        ]
        
        print("[9] Creating JOINs...")
        for src, src_col, tgt, tgt_col, rel in joins:
            session.run(f"""
                MATCH (a:Table {{name: $src}})
                MATCH (b:Table {{name: $tgt}})
                MERGE (a)-[r:{rel}]->(b)
                SET r.srcColumn = $src_col, r.tgtColumn = $tgt_col
            """, src=src, tgt=tgt, src_col=src_col, tgt_col=tgt_col)
        
        # Verify
        print("[10] Verification...")
        r = session.run("MATCH (c:Column) WHERE c.embedding IS NOT NULL RETURN count(c) as c")
        print(f"   Columns with embeddings: {r.single()['c']}")
        
        r = session.run("MATCH (a)-[r]->(b) RETURN type(r) as t, count(*) as c")
        print("   Relationships:")
        for rec in r:
            print(f"      {rec['t']}: {rec['c']}")
    
    driver.close()
    print("\nDONE!")

if __name__ == "__main__":
    main()
