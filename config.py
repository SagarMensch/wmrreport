"""
Bashira Intelligence — Centralized Configuration
=================================================
Single source of truth for all connection parameters.
Loads from .env file. Validates required keys on import.
"""

import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def _require(key: str) -> str:
    """Get a required environment variable or exit with clear error."""
    val = os.environ.get(key)
    if not val:
        print(f"❌ FATAL: Missing required environment variable: {key}")
        print(f"   → Add it to your .env file in the project root.")
        sys.exit(1)
    return val


@dataclass(frozen=True)
class Settings:
    """Immutable configuration loaded once at startup."""

    # Neo4j
    NEO4J_URI: str = _require("NEO4J_URI")
    NEO4J_USER: str = _require("NEO4J_USER")
    NEO4J_PASSWORD: str = _require("NEO4J_PASSWORD")
    NEO4J_DATABASE: str = os.environ.get("NEO4J_DATABASE", "neo4j")

    # Groq LLM
    GROQ_API_KEY: str = _require("GROQ_API_KEY")
    GROQ_API_KEY_2: str = os.environ.get("GROQ_API_KEY_2", "")
    SARVAM_API_KEY: str = os.environ.get("SARVAM_API_KEY", "")

    # Mistral LLM (replacement for Groq when rate limited)
    MISTRAL_API_KEY: str = "SFi0NsPkMMDwdi0fIsExbxPSG4BBnDFh"
    MISTRAL_MODEL: str = "mistral-large-latest"

    # SQL Server (Production Local)
    GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "groq/llama-3.3-70b-versatile")

    # SQL Server
    SQL_SERVER: str = _require("SQL_SERVER")
    SQL_DATABASE: str = _require("SQL_DATABASE")
    SQL_TRUSTED_CONNECTION: bool = os.environ.get("SQL_TRUSTED_CONNECTION", "False").lower() == "true"
    SQL_USER: str = os.environ.get("SQL_USER", "")
    SQL_PASSWORD: str = os.environ.get("SQL_PASSWORD", "")

    # Embedding model
    EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIM: int = 384

    # Retrieval parameters (Expanded for higher-fidelity context)
    VECTOR_TOP_K: int = int(os.environ.get("VECTOR_TOP_K", "40"))
    BM25_TOP_K: int = int(os.environ.get("BM25_TOP_K", "40"))
    FULLTEXT_TOP_K: int = int(os.environ.get("FULLTEXT_TOP_K", "40"))
    FINAL_TOP_K: int = int(os.environ.get("FINAL_TOP_K", "75"))
    RRF_K: int = int(os.environ.get("RRF_K", "60"))

    # Self-healing
    MAX_HEAL_RETRIES: int = int(os.environ.get("MAX_HEAL_RETRIES", "2"))

    # SQL execution
    SQL_MAX_ROWS: int = int(os.environ.get("SQL_MAX_ROWS", "100"))

    # LangGraph State Persistence (Supabase)
    SUPABASE_DB_URI: str = os.environ.get("SUPABASE_DB_URI", "")

    @property
    def sql_connection_string(self) -> str:
        if self.SQL_TRUSTED_CONNECTION:
            return (
                "DRIVER={ODBC Driver 18 for SQL Server};"
                f"SERVER={self.SQL_SERVER};"
                f"DATABASE={self.SQL_DATABASE};"
                "Trusted_Connection=yes;"
                "Encrypt=Optional;"
                "TrustServerCertificate=yes;"
            )
        else:
            return (
                "DRIVER={ODBC Driver 18 for SQL Server};"
                f"SERVER={self.SQL_SERVER};"
                f"DATABASE={self.SQL_DATABASE};"
                f"UID={self.SQL_USER};"
                f"PWD={self.SQL_PASSWORD};"
                "Encrypt=yes;"
                "TrustServerCertificate=yes;"
            )

    # Project paths
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))

    @property
    def columns_csv_path(self) -> str:
        return os.path.join(self.BASE_DIR, "columns_atnm_dev.csv")

    @property
    def columns_clean_csv_path(self) -> str:
        return os.path.join(self.BASE_DIR, "columns_clean.csv")


# Singleton — import `settings` everywhere
settings = Settings()
