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
import os
import uuid

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
        password: Optional[str] = None
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
        resolved_password = password or os.getenv("NEO4J_PASSWORD")
        if not resolved_password:
            raise ValueError(
                "NEO4J_PASSWORD is required for Neo4jGraphClient. "
                "Set environment variable NEO4J_PASSWORD or pass password explicitly."
            )

        self.logger = logging.getLogger(__name__)

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, resolved_password))
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
                    f.source_code = $source_code,
                    f.statement = $statement,
                    f.confidence_score = $confidence_score,
                    f.data_source = $data_source,
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
                'source_code': fact.source_code,
                'statement': fact.statement,
                'confidence_score': fact.confidence_score,
                'data_source': fact.data_source,
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

    def create_synthesis_node(
        self,
        fact_id: str,
        synthesis_data: Dict[str, Any]
    ) -> str:
        """
        Create Synthesis node linked to a fact (link created separately).

        Args:
            fact_id: Parent fact identifier
            synthesis_data: Serialized synthesis payload

        Returns:
            synthesis_id
        """
        synthesis_id = synthesis_data.get("synthesis_id") or str(uuid.uuid4())
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Synthesis {synthesis_id: $synthesis_id})
                SET s.fact_id = $fact_id,
                    s.balanced_view = $balanced_view,
                    s.recommendation = $recommendation,
                    s.original_confidence = $original_confidence,
                    s.adjusted_confidence = $adjusted_confidence,
                    s.debate_quality_score = $debate_quality_score,
                    s.key_risks = $key_risks,
                    s.key_opportunities = $key_opportunities,
                    s.areas_of_agreement = $areas_of_agreement,
                    s.areas_of_disagreement = $areas_of_disagreement,
                    s.raw_payload = $raw_payload,
                    s.created_at = $created_at
            """, {
                "synthesis_id": synthesis_id,
                "fact_id": fact_id,
                "balanced_view": synthesis_data.get("balanced_view"),
                "recommendation": synthesis_data.get("recommendation"),
                "original_confidence": synthesis_data.get("original_confidence"),
                "adjusted_confidence": synthesis_data.get("adjusted_confidence"),
                "debate_quality_score": synthesis_data.get("debate_quality_score"),
                "key_risks": synthesis_data.get("key_risks", []),
                "key_opportunities": synthesis_data.get("key_opportunities", []),
                "areas_of_agreement": synthesis_data.get("areas_of_agreement", []),
                "areas_of_disagreement": synthesis_data.get("areas_of_disagreement", []),
                "raw_payload": json.dumps(synthesis_data),
                "created_at": datetime.utcnow().isoformat(),
            })

        self.logger.info(f"Created Synthesis node: {synthesis_id} for fact {fact_id}")
        return synthesis_id

    def link_fact_to_synthesis(self, fact_id: str, synthesis_id: str):
        """
        Link VerifiedFact to Synthesis node.

        Args:
            fact_id: Fact identifier
            synthesis_id: Synthesis identifier
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (f:VerifiedFact {fact_id: $fact_id})
                MATCH (s:Synthesis {synthesis_id: $synthesis_id})
                MERGE (f)-[:SYNTHESIZED_INTO]->(s)
            """, {
                "fact_id": fact_id,
                "synthesis_id": synthesis_id
            })

        self.logger.info(f"Linked Fact {fact_id} -> Synthesis {synthesis_id}")

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

    def list_episodes(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List Episode nodes with pagination.

        Args:
            limit: Max records to return
            offset: Offset for pagination

        Returns:
            List of episode dictionaries
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                RETURN e
                ORDER BY e.created_at DESC
                SKIP $offset
                LIMIT $limit
            """, {"limit": limit, "offset": offset})

            return [dict(record["e"]) for record in result]

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

    def search_facts_by_ticker(self, ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search facts by ticker symbol in statement/extracted values/query text.

        Args:
            ticker: Ticker symbol (e.g., AAPL)
            limit: Max records to return

        Returns:
            List of fact dictionaries
        """
        ticker_upper = ticker.upper()
        with self.driver.session() as session:
            result = session.run("""
                MATCH (f:VerifiedFact)
                OPTIONAL MATCH (e:Episode)-[:GENERATED]->(f)
                WHERE toUpper(coalesce(f.statement, "")) CONTAINS $ticker
                   OR toUpper(coalesce(f.extracted_values, "")) CONTAINS $ticker
                   OR toUpper(coalesce(e.query_text, "")) CONTAINS $ticker
                RETURN DISTINCT f
                ORDER BY f.created_at DESC
                LIMIT $limit
            """, {"ticker": ticker_upper, "limit": limit})

            facts: List[Dict[str, Any]] = []
            for record in result:
                fact_dict = dict(record["f"])
                if "extracted_values" in fact_dict and isinstance(fact_dict["extracted_values"], str):
                    try:
                        fact_dict["extracted_values"] = json.loads(fact_dict["extracted_values"])
                    except json.JSONDecodeError:
                        pass
                facts.append(fact_dict)
            return facts

    def get_related_facts(self, fact_id: str) -> Dict[str, Any]:
        """
        Get related facts and synthesis artifacts for a fact.

        Args:
            fact_id: Fact identifier

        Returns:
            Dict with current fact and related entities
        """
        base_fact = self.get_fact_node(fact_id)
        if not base_fact:
            return {"fact": None, "ancestors": [], "descendants": [], "syntheses": []}

        with self.driver.session() as session:
            ancestors_res = session.run("""
                MATCH (f:VerifiedFact {fact_id: $fact_id})-[:DERIVED_FROM]->(ancestor:VerifiedFact)
                RETURN ancestor
            """, {"fact_id": fact_id})

            descendants_res = session.run("""
                MATCH (descendant:VerifiedFact)-[:DERIVED_FROM]->(f:VerifiedFact {fact_id: $fact_id})
                RETURN descendant
            """, {"fact_id": fact_id})

            syntheses_res = session.run("""
                MATCH (f:VerifiedFact {fact_id: $fact_id})-[:SYNTHESIZED_INTO]->(s:Synthesis)
                RETURN s
                ORDER BY s.created_at DESC
            """, {"fact_id": fact_id})

            ancestors: List[Dict[str, Any]] = []
            descendants: List[Dict[str, Any]] = []
            syntheses: List[Dict[str, Any]] = []

            for record in ancestors_res:
                node = dict(record["ancestor"])
                if "extracted_values" in node and isinstance(node["extracted_values"], str):
                    try:
                        node["extracted_values"] = json.loads(node["extracted_values"])
                    except json.JSONDecodeError:
                        pass
                ancestors.append(node)

            for record in descendants_res:
                node = dict(record["descendant"])
                if "extracted_values" in node and isinstance(node["extracted_values"], str):
                    try:
                        node["extracted_values"] = json.loads(node["extracted_values"])
                    except json.JSONDecodeError:
                        pass
                descendants.append(node)

            for record in syntheses_res:
                node = dict(record["s"])
                if "raw_payload" in node and isinstance(node["raw_payload"], str):
                    try:
                        node["raw_payload"] = json.loads(node["raw_payload"])
                    except json.JSONDecodeError:
                        pass
                syntheses.append(node)

            return {
                "fact": base_fact,
                "ancestors": ancestors,
                "descendants": descendants,
                "syntheses": syntheses
            }

    def get_audit_trail(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Get end-to-end audit trail for a query.

        Args:
            query_id: Query identifier (maps to Episode.episode_id)

        Returns:
            Dict with episode, latest verified fact and synthesis (if any), or None.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode {episode_id: $query_id})
                OPTIONAL MATCH (e)-[:GENERATED]->(f:VerifiedFact)
                OPTIONAL MATCH (f)-[:SYNTHESIZED_INTO]->(s:Synthesis)
                RETURN e, f, s
                ORDER BY f.created_at DESC, s.created_at DESC
                LIMIT 1
            """, {"query_id": query_id})

            record = result.single()
            if not record or not record.get("e"):
                return None

            episode = dict(record["e"])
            fact_node = dict(record["f"]) if record.get("f") else None
            synthesis_node = dict(record["s"]) if record.get("s") else None

            if fact_node and "extracted_values" in fact_node and isinstance(fact_node["extracted_values"], str):
                try:
                    fact_node["extracted_values"] = json.loads(fact_node["extracted_values"])
                except json.JSONDecodeError:
                    pass

            if synthesis_node and "raw_payload" in synthesis_node and isinstance(synthesis_node["raw_payload"], str):
                try:
                    synthesis_node["raw_payload"] = json.loads(synthesis_node["raw_payload"])
                except json.JSONDecodeError:
                    pass

            return {
                "episode": episode,
                "verified_fact": fact_node,
                "synthesis": synthesis_node,
            }

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

            # Count syntheses
            synthesis_result = session.run("MATCH (s:Synthesis) RETURN count(s) as count")
            synthesis_count = synthesis_result.single()['count']

            return {
                'episode_count': episode_count,
                'fact_count': fact_count,
                'synthesis_count': synthesis_count,
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

# Compatibility alias (Week 11: for imports expecting Neo4jClient)
Neo4jClient = Neo4jGraphClient
