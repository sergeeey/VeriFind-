"""
ChromaDB Vector Store Client for APE 2026.

Week 1 Day 2: Embedded mode implementation with temporal filtering.
Target: <30ms retrieval latency for 10K documents.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from pydantic import BaseModel, Field


# ==============================================================================
# Metadata Schema
# ==============================================================================

@dataclass
class DocumentMetadata:
    """
    Metadata schema for financial documents.

    Design principles:
    1. ticker + date_published = temporal filtering capability
    2. source = data provenance tracking
    3. doc_type = filtering by document category
    4. asof_timestamp = critical for temporal integrity (Week 7)
    """
    ticker: str
    date_published: str  # ISO 8601: "2024-01-15"
    source: str  # "10-K", "10-Q", "earnings_call", "sec_filing", etc.
    doc_type: str  # "financial_statement", "transcript", "press_release"
    asof_timestamp: str  # ISO 8601 with time: "2024-01-15T16:00:00Z"

    # Optional fields
    fiscal_quarter: Optional[str] = None  # "Q1 2024"
    fiscal_year: Optional[int] = None
    page_number: Optional[int] = None
    section: Optional[str] = None  # "Risk Factors", "MD&A", etc.
    date_timestamp: Optional[int] = None  # Unix timestamp for range filtering

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, filtering None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class EvidenceDocument(BaseModel):
    """Evidence document for ChromaDB ingestion."""

    id: str = Field(..., description="Unique document ID (hash of content)")
    text: str = Field(..., description="Document text content")
    metadata: DocumentMetadata = Field(..., description="Temporal metadata")

    class Config:
        arbitrary_types_allowed = True


# ==============================================================================
# ChromaDB Vector Store
# ==============================================================================

class ChromaVectorStore:
    """
    Embedded ChromaDB instance for financial evidence retrieval.

    Design (ADR-006):
    - Embedded mode (no separate service)
    - Persistent SQLite storage
    - sentence-transformers/all-MiniLM-L6-v2 (384-dim, fast)
    - Target: <30ms query latency for 10K docs
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_data",
        collection_name: str = "financial_documents",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize ChromaDB client.

        Args:
            persist_directory: Path to persistent storage
            collection_name: Name of the collection
            embedding_model: sentence-transformers model name
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        # Create persist directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client (embedded mode)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True  # For testing only
            )
        )

        # Create embedding function (using default ONNX-based for Windows compatibility)
        # Note: SentenceTransformer has PyTorch DLL issues on Windows
        # Using ChromaDB default (all-MiniLM-L6-v2 via ONNX) instead
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}  # Cosine similarity
        )

    def add_documents(
        self,
        documents: List[EvidenceDocument]
    ) -> None:
        """
        Add documents to the collection.

        Args:
            documents: List of EvidenceDocument objects
        """
        if not documents:
            return

        ids = [doc.id for doc in documents]
        texts = [doc.text for doc in documents]
        metadatas = [doc.metadata.to_dict() for doc in documents]

        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )

    def query(
        self,
        query_text: str,
        n_results: int = 10,
        ticker: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        doc_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query the collection with optional temporal filtering.

        Args:
            query_text: Search query
            n_results: Number of results to return
            ticker: Filter by ticker symbol
            date_start: Filter by start date (ISO 8601) - converted to timestamp
            date_end: Filter by end date (ISO 8601) - converted to timestamp
            doc_type: Filter by document type

        Returns:
            Query results with documents, metadatas, distances
        """
        from datetime import datetime

        # Build where clause for filtering
        where_conditions = []

        if ticker:
            where_conditions.append({"ticker": {"$eq": ticker}})

        if date_start:
            # Convert ISO string to Unix timestamp
            ts_start = int(datetime.fromisoformat(date_start).timestamp())
            where_conditions.append({"date_timestamp": {"$gte": ts_start}})

        if date_end:
            # Convert ISO string to Unix timestamp
            ts_end = int(datetime.fromisoformat(date_end).timestamp())
            where_conditions.append({"date_timestamp": {"$lte": ts_end}})

        if doc_type:
            where_conditions.append({"doc_type": {"$eq": doc_type}})

        # Combine conditions with $and
        where = None
        if where_conditions:
            if len(where_conditions) == 1:
                where = where_conditions[0]
            else:
                where = {"$and": where_conditions}

        # Execute query
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
            "persist_directory": str(self.persist_directory)
        }

    def reset(self) -> None:
        """
        Reset the collection (DELETE ALL DATA).
        Use only for testing!
        """
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )


# ==============================================================================
# Helper Functions
# ==============================================================================

def create_document_id(text: str, metadata: DocumentMetadata) -> str:
    """
    Create unique document ID from content hash.

    Args:
        text: Document text
        metadata: Document metadata

    Returns:
        Unique ID (SHA256 hash prefix)
    """
    import hashlib

    # Include more metadata fields to ensure uniqueness
    content = (
        f"{metadata.ticker}_{metadata.date_published}_"
        f"{metadata.source}_{metadata.doc_type}_{text}"
    )
    return hashlib.sha256(content.encode()).hexdigest()[:16]
