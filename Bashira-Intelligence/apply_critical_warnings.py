"""
Apply Critical Warnings to Neo4j
================================
Incremental update - adds warnings to existing columns without deleting data.
"""

import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from neo4j import GraphDatabase

URI = "neo4j+s://4ba6a45a.databases.neo4j.io"
AUTH = ("4ba6a45a", "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s")

CRITICAL_UPDATES = {
    ("Revenue", "rigcode"): {
        "warning": "CRITICAL: This is RIG CODE (NL0010, NF0010), NOT geographic location! Use Revenue.rigcode for rig filtering, NOT well_location",
        "is_critical": True,
        "valid_rig_codes": "NL0010, NF0010, ML0010, MS0010, MF0010, MCOF10, MCWF10, MROP10, MRWF10, NCOF10, NNSW10, NS0010",
        "usage": "Filter by rig using WHERE rigcode = 'NL0010' - NEVER use well_location for this"
    },
    ("Revenue", "planned_progress"): {
        "warning": "CRITICAL: NVARCHAR - must CAST before comparison: TRY_CAST(planned_progress AS DECIMAL(10,2))",
        "data_type_issue": True
    },
    ("Revenue", "planned_purpose_value"): {
        "warning": "CRITICAL: NVARCHAR - must CAST before SUM: TRY_CCAST(planned_purpose_value AS DECIMAL(18,2))",
        "data_type_issue": True
    },
    ("WellMonitoringReport", "well_location"): {
        "warning": "Geographic location - NOT for rig codes! Use Revenue.rigcode for NL0010/NF0010"
    },
    ("WellMonitoringReport", "pdo_well_id"): {
        "is_primary_join_key": True,
        "join_targets": "Revenue.Well_ID, SAP_DRILLING_SEQUENCE.Well_ID, Job_Progress_Report_GB.[Well ID], Job_Progress_PlanSnapshot.Well_ID"
    },
    ("Revenue", "well_id"): {
        "join_to": "WellMonitoringReport.pdo_well_id",
        "is_join_key": True
    },
    ("SAP_DRILLING_SEQUENCE", "Well_ID"): {
        "join_to": "WellMonitoringReport.pdo_well_id",
        "is_join_key": True
    },
    ("Job_Progress_Report_GB", "Well ID"): {
        "join_to": "WellMonitoringReport.pdo_well_id",
        "is_join_key": True,
        "note": "Column name has space - use [Well ID]"
    },
    ("WellMonitoringReport", "Cluster"): {
        "valid_values": "Nimr, Marmul",
        "usage": "Filter by operational cluster: WHERE Cluster = 'Nimr'"
    }
}


def main():
    print(f"Connecting to {URI}...")
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    with driver.session() as session:
        # Check current state
        result = session.run("MATCH (c:Column) RETURN count(c) as count")
        count = result.single()["count"]
        print(f"Current columns in Neo4j: {count}")
        
        # Apply updates
        for (table, col), props in CRITICAL_UPDATES.items():
            # Build SET clause dynamically
            set_parts = []
            params = {"table": table, "col": col}
            
            for key, val in props.items():
                set_parts.append(f"c.{key} = ${key}")
                params[key] = val
            
            query = f"""
            MATCH (c:Column {{tableName: $table, name: $col}})
            SET {', '.join(set_parts)}
            RETURN c.name as updated
            """
            
            result = session.run(query, **params)
            updated = result.single()
            if updated:
                print(f"  [OK] Updated {table}.{col}")
            else:
                print(f"  [NOT FOUND] {table}.{col}")
        
        # Add indexes for critical columns
        print("\nEnsuring indexes...")
        session.run("CREATE INDEX IF NOT EXISTS FOR (c:Column) ON (c.table_name, c.name)")
        
    driver.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
