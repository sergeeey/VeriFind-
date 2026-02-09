"""
Graph storage modules for APE 2026.

Week 3 Day 4: Neo4j graph storage for Episodes and VerifiedFacts lineage.
"""

from .neo4j_client import Neo4jGraphClient

# Compatibility alias (Week 11: for imports expecting Neo4jClient)
Neo4jClient = Neo4jGraphClient

__all__ = ["Neo4jGraphClient", "Neo4jClient"]
