"""
Neo4j Graph Client for APE 2026.

Week 3 Day 4: Store Episodes, VerifiedFacts, and lineage tracking.

Graph Schema:
- Episode nodes: episode_id, query_text, created_at
- VerifiedFact nodes: fact_id, query_id, status, extracted_values, created_at
- Relationships:
  - (:Episode)-[:GENERATED]->(:VerifiedFact)
  - (:VerifiedFact)-[:DERIVED_FROM]->(:VerifiedFact)
"""

from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json

from src.truth_boundary.gate import VerifiedFact


class Neo4jGraphClient:
    """
    Neo4j graph client for storing Episodes and VerifiedFacts.

    Provides methods for:
    - Creating Episode and VerifiedFact nodes
    - Linking Episodes to Facts
    - Tracking fact lineage
    - Querying audit trails
    """

    def __init__(
        self,
        uri: str = 'neo4j://localhost:7688',
        user: str = 'neo4j',
        password: str = 'PDHGuBQs62EBXLknJC-Hd4XxPW3uwaC0q9FKNoeFDKY'  # Persisted auto-generated password
    ):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI
            user: Database user
            password: Database password
        """
        self.uri = uri
        self.user = user

        self.logger = logging.getLogger(__name__)

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.logger.info(f"Connected to Neo4j at {uri}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def is_connected(self) -> bool:
        """Check if Neo4j connection is active."""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except:
            return False

    def create_episode(
        self,
        episode_id: str,
        query_text: str,
        created_at: datetime
    ):
        """
        Create Episode node.

        Args:
            episode_id: Unique episode identifier
            query_text: User query
            created_at: Creation timestamp
        """
        with self.driver.session() as session:
            session.run("""
                MERGE (e:Episode {episode_id: $episode_id})
                SET e.query_text = $query_text,
                    e.created_at = $created_at
            """, {
                'episode_id': episode_id,
                'query_text': query_text,
                'created_at': created_at.isoformat()
            })

        self.logger.info(f"Created Episode node: {episode_id}")

    def create_verified_fact_node(self, fact: VerifiedFact):
        """
        Create VerifiedFact node.

        Args:
            fact: VerifiedFact object
        """
        with self.driver.session() as session:
            session.run("""
                MERGE (f:VerifiedFact {fact_id: $fact_id})
                SET f.query_id = $query_id,
                    f.plan_id = $plan_id,
                    f.code_hash = $code_hash,
                    f.status = $status,
                    f.extracted_values = $extracted_values,
                    f.execution_time_ms = $execution_time_ms,
                    f.memory_used_mb = $memory_used_mb,
                    f.created_at = $created_at,
                    f.error_message = $error_message
            """, {
                'fact_id': fact.fact_id,
                'query_id': fact.query_id,
                'plan_id': fact.plan_id,
                'code_hash': fact.code_hash,
                'status': fact.status,
                'extracted_values': json.dumps(fact.extracted_values),
                'execution_time_ms': fact.execution_time_ms,
                'memory_used_mb': fact.memory_used_mb,
                'created_at': fact.created_at.isoformat(),
                'error_message': fact.error_message
            })

        self.logger.info(f"Created VerifiedFact node: {fact.fact_id}")

    def link_episode_to_fact(self, episode_id: str, fact_id: str):
        """
        Create GENERATED relationship: Episode → VerifiedFact.

        Args:
            episode_id: Episode identifier
            fact_id: Fact identifier
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (e:Episode {episode_id: $episode_id})
                MATCH (f:VerifiedFact {fact_id: $fact_id})
                MERGE (e)-[:GENERATED]->(f)
            """, {
                'episode_id': episode_id,
                'fact_id': fact_id
            })

        self.logger.info(f"Linked Episode {episode_id} → Fact {fact_id}")

    def create_lineage(self, from_fact_id: str, to_fact_id: str):
        """
        Create DERIVED_FROM relationship: VerifiedFact → VerifiedFact.

        Args:
            from_fact_id: Derived fact ID
            to_fact_id: Source fact ID
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (from:VerifiedFact {fact_id: $from_fact_id})
                MATCH (to:VerifiedFact {fact_id: $to_fact_id})
                MERGE (from)-[:DERIVED_FROM]->(to)
            """, {
                'from_fact_id': from_fact_id,
                'to_fact_id': to_fact_id
            })

        self.logger.info(f"Created lineage: {from_fact_id} → {to_fact_id}")

    def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve Episode by ID.

        Args:
            episode_id: Episode identifier

        Returns:
            Episode data or None
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode {episode_id: $episode_id})
                RETURN e
            """, {'episode_id': episode_id})

            record = result.single()
            if record:
                return dict(record['e'])
            return None

    def get_fact_node(self, fact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve VerifiedFact node by ID.

        Args:
            fact_id: Fact identifier

        Returns:
            Fact node data or None
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (f:VerifiedFact {fact_id: $fact_id})
                RETURN f
            """, {'fact_id': fact_id})

            record = result.single()
            if record:
                fact_dict = dict(record['f'])
                # Parse JSON extracted_values
                if 'extracted_values' in fact_dict:
                    fact_dict['extracted_values'] = json.loads(fact_dict['extracted_values'])
                return fact_dict
            return None

    def get_facts_for_episode(self, episode_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all VerifiedFacts generated by an Episode.

        Args:
            episode_id: Episode identifier

        Returns:
            List of fact dictionaries
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode {episode_id: $episode_id})-[:GENERATED]->(f:VerifiedFact)
                RETURN f
                ORDER BY f.created_at DESC
            """, {'episode_id': episode_id})

            facts = []
            for record in result:
                fact_dict = dict(record['f'])
                # Parse JSON
                if 'extracted_values' in fact_dict:
                    fact_dict['extracted_values'] = json.loads(fact_dict['extracted_values'])
                facts.append(fact_dict)

            return facts

    def get_fact_lineage(self, fact_id: str) -> List[Dict[str, Any]]:
        """
        Get all facts that this fact was derived from (ancestors).

        Args:
            fact_id: Fact identifier

        Returns:
            List of ancestor fact dictionaries
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (f:VerifiedFact {fact_id: $fact_id})-[:DERIVED_FROM]->(ancestor:VerifiedFact)
                RETURN ancestor
            """, {'fact_id': fact_id})

            ancestors = []
            for record in result:
                ancestor_dict = dict(record['ancestor'])
                if 'extracted_values' in ancestor_dict:
                    ancestor_dict['extracted_values'] = json.loads(ancestor_dict['extracted_values'])
                ancestors.append(ancestor_dict)

            return ancestors

    def run_cypher(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Run arbitrary Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result dictionaries
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})

            records = []
            for record in result:
                records.append(dict(record))

            return records

    def delete_episode(self, episode_id: str):
        """
        Delete Episode and all related facts (CASCADE).

        Args:
            episode_id: Episode identifier
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (e:Episode {episode_id: $episode_id})-[:GENERATED]->(f:VerifiedFact)
                DETACH DELETE e, f
            """, {'episode_id': episode_id})

        self.logger.info(f"Deleted Episode: {episode_id}")

    def get_graph_stats(self) -> Dict[str, int]:
        """
        Get graph statistics.

        Returns:
            Dictionary with node and relationship counts
        """
        with self.driver.session() as session:
            # Count Episodes
            episode_result = session.run("MATCH (e:Episode) RETURN count(e) as count")
            episode_count = episode_result.single()['count']

            # Count VerifiedFacts
            fact_result = session.run("MATCH (f:VerifiedFact) RETURN count(f) as count")
            fact_count = fact_result.single()['count']

            # Count relationships
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.single()['count']

            return {
                'episode_count': episode_count,
                'fact_count': fact_count,
                'relationship_count': rel_count
            }

    def clear_all(self):
        """
        Clear all nodes and relationships (for testing only).

        WARNING: Deletes all data!
        """
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        self.logger.warning("Cleared all graph data (testing mode)")

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j connection closed")
