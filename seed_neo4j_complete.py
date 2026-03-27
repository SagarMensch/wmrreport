"""
Seed Neo4j with Complete AppMasterDB Knowledge
============================================
Uses the comprehensive knowledge base to populate Neo4j.
"""

import json
from neo4j import GraphDatabase

URI = "neo4j+s://4ba6a45a.databases.neo4j.io"
AUTH = ("4ba6a45a", "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s")

# Load knowledge base
with open("appmasterdb_complete_knowledge.json", "r") as f:
    KB = json.load(f)

with open("appmasterdb_bm25_documents.json", "r") as f:
    BM25_DOCS = json.load(f)

def seed():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    with driver.session() as session:
        print("Seeding Neo4j with AppMasterDB knowledge...")
        
        # Create AppMasterDB database node
        session.run("""
            MERGE (db:Database {name: 'AppMasterDB'})
            SET db.description = 'Main operational database containing views for well monitoring, job progress, productivity, and cost tracking'
        """)
        
        # Create View nodes with full knowledge
        for view_name, view_info in KB["views"].items():
            props = {
                "name": f"AppMasterDB.dbo.{view_name}",
                "purpose": view_info["purpose"],
                "source_tables": json.dumps(view_info.get("source_tables", [])),
                "business_logic": json.dumps(view_info.get("business_logic", {})),
                "sql_patterns": json.dumps(view_info.get("sql_patterns", {})),
                "search_text": f"{view_name} {view_info['purpose']} {json.dumps(view_info.get('key_columns', {}))}"
            }
            
            set_parts = [f"v.{k} = ${k}" for k in props.keys()]
            session.run(f"""
                MERGE (v:View {{name: $name}})
                SET {', '.join(set_parts)}
            """, props=props)
            
            # Link to database
            session.run("""
                MATCH (v:View), (db:Database)
                WHERE v.name CONTAINS 'AppMasterDB'
                MERGE (v)-[:IN_DATABASE]->(db)
            """)
            
            print(f"  Created: {view_name}")
        
        # Create Column nodes
        for doc in BM25_DOCS:
            if doc["type"] == "VIEW_COLUMN":
                table = doc["table"].replace("AppMasterDB.dbo.", "")
                props = {
                    "name": doc["column"],
                    "table_name": table,
                    "semantic": doc.get("semantic", ""),
                    "view_purpose": doc.get("view_purpose", ""),
                    "search_text": doc["document"]
                }
                
                set_parts = [f"c.{k} = ${k}" for k in props.keys()]
                session.run(f"""
                    MERGE (c:ViewColumn {{name: $name, table_name: $table_name}})
                    SET {', '.join(set_parts)}
                    WITH c
                    MATCH (v:View {{name: $view}})
                    MERGE (c)-[:IN_VIEW]->(v)
                """, props=props, view=doc["table"])
        
        # Create semantic mapping nodes
        for term, column in KB["semantic_mappings"].items():
            session.run("""
                MERGE (m:SemanticMapping {term: $term})
                SET m.column_hint = $column
            """, term=term, column=column)
        
        print(f"\nTotal BM25 docs indexed: {len(BM25_DOCS)}")
        
        # Verify
        result = session.run("MATCH (v:View) RETURN count(v) as cnt")
        print(f"Views in Neo4j: {result.single()['cnt']}")
        
        result = session.run("MATCH (c:ViewColumn) RETURN count(c) as cnt")
        print(f"ViewColumns in Neo4j: {result.single()['cnt']}")
        
        result = session.run("MATCH (m:SemanticMapping) RETURN count(m) as cnt")
        print(f"Semantic Mappings: {result.single()['cnt']}")
    
    driver.close()
    print("\nNeo4j seeding complete!")

if __name__ == "__main__":
    seed()
