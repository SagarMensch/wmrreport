import os
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def explore_neo4j():
    print("=== NEO4J AURA EXPLORATION ===")
    uri = os.getenv("NEO4J_URI", "neo4j+s://4ba6a45a.databases.neo4j.io")
    user = os.getenv("NEO4J_USER", "4ba6a45a")
    pw = os.getenv("NEO4J_PASSWORD", "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, pw))
        driver.verify_connectivity()
        
        with driver.session() as session:
            # Get Node Counts
            print("\nNode Counts:")
            res = session.run("MATCH (n) RETURN labels(n) AS Label, count(n) AS Count")
            for record in res:
                print(f"  - {record['Label']}: {record['Count']}")
                
            # Get Relationships
            print("\nRelationships:")
            res = session.run("MATCH (n)-[r]->(m) RETURN type(r) AS Type, count(r) AS Count")
            for record in res:
                print(f"  - {record['Type']}: {record['Count']}")
        driver.close()
    except Exception as e:
        print("Neo4j Error:", e)


def explore_supabase():
    print("\n=== SUPABASE EXPLORATION ===")
    uri = os.getenv("SUPABASE_DB_URI", "postgresql://neondb_owner:npg_NkUoV0R6IgDY@ep-lingering-dawn-apl8j3xh-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require")
    
    try:
        engine = create_engine(uri)
        with engine.connect() as conn:
            print("\nTables in 'public' schema:")
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            for row in result:
                print(f"  - {row[0]}")
    except Exception as e:
        print("Supabase Error:", e)

if __name__ == "__main__":
    explore_neo4j()
    explore_supabase()
