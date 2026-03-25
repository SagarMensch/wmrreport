"""
Neo4j Search Wrapper — Hybrid vector + fulltext over knowledge graph
====================================================================
Thin convenience layer that combines neo4j_client methods into
a single hybrid_search call, plus schema context formatting.
"""

import re
import logging
from sentence_transformers import SentenceTransformer
from database.neo4j_client import neo4j_client
from retrieval.abbreviation_map import expand_query
from config import settings

log = logging.getLogger("bashira.neo4j_search")

# Lazy-loaded embedding model
_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        log.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        log.info("   ✓ Embedding model loaded (%d-dim)", settings.EMBEDDING_DIM)
    return _embedding_model


def embed_text(text: str) -> list[float]:
    """Generate MiniLM embedding for a text string."""
    model = _get_embedding_model()
    return model.encode(text).tolist()


def hybrid_search(
    question: str,
    vector_top_k: int | None = None,
    fulltext_top_k: int | None = None,
) -> dict[str, list[dict]]:
    """
    Execute both vector and fulltext searches against Neo4j.
    
    Returns {
        "vector_results": [...],
        "fulltext_results": [...],
    }
    
    Each result dict: {table, column, description, dataType, score}
    """
    vector_top_k = vector_top_k or settings.VECTOR_TOP_K
    fulltext_top_k = fulltext_top_k or settings.FULLTEXT_TOP_K

    # ── Vector Search ────────────────────────────────────────────────────
    expanded = expand_query(question)
    embedding = embed_text(expanded)
    vector_results = neo4j_client.vector_search(embedding, vector_top_k)

    # ── Fulltext (Keyword) Search ────────────────────────────────────────
    # Build Lucene OR-query with expanded abbreviations, minus stopwords
    words = re.findall(r'\w+', expanded)
    # Filter very short words and common ones
    meaningful = [w for w in words if len(w) >= 2]
    keyword_query = " OR ".join(meaningful) if meaningful else question

    try:
        fulltext_results = neo4j_client.fulltext_search(keyword_query, fulltext_top_k)
    except Exception as e:
        log.warning("Fulltext search failed: %s", e)
        fulltext_results = []

    return {
        "vector_results": vector_results,
        "fulltext_results": fulltext_results,
    }
