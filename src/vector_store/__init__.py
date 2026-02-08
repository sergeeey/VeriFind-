"""
Vector store module for APE 2026.
Handles ChromaDB embedded instance for evidence retrieval.
"""

from .chroma_client import ChromaVectorStore, DocumentMetadata, EvidenceDocument

__all__ = ["ChromaVectorStore", "DocumentMetadata", "EvidenceDocument"]
