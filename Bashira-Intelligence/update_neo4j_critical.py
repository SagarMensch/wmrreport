"""
Update Neo4j with Critical Warnings - Incremental Update
=======================================================
Updates existing Neo4j data with critical column warnings.
Does NOT delete existing data.
"""

import json

# ============================================================================
# CRITICAL UPDATES - These will be added to existing columns
# ============================================================================

CRITICAL_UPDATES = {
    # Revenue table - rigcode warning
    ("Revenue", "rigcode"): {
        "warning": "CRITICAL: This is RIG CODE (NL0010, NF0010), NOT geographic location! Use Revenue.rigcode for rig filtering, NOT well_location",
        "is_critical": True,
        "valid_rig_codes": ["NL0010", "NF0010", "ML0010", "MS0010", "MF0010", "MCOF10", "MCWF10", "MROP10", "MRWF10", "NCOF10", "NNSW10", "NS0010"],
        "usage": "Filter by rig using WHERE rigcode = 'NL0010' - NEVER use well_location for this!"
    },
    
    # Revenue table - type casting warnings
    ("Revenue", "planned_progress"): {
        "warning": "CRITICAL: This column is NVARCHAR! Must CAST to DECIMAL before comparison: TRY_CAST(planned_progress AS DECIMAL(10,2))",
        "data_type_issue": True
    },
    
    ("Revenue", "planned_purpose_value"): {
        "warning": "CRITICAL: This column is NVARCHAR! Must CAST before SUM: TRY_CAST(planned_purpose_value AS DECIMAL(18,2))",
        "data_type_issue": True
    },
    
    # WellMonitoringReport - location vs rig warning
    ("WellMonitoringReport", "well_location"): {
        "warning": "This is geographic location, NOT rig code! Do NOT search for NL0010/NF0010 here - use Revenue.rigcode instead"
    },
    
    # Join keys
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
    
    # Cluster info
    ("WellMonitoringReport", "Cluster"): {
        "valid_values": ["Nimr", "Marmul"],
        "usage": "Filter by operational cluster: WHERE Cluster = 'Nimr'"
    }
}


# Save as JSON for the updater script
if __name__ == "__main__":
    with open("critical_neo4j_updates.json", "w") as f:
        json.dump(CRITICAL_UPDATES, f, indent=2)
    
    print("Critical updates defined:")
    for (table, col), info in CRITICAL_UPDATES.items():
        print(f"  {table}.{col}: {info.get('warning', info.get('usage', ''))[:60]}...")
    print(f"\nTotal updates: {len(CRITICAL_UPDATES)}")
    print("\nRun the update via the API or manually apply these to Neo4j.")
