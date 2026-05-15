"""
Embed Column Descriptions into Neo4j using MiniLM
==================================================
1. Loads the all-MiniLM-L6-v2 model locally (384-dim vectors).
2. Reads columns_updated.csv and batch-encodes all descriptions.
3. Creates a Neo4j native vector index (384 dims, cosine).
4. Pushes embeddings to existing Column nodes via UNWIND.
"""

import csv
import os
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

# ── Credentials (same as seed_neo4j.py) ──────────────────────────────────────
URI      = "neo4j+s://4ba6a45a.databases.neo4j.io"
USERNAME = "4ba6a45a"
PASSWORD = "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s"
DATABASE = "4ba6a45a"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    # ── 1. Load MiniLM locally ───────────────────────────────────────────
    print("Loading MiniLM model (all-MiniLM-L6-v2)...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("   OK: Model loaded (384-dim embeddings)")

    # ── 2. Connect to Neo4j ──────────────────────────────────────────────
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("OK: Connected to Neo4j Aura")

    with driver.session(database=DATABASE) as session:

        # ── 3. Create Vector Index ───────────────────────────────────────
        print("\n[1] Creating vector index (384 dims, cosine)...")
        try:
            session.run("""
                CREATE VECTOR INDEX column_embeddings IF NOT EXISTS
                FOR (c:Column) ON (c.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 384,
                    `vector.similarity_function`: 'cosine'
                }}
            """)
            print("   OK: Vector index 'column_embeddings' created/verified")
        except Exception as e:
            print(f"   WARN: Vector index: {e}")

        # ── 4. Read CSV and batch-encode ─────────────────────────────────
        print("\n[2] Reading columns_clean.csv...")
        csv_path = os.path.join(BASE_DIR, "columns_atnm_dev.csv")
        columns_data = []
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                columns_data.append({
                    'columnName': row['columnName'].strip(),
                    'tableName':  row['tableName'].strip(),
                    'description': row['description'].strip(),
                })
        print(f"   OK: {len(columns_data)} column descriptions loaded")

        # Batch encode all descriptions in one call (optimized for CPU/GPU)
        print("\n[3] Generating MiniLM embeddings (batch)...")
        descriptions = [col['description'] for col in columns_data]
        embeddings = embedding_model.encode(descriptions, show_progress_bar=True).tolist()

        # Attach embeddings to data payload
        for i, col in enumerate(columns_data):
            col['embedding'] = embeddings[i]
        print(f"   OK: {len(embeddings)} embeddings generated (384-dim each)")

        # ── 5. Push embeddings to Neo4j ──────────────────────────────────
        print("\n[4] Pushing embeddings to Neo4j Column nodes...")
        push_query = """
            UNWIND $data AS row
            MATCH (t:Table {name: row.tableName})-[:HAS_COLUMN]->(c:Column {name: row.columnName})
            SET c.embedding = row.embedding
        """
        session.run(push_query, data=columns_data)
        print("   OK: All embeddings stored on Column nodes")

        # ── 6. Verify ────────────────────────────────────────────────────
        print("\n[5] Verification...")
        result = session.run("""
            MATCH (c:Column)
            WHERE c.embedding IS NOT NULL
            RETURN count(c) AS embedded_count
        """)
        count = result.single()["embedded_count"]
        print(f"   OK: {count} Column nodes now have embeddings")

    driver.close()
    print("\n[OK] Embedding ingestion complete!")


if __name__ == "__main__":
    main()
