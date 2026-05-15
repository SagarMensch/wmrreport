# BM25 + Neo4j + MiniLM Integration Guide

This document explains how the three retrieval systems work together to prevent hallucinations and find the right tables/columns.

---

## Architecture Overview

```
User Query
    |
    v
+------------------+
| Query Expansion  |  <-- Abbreviation mapping (e.g., "SCR" -> "scr_no")
+------------------+
    |
    v
+------------------+     +-------------------+     +------------------+
| BM25 Search      |     | Neo4j Fulltext   |     | MiniLM Embedding |
| (Keyword match)  |     | (Schema match)    |     | (Semantic match) |
+------------------+     +-------------------+     +------------------+
    |                          |                          |
    +------------+-------------+-------------+----------+
                 |                          |
                 v                          v
         +------------------------------------------------+
         |           RERANKING & FUSION                   |
         |  - Reciprocal Rank Fusion (RRF)              |
         |  - Score weighted combination                 |
         +------------------------------------------------+
                          |
                          v
         +------------------------------------------------+
         |         INTENT CLASSIFICATION                 |
         |  - Well Progress Query                       |
         |  - Revenue Query                             |
         |  - Productivity Query                        |
         |  - General Query                             |
         +------------------------------------------------+
                          |
                          v
         +------------------------------------------------+
         |         SQL GENERATION (DSPy)                 |
         |  - Schema context from retrieval              |
         |  - Query patterns from training               |
         |  - Type casting auto-fix                      |
         +------------------------------------------------+
```

---

## 1. BM25 (Statistical Keyword Search)

### Purpose
- Fast keyword-based matching
- Good for exact column name matches
- Handles abbreviations and synonyms

### How It Works
BM25 ranks documents based on:
- **Term Frequency (TF)**: How often a term appears in document
- **Inverse Document Frequency (IDF)**: How rare the term is across documents
- **Document Length Normalization**: Balances short vs long documents

### Formula
```
score(Q,d) = sum over qi in Q:
    IDF(qi) * (f(qi,D) * (k1+1)) / (f(qi,D) + k1 * (1 - b + b * |D|/avgdl))
```

### In Our System
- Each column description is a "document"
- Query expands abbreviations before search
- Returns top-K results ranked by relevance

### Configuration
```python
BM25_TOP_K = 40  # Number of results to retrieve
k1 = 1.5         # Term frequency saturation
b = 0.75         # Length normalization
```

---

## 2. Neo4j Graph (Schema Knowledge)

### Purpose
- Store table/column relationships
- Enable graph traversal for joins
- Fulltext search on descriptions

### Graph Structure

### Nodes
- **Table**: Database table with business description
- **Column**: Table column with semantic description
- **Well**: Central hub for well data

### Relationships
- `HAS_COLUMN` / `BELONGS_TO`: Table -> Column
- `REFERENCES_WELL`: Tables linking to wells
- `MIRRORS`: Tables with similar schema
- `JOINS_ON`: Foreign key relationships

### Fulltext Index
```cypher
CREATE FULLTEXT INDEX column_description_ft FOR (c:Column) ON EACH [c.name, c.description]
```

### Queries
- Find all columns in a table
- Find tables related to "wells"
- Find join paths between tables

---

## 3. MiniLM (Semantic Embeddings)

### Purpose
- Understand query intent semantically
- Match columns even with different terminology
- Handle paraphrased questions

### Model: all-MiniLM-L6-v2
- **Dimensions**: 384
- **Architecture**: Transformer-based (DistilBERT)
- **Training**: Sentence-BERT with NLI data

### How It Works
1. Convert column description to 384-dim vector
2. Convert user query to 384-dim vector
3. Compute cosine similarity
4. Return top-K semantically similar columns

### Neo4j Vector Index
```cypher
CREATE VECTOR INDEX column_embeddings 
FOR (c:Column) ON (c.embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
}}
```

---

## Query Flow Example

**User Query**: "Which wells are behind schedule?"

### Step 1: Query Expansion
```
"wells behind schedule" 
-> expand "wells" -> "well"
-> expand "behind schedule" -> "delay" "overrun"
```

### Step 2: BM25 Search
Matches:
- `engg_kpi_after_rig-off_days` (score: 12.3)
- `actual_rig_off_date` (score: 8.1)
- `progress` (score: 7.5)

### Step 3: Neo4j Fulltext
Matches:
- `WellMonitoringReport` has column `over_all_progress_percentages`
- Table linked to Cluster, Rig

### Step 4: MiniLM Semantic
Finds:
- `over_all_progress_percentages` (similarity: 0.89)
- `engg_kpi_after_rig-off_days` (similarity: 0.82)

### Step 5: Fusion & Rerank
Combined results with RRF:
1. `over_all_progress_percentages` - WellMonitoringReport
2. `engg_kpi_after_rig-off_days` - WellMonitoringReport
3. `Cluster` - WellMonitoringReport

### Step 6: SQL Generation
```sql
SELECT well_name_after_spud, pdo_well_id, rig_no, 
       over_all_progress_percentages * 100 AS progress_pct,
       engg_kpi_after_rig_off_days AS kpi_days
FROM WellMonitoringReport_Latest
WHERE Cluster = 'Nimr' 
  AND (over_all_progress_percentages < 0.5 
       OR engg_kpi_after_rig_off_days > 2)
ORDER BY over_all_progress_percentages
```

---

## Key Column Mappings (For SQL Generation)

### Well Identification
| Table | Column | Usage |
|-------|--------|-------|
| WellMonitoringReport | pdo_well_id | Primary key, count distinct |
| WellMonitoringReport_Latest | pdo_well_id | Current wells |
| Job_Progress_Report_GB | [Well ID] | Join key (bracket!) |
| Revenue | well_id | Revenue by well |
| task_daily | well_id | Tasks by well |
| ActivityTaskPlan | Well_ID | Tasks by well |

### Progress Columns
| Column | Table | Meaning |
|--------|-------|---------|
| over_all_progress_percentages | WMR | 0-1 decimal |
| progress | task_daily | Task progress |
| Week-1 Actual % | Job_Progress | Actual vs plan |

### Join Patterns
```sql
-- Join WMR with Job Progress
SELECT w.well_name, j.[Week-1 Actual %]
FROM WellMonitoringReport_Latest w
JOIN Job_Progress_Report_GB j ON w.pdo_well_id = j.[Well ID]

-- Join with Revenue
SELECT w.well_name, r.actual_purpose_value
FROM WellMonitoringReport_Latest w
JOIN Revenue r ON w.pdo_well_id = r.well_id
```

---

## Anti-Hallucination Measures

1. **Schema-Bound SQL**: Only generate SQL using retrieved columns
2. **Type Casting Auto-Fix**: TRY_CAST for nvarchar comparisons
3. **Well ID Enforcement**: Use pdo_well_id for counting
4. **Validation Layer**: Check SQL before execution
5. **Result Verification**: Warn on unusual results

---

## Files Modified

1. `columns_updated.csv` - 463 columns with business descriptions
2. `seed_neo4j.py` - Updated for new schema
3. `embed_columns.py` - Generates MiniLM embeddings
4. `bm25_index.py` - Keyword search over columns

---

## To Run Full Pipeline

```bash
# 1. Update Neo4j with new schema
python seed_neo4j.py

# 2. Generate MiniLM embeddings
python embed_columns.py

# 3. Rebuild BM25 index (automatic on startup)
# The orchestrator loads BM25 at startup
```
