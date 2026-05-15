"""
Retrieval Agent — Triple-source hybrid retrieval with RRF
=========================================================
Orchestrates three retrieval sources:
  1. Neo4j Vector Search (semantic, MiniLM embeddings)
  2. Neo4j Fulltext Search (keyword, Lucene)
  3. BM25 In-Memory Index (statistical keyword ranking)

Merges results using Reciprocal Rank Fusion (RRF) and
enriches with JOIN path metadata from the knowledge graph.
"""

import logging
from dataclasses import dataclass, field
from config import settings
from agents.intent_agent import IntentResult
from retrieval.bm25_index import ColumnBM25Index
from retrieval.neo4j_search import hybrid_search as neo4j_hybrid_search
from database.neo4j_client import neo4j_client

log = logging.getLogger("bashira.retrieval_agent")


# ── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class ColumnMatch:
    """A single column found by retrieval."""
    column: str
    table: str
    description: str
    data_type: str = ""
    vector_score: float = 0.0
    fulltext_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0


@dataclass
class SchemaContext:
    """Retrieval result with merged schema and JOIN information."""
    columns: list[ColumnMatch] = field(default_factory=list)
    join_paths: list[dict] = field(default_factory=list)
    schema_text: str = ""
    retrieval_summary: str = ""


# ── Reciprocal Rank Fusion ───────────────────────────────────────────────

def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    key_fn,
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    Merge multiple ranked lists using RRF.
    score(d) = Σ 1 / (k + rank_i(d))
    
    key_fn: function that extracts a unique key from each result dict.
    Returns list of (key, rrf_score) sorted by score descending.
    """
    scores: dict[str, float] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            key = key_fn(item)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── Retrieval Agent ──────────────────────────────────────────────────────

class RetrievalAgent:
    """
    Triple-source hybrid retrieval agent.
    
    Combines Neo4j vector, Neo4j fulltext, and BM25 results
    using Reciprocal Rank Fusion for maximum recall.
    """

    def __init__(self, bm25_index: ColumnBM25Index):
        self._bm25 = bm25_index

    def retrieve(self, intent: IntentResult) -> SchemaContext:
        """
        Execute triple-source retrieval and merge with RRF.
        
        Pipeline:
          1. Neo4j vector search (semantic)
          2. Neo4j fulltext search (keyword, expanded)
          3. BM25 over columns.csv (statistical, expanded)
          4. RRF merge + dedup
          5. Fetch JOIN paths for selected columns
          6. Build schema context string
        """
        question = intent.expanded_question

        log.info("Retrieval Agent: processing '%s'", intent.original_question)
        log.info("  Expanded: '%s'", question[:100])

        # ── 1+2. Neo4j Hybrid Search ─────────────────────────────────────
        neo4j_results = neo4j_hybrid_search(
            intent.original_question,
            vector_top_k=settings.VECTOR_TOP_K,
            fulltext_top_k=settings.FULLTEXT_TOP_K,
        )
        vector_results = neo4j_results["vector_results"]
        fulltext_results = neo4j_results["fulltext_results"]

        log.info("  Vector results: %d, Fulltext results: %d",
                 len(vector_results), len(fulltext_results))

        # ── 3. BM25 Search ───────────────────────────────────────────────
        bm25_results = self._bm25.search(
            intent.original_question, top_k=settings.BM25_TOP_K
        )
        log.info("  BM25 results: %d", len(bm25_results))

        # ── 4. RRF Fusion ────────────────────────────────────────────────
        def make_key(item: dict) -> str:
            table = item.get("table") or item.get("tableName", "")
            col = item.get("column") or item.get("columnName", "")
            return f"{table}::{col}"

        rrf_scores = reciprocal_rank_fusion(
            [vector_results, fulltext_results, bm25_results],
            key_fn=make_key,
            k=settings.RRF_K,
        )

        # ── Build ColumnMatch objects ────────────────────────────────────
        # Index all results by key for quick lookup
        all_results: dict[str, dict] = {}
        for item in vector_results + fulltext_results + bm25_results:
            key = make_key(item)
            if key not in all_results:
                all_results[key] = {
                    "column": item.get("column") or item.get("columnName", ""),
                    "table": item.get("table") or item.get("tableName", ""),
                    "description": item.get("description", ""),
                    "data_type": item.get("dataType") or item.get("data_type", ""),
                }

        columns: list[ColumnMatch] = []
        for key, rrf_score in rrf_scores[:settings.FINAL_TOP_K]:
            if key in all_results:
                info = all_results[key]
                columns.append(ColumnMatch(
                    column=info["column"],
                    table=info["table"],
                    description=info["description"],
                    data_type=info["data_type"],
                    rrf_score=rrf_score,
                ))

        # ── 5. Fetch JOIN paths ──────────────────────────────────────────
        if columns:
            pairs = [(c.table, c.column) for c in columns]
            try:
                join_paths = neo4j_client.get_join_paths(pairs)
            except Exception as e:
                log.warning("JOIN path resolution failed: %s", e)
                join_paths = []
        else:
            join_paths = []

        # ── 6. Build schema context string ───────────────────────────────
        schema_text = self._build_schema_text(columns, join_paths)

        summary = (
            f"Retrieved {len(columns)} columns via RRF "
            f"(Vector: {len(vector_results)}, Fulltext: {len(fulltext_results)}, "
            f"BM25: {len(bm25_results)}), {len(join_paths)} JOIN paths"
        )

        log.info("  %s", summary)

        return SchemaContext(
            columns=columns,
            join_paths=join_paths,
            schema_text=schema_text,
            retrieval_summary=summary,
        )

    @staticmethod
    def _build_schema_text(
        columns: list[ColumnMatch],
        join_paths: list[dict],
    ) -> str:
        """
        Build a structured schema context string for the SQL agent.
        Groups columns by table for clarity.
        """
        if not columns:
            return "(No matching schema found)"

        # Group by table
        tables: dict[str, list[ColumnMatch]] = {}
        for col in columns:
            tables.setdefault(col.table, []).append(col)

        lines = ["Database Schema (from Knowledge Graph + BM25 retrieval):\n"]

        for table_name, cols in tables.items():
            lines.append(f"TABLE: {table_name}")
            for c in cols:
                dtype = f" ({c.data_type})" if c.data_type else ""
                lines.append(
                    f"  - Column '{c.column}'{dtype}: {c.description}"
                )
            lines.append("")

        # Add JOIN hints
        if join_paths:
            lines.append("JOIN RELATIONSHIPS:")
            seen = set()
            for jp in join_paths:
                key = f"{jp['from_table']}.{jp['from_col']}={jp['to_table']}.{jp['to_col']}"
                if key not in seen:
                    seen.add(key)
                    lines.append(
                        f"  - {jp['from_table']}.{jp['from_col']} "
                        f"JOINS_ON {jp['to_table']}.{jp['to_col']}"
                    )
            lines.append("")

        return "\n".join(lines)
