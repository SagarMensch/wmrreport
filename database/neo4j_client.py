"""
Neo4j Client — Connection management + search queries
=====================================================
Wraps the Neo4j Python driver with connection pooling,
auto-reconnect, and structured search methods.
"""

import logging
from typing import Optional
from neo4j import GraphDatabase, Driver
from config import settings

log = logging.getLogger("bashira.neo4j")


class Neo4jClient:
    """Thread-safe Neo4j client with lazy connection."""

    def __init__(self):
        self._driver: Optional[Driver] = None

    # ── Connection Lifecycle ────────────────────────────────────────────

    def connect(self) -> None:
        """Establish a new driver connection."""
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        self._driver.verify_connectivity()
        log.info("✓ Connected to Neo4j Aura (%s)", settings.NEO4J_URI)

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self.connect()
        return self._driver

    def _fresh_session(self):
        """Return a new session (avoids ConnectionResetError on long-lived APIs)."""
        return self.driver.session(database=settings.NEO4J_DATABASE)

    # ── Vector Search ────────────────────────────────────────────────────

    def vector_search(self, embedding: list[float], top_k: int = 15) -> list[dict]:
        """
        Semantic search using Neo4j native vector index.
        Returns list of {column, table, description, score}.
        """
        query = """
        CALL db.index.vector.queryNodes('column_embeddings', $top_k, $embedding)
        YIELD node, score
        MATCH (t:Table)-[:HAS_COLUMN]->(node)
        RETURN t.name AS table, node.name AS column,
               node.description AS description, node.dataType AS dataType,
               score
        ORDER BY score DESC
        """
        with self._fresh_session() as session:
            results = session.run(query, embedding=embedding, top_k=top_k)
            return [dict(r) for r in results]

    # ── Fulltext Search ──────────────────────────────────────────────────

    def fulltext_search(self, query_string: str, top_k: int = 15) -> list[dict]:
        """
        Keyword search using Neo4j fulltext index.
        Returns list of {column, table, description, score}.
        """
        query = """
        CALL db.index.fulltext.queryNodes('column_description_ft', $query_string)
        YIELD node, score
        MATCH (t:Table)-[:HAS_COLUMN]->(node)
        RETURN t.name AS table, node.name AS column,
               node.description AS description, node.dataType AS dataType,
               score
        ORDER BY score DESC
        LIMIT $top_k
        """
        with self._fresh_session() as session:
            results = session.run(
                query, query_string=query_string, top_k=top_k
            )
            return [dict(r) for r in results]

    # ── JOIN Path Resolution ─────────────────────────────────────────────

    def get_join_paths(self, table_column_pairs: list[tuple[str, str]]) -> list[dict]:
        """
        For a set of (table, column) pairs, find all JOINS_ON relationships.
        Returns list of {from_table, from_col, to_table, to_col, description}.
        """
        query = """
        UNWIND $pairs AS pair
        MATCH (c:Column {name: pair[1], tableName: pair[0]})
        OPTIONAL MATCH (c)-[j:JOINS_ON]-(other:Column)
        OPTIONAL MATCH (other_table:Table)-[:HAS_COLUMN]->(other)
        WHERE j IS NOT NULL
        RETURN c.tableName AS from_table, c.name AS from_col,
               other_table.name AS to_table, other.name AS to_col,
               j.description AS join_description
        """
        with self._fresh_session() as session:
            results = session.run(query, pairs=list(table_column_pairs))
            return [dict(r) for r in results if r["to_table"] is not None]

    # ── Health Check ─────────────────────────────────────────────────────

    def health_check(self) -> bool:
        try:
            with self._fresh_session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False


# Singleton
neo4j_client = Neo4jClient()
