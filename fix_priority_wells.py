import pandas as pd

# Fix priority_wells_final.csv
print("Loading priority_wells_final.csv...")
priority = pd.read_csv("wmr_results (1)/priority_wells_final.csv")

print(f"Before dedup: {len(priority)} rows")
print(f"Unique well_name_after_spud: {priority['well_name_after_spud'].nunique()}")

# Check if pdo_well_id exists
if 'pdo_well_id' in priority.columns:
    print(f"Unique pdo_well_id: {priority['pdo_well_id'].nunique()}")
    # Deduplicate by pdo_well_id
    priority_dedup = priority.drop_duplicates(subset=['pdo_well_id'], keep='first')
else:
    print("pdo_well_id not in priority file, checking risk_scores.csv...")
    # Need to get pdo_well_id from risk_scores
    risk = pd.read_csv("wmr_results (1)/risk_scores.csv")
    # Get unique pdo_well_id -> well_name mapping
    well_map = risk[['pdo_well_id', 'well_name_after_spud']].drop_duplicates()
    well_map = well_map.sort_values('pdo_well_id').drop_duplicates(subset=['pdo_well_id'], keep='first')
    
    # Add pdo_well_id to priority
    priority = priority.merge(well_map, on='well_name_after_spud', how='left')
    priority_dedup = priority.drop_duplicates(subset=['pdo_well_id'], keep='first')

print(f"After dedup: {len(priority_dedup)} rows")

# Sort by risk_tier and risk_score
tier_order = {"CRITICAL": 0, "HIGH_RISK": 1, "WATCH": 2, "HEALTHY": 3}
priority_dedup['tier_order'] = priority_dedup['risk_tier'].map(tier_order)
priority_dedup = priority_dedup.sort_values(['tier_order', 'risk_score'], ascending=[True, False])
priority_dedup = priority_dedup.drop(columns=['tier_order'])

# Reorder columns - put pdo_well_id first
cols = priority_dedup.columns.tolist()
if 'pdo_well_id' in cols:
    cols.remove('pdo_well_id')
    cols = ['pdo_well_id'] + cols
    priority_dedup = priority_dedup[cols]

# Save
priority_dedup.to_csv("wmr_results (1)/priority_wells_final.csv", index=False)
print(f"Saved priority_wells_final.csv with {len(priority_dedup)} unique wells")

# Also fix risk_scores.csv
print("\nLoading risk_scores.csv...")
risk = pd.read_csv("wmr_results (1)/risk_scores.csv")
print(f"Before dedup: {len(risk)} rows")
print(f"Unique pdo_well_id: {risk['pdo_well_id'].nunique()}")

# Get unique wells by pdo_well_id, keep first (or latest by ramz_id if available)
if 'ramz_id' in risk.columns:
    risk_dedup = risk.sort_values('ramz_id', ascending=False).drop_duplicates(subset=['pdo_well_id'], keep='first')
else:
    risk_dedup = risk.drop_duplicates(subset=['pdo_well_id'], keep='first')

print(f"After dedup: {len(risk_dedup)} rows")

risk_dedup.to_csv("wmr_results (1)/risk_scores.csv", index=False)
print(f"Saved risk_scores.csv with {len(risk_dedup)} unique wells")

print("\n✅ FIX COMPLETE!")
print(f"Priority wells now: {len(priority_dedup)} unique wells (was {len(priority)})")
