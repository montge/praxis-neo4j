"""Neo4j connection management."""

import logging
from typing import Optional, Any, Dict, List
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Manages Neo4j database connections."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "yourpassword",
    ):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j bolt URI
            username: Database username
            password: Database password
        """
        self.uri = uri
        self.username = username
        self.password = password
        self._driver: Optional[Driver] = None

    def connect(self) -> Driver:
        """
        Establish connection to Neo4j.

        Returns:
            Neo4j driver instance

        Raises:
            ServiceUnavailable: If Neo4j is not reachable
            AuthError: If authentication fails
        """
        try:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            return self._driver
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable at {self.uri}: {e}")
            raise
        except AuthError as e:
            logger.error(f"Authentication failed for user {self.username}: {e}")
            raise

    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")
            self._driver = None

    @property
    def driver(self) -> Driver:
        """
        Get the driver instance, connecting if necessary.

        Returns:
            Neo4j driver instance
        """
        if not self._driver:
            return self.connect()
        return self._driver

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def execute_write(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a write query in a transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """

        def _write_tx(tx):
            result = tx.run(query, parameters or {})
            return [dict(record) for record in result]

        with self.driver.session() as session:
            return session.execute_write(_write_tx)

    def get_node_count(self) -> int:
        """
        Get total number of nodes in database.

        Returns:
            Node count
        """
        result = self.execute_query("MATCH (n) RETURN count(n) as count")
        return result[0]["count"] if result else 0

    def get_relationship_count(self) -> int:
        """
        Get total number of relationships in database.

        Returns:
            Relationship count
        """
        result = self.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
        return result[0]["count"] if result else 0

    def clear_database(self) -> None:
        """
        Clear all nodes and relationships from database.

        Warning: This is a destructive operation!
        """
        logger.warning("Clearing all data from database")
        self.execute_write("MATCH (n) DETACH DELETE n")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
