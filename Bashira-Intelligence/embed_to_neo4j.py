"""
Embed Column Descriptions into Neo4j - Fixed Version
Loads MiniLM, generates embeddings for all columns in Neo4j
"""
import csv
import os
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

URI = "neo4j+s://4ba6a45a.databases.neo4j.io"
USERNAME = "4ba6a45a"
PASSWORD = "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s"
DATABASE = "4ba6a45a"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    print("Loading MiniLM model...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("   OK: Model loaded")

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("OK: Connected to Neo4j")

    with driver.session(database=DATABASE) as session:
        print("\n[1] Getting all columns from Neo4j...")
        result = session.run("""
            MATCH (c:Column)
            RETURN c.name AS name, c.tableName AS tableName, c.description AS description
        """)
        columns = list(result)
        print(f"   Found {len(columns)} columns in Neo4j")

        print("\n[2] Generating embeddings...")
        batch_size = 50
        total = len(columns)
        
        for i in range(0, total, batch_size):
            batch = columns[i:i+batch_size]
            descriptions = []
            for col in batch:
                desc = col.get('description', '') or ''
                name = col.get('name', '') or ''
                text = f"{name} {desc}"
                descriptions.append(text)
            
            embeddings = embedding_model.encode(descriptions, show_progress_bar=False).tolist()
            
            for j, col in enumerate(batch):
                session.run("""
                    MATCH (c:Column {name: $name, tableName: $tableName})
                    SET c.embedding = $embedding
                """, 
                name=col['name'], 
                tableName=col['tableName'], 
                embedding=embeddings[j])
            
            print(f"   Processed {min(i+batch_size, total)}/{total}")
        
        print("\n[3] Verifying embeddings...")
        result = session.run("""
            MATCH (c:Column)
            WHERE c.embedding IS NOT NULL
            RETURN count(c) AS cnt
        """)
        emb_count = result.single()['cnt']
        print(f"   Columns with embeddings: {emb_count}")

    driver.close()
    print("\n[OK] Embedding update complete!")

if __name__ == "__main__":
    main()
