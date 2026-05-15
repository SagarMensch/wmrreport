"""
Complete Neo4j Seeding - Full Schema + Embeddings
1. Creates Table nodes
2. Creates Column nodes with business descriptions
3. Adds MiniLM embeddings to columns
4. Creates JOIN relationships
"""
import csv
import os
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

URI = "neo4j+s://4ba6a45a.databases.neo4j.io"
USERNAME = "4ba6a45a"
PASSWORD = "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s"
DATABASE = "4ba6a45a"

# Join relationships
JOINS = [
    ("WellMonitoringReport", "pdo_well_id", "WMR_Full", "pdo_well_id", "MIRRORS"),
    ("WellMonitoringReport", "pdo_well_id", "WellMonitoringReport_Latest", "pdo_well_id", "MIRRORS"),
    ("WellMonitoringReport", "well_name_after_spud", "SAP_DRILLING_SEQUENCE", "Well_Name", "HAS_SAP"),
    ("WellMonitoringReport", "pdo_well_id", "Job_Progress_Report_GB", "Well ID", "HAS_JOB_PROGRESS"),
    ("WellMonitoringReport", "pdo_well_id", "Revenue", "well_id", "HAS_REVENUE"),
    ("WellMonitoringReport", "rig_no", "crews", "Code", "ASSIGNED_CREW"),
]

def main():
    print("="*60)
    print("FULL NEO4J SEEDING WITH EMBEDDINGS")
    print("="*60)
    
    # Load CSV
    print("\n[1] Loading CSV...")
    csv_path = "columns_atnm_dev.csv"
    columns_data = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('columnName') and row.get('tableName'):
                columns_data.append({
                    'columnName': row['columnName'].strip(),
                    'tableName': row['tableName'].strip(),
                    'description': row.get('description', '').strip() or f"{row['tableName']} - {row['columnName']}",
                    'dataType': row.get('dataType', '').strip()
                })
    print(f"   Loaded {len(columns_data)} columns")
    
    # Get unique tables
    tables = list(set(c['tableName'] for c in columns_data))
    print(f"   {len(tables)} unique tables")
    
    # Load MiniLM
    print("\n[2] Loading MiniLM...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("   OK: Model loaded")
    
    # Connect to Neo4j
    print("\n[3] Connecting to Neo4j...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("   Connected!")
    
    with driver.session(database=DATABASE) as session:
        # Clear
        print("\n[4] Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create Table nodes
        print("\n[5] Creating Table nodes...")
        for table in tables:
            desc = f"Table: {table}"
            session.run("MERGE (t:Table {name: $name}) SET t.description = $desc", name=table, desc=desc)
        print(f"   Created {len(tables)} tables")
        
        # Create Column nodes with embeddings
        print("\n[6] Creating Column nodes with embeddings...")
        batch_size = 50
        total = len(columns_data)
        
        for i in range(0, total, batch_size):
            batch = columns_data[i:i+batch_size]
            
            # Generate embeddings
            descs = [c['description'] for c in batch]
            embeddings = embedding_model.encode(descs, show_progress_bar=False).tolist()
            
            # Create nodes with embeddings
            for j, col in enumerate(batch):
                session.run("""
                    MERGE (c:Column {name: $name, tableName: $table})
                    SET c.description = $desc,
                        c.dataType = $dtype,
                        c.embedding = $emb
                """, 
                    name=col['columnName'],
                    table=col['tableName'],
                    desc=col['description'],
                    dtype=col['dataType'],
                    emb=embeddings[j]
                )
                
                # Link to table
                session.run("""
                    MATCH (c:Column {name: $name, tableName: $table})
                    MATCH (t:Table {name: $table})
                    MERGE (t)-[:HAS_COLUMN]->(c)
                """, name=col['columnName'], table=col['tableName'])
            
            print(f"   Processed {min(i+batch_size, total)}/{total}")
        
        # Create Well hub
        print("\n[7] Creating Well hub...")
        session.run("MERGE (w:Well {wellId: '__MASTER__'})")
        
        # Link well tables to Well hub
        well_tables = ["WellMonitoringReport", "WellMonitoringReport_Latest", "WMR_Full"]
        for table in well_tables:
            session.run("""
                MATCH (t:Table {name: $table})
                MATCH (w:Well {wellId: '__MASTER__'})
                MERGE (t)-[:REFERENCES_WELL {via: 'pdo_well_id'}]->(w)
            """, table=table)
        
        # Create JOIN relationships
        print("\n[8] Creating JOIN relationships...")
        for src_table, src_col, tgt_table, tgt_col, rel_type in JOINS:
            session.run(f"""
                MATCH (a:Table {{name: $src}})
                MATCH (b:Table {{name: $tgt}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.srcColumn = $src_col, r.tgtColumn = $tgt_col
            """, src=src_table, tgt=tgt_table, src_col=src_col, tgt_col=tgt_col)
        print(f"   Created {len(JOINS)} relationships")
        
        # Verify
        print("\n[9] Verification...")
        result = session.run("MATCH (c:Column) WHERE c.embedding IS NOT NULL RETURN count(c) as cnt")
        emb_count = result.single()['cnt']
        print(f"   Columns with embeddings: {emb_count}")
        
        result = session.run("MATCH (a)-[r]->(b) RETURN type(r) as rel, count(*) as cnt")
        print("   Relationships:")
        for record in result:
            print(f"      {record['rel']}: {record['cnt']}")
    
    driver.close()
    print("\n" + "="*60)
    print("DONE! Full schema with embeddings seeded.")
    print("="*60)

if __name__ == "__main__":
    main()
