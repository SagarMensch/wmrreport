"""
BM25 Index — In-memory keyword ranking over column corpus
=========================================================
Builds a BM25Okapi index from columns.csv at startup.
Each document = "column_name table_name description" with
abbreviation expansion for domain-specific terms.

Uses rank_bm25 library (pure Python, no external dependencies).
"""

import csv
import re
import logging
from typing import Optional
from rank_bm25 import BM25Okapi
from retrieval.abbreviation_map import ABBREVIATION_MAP, expand_query

log = logging.getLogger("bashira.bm25")


# ── Tokenizer ────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """
    Lowercase tokenization with abbreviation expansion.
    Splits on non-alphanumeric, expands known abbreviations,
    and removes stopwords.
    """
    STOPWORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
        "of", "in", "to", "for", "with", "on", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "and", "but", "or", "nor", "not", "so",
        "yet", "both", "either", "neither", "each", "every", "all",
        "any", "few", "more", "most", "other", "some", "such", "no",
        "than", "too", "very", "just", "about", "this", "that",
        "these", "those", "it", "its", "they", "them", "their",
        "we", "our", "you", "your", "he", "she", "his", "her",
        "what", "which", "who", "whom", "how", "when", "where", "why",
    }

    raw_tokens = re.findall(r'[a-zA-Z0-9_]+', text.lower())
    tokens = []
    for token in raw_tokens:
        if token in STOPWORDS:
            continue
        tokens.append(token)
        # Expand abbreviations inline
        if token in ABBREVIATION_MAP:
            expansion = ABBREVIATION_MAP[token].split()
            tokens.extend(expansion)
        # Also split underscored names: scr_no → scr, no
        if "_" in token:
            parts = token.split("_")
            tokens.extend(parts)

    return tokens


class ColumnBM25Index:
    """
    BM25 index over all columns from columns.csv.

    Each document represents one column with text:
        "{column_name} {table_name} {description}"
    
    Index is built once at startup (~750 docs, sub-second).
    """

    def __init__(self, csv_path: str):
        self._documents: list[dict] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: Optional[BM25Okapi] = None
        self._build_index(csv_path)

    def _build_index(self, csv_path: str) -> None:
        """Load columns.csv and build BM25 index."""
        log.info("Building BM25 index from %s ...", csv_path)

        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                col_name = row.get("columnName", "").strip()
                table_name = row.get("tableName", "").strip()
                desc = row.get("description", "").strip()
                data_type = row.get("dataType", "").strip()

                if not col_name or not table_name:
                    continue

                # Compose document text (column name weighted by repetition)
                doc_text = f"{col_name} {col_name} {table_name} {desc} {data_type}"
                tokens = _tokenize(doc_text)

                self._documents.append({
                    "columnName": col_name,
                    "tableName": table_name,
                    "description": desc,
                    "dataType": data_type,
                })
                self._tokenized_corpus.append(tokens)

        # Build BM25 index
        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)
            log.info("   ✓ BM25 index built: %d documents", len(self._documents))
        else:
            log.warning("   ⚠ No documents found for BM25 index")

    def search(self, query: str, top_k: int = 15) -> list[dict]:
        """
        Search the BM25 index with a query.
        Returns top_k results ranked by BM25 score.
        
        Each result: {columnName, tableName, description, dataType, bm25_score}
        """
        if self._bm25 is None:
            return []

        # Tokenize query with abbreviation expansion
        query_tokens = _tokenize(expand_query(query))

        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # Get top-k indices by score
        scored_indices = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:top_k]

        results = []
        for idx, score in scored_indices:
            if score <= 0:
                continue
            doc = self._documents[idx].copy()
            doc["bm25_score"] = float(score)
            results.append(doc)

        return results

    @property
    def document_count(self) -> int:
        return len(self._documents)
