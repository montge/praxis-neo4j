"""Health check utilities for Neo4j."""

import logging
import time
from typing import Dict, Any
from neo4j.exceptions import ServiceUnavailable
from .connection import Neo4jConnection

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check utilities for Neo4j database."""

    def __init__(self, connection: Neo4jConnection):
        """
        Initialize health checker.

        Args:
            connection: Neo4j connection instance
        """
        self.connection = connection

    def check_connectivity(self) -> bool:
        """
        Check if Neo4j is reachable.

        Returns:
            True if connected, False otherwise
        """
        try:
            self.connection.driver.verify_connectivity()
            return True
        except ServiceUnavailable:
            return False

    def check_apoc_available(self) -> bool:
        """
        Check if APOC plugin is available.

        Returns:
            True if APOC is available, False otherwise
        """
        try:
            result = self.connection.execute_query(
                "CALL apoc.help('version') YIELD name RETURN count(name) as count"
            )
            return result[0]["count"] > 0 if result else False
        except Exception as e:
            logger.error(f"APOC check failed: {e}")
            return False

    def get_version(self) -> str:
        """
        Get Neo4j version.

        Returns:
            Neo4j version string
        """
        result = self.connection.execute_query(
            "CALL dbms.components() YIELD versions RETURN versions[0] as version"
        )
        return result[0]["version"] if result else "unknown"

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with node count, relationship count, and labels
        """
        node_count = self.connection.get_node_count()
        rel_count = self.connection.get_relationship_count()

        # Get all labels
        labels_result = self.connection.execute_query(
            "CALL db.labels() YIELD label RETURN collect(label) as labels"
        )
        labels = labels_result[0]["labels"] if labels_result else []

        return {
            "node_count": node_count,
            "relationship_count": rel_count,
            "labels": labels,
        }

    def wait_for_ready(self, timeout: int = 60, interval: int = 2) -> bool:
        """
        Wait for Neo4j to be ready.

        Args:
            timeout: Maximum wait time in seconds
            interval: Check interval in seconds

        Returns:
            True if Neo4j becomes ready, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_connectivity():
                logger.info("Neo4j is ready")
                return True
            logger.debug(f"Waiting for Neo4j... ({int(time.time() - start_time)}s)")
            time.sleep(interval)

        logger.error(f"Neo4j did not become ready within {timeout}s")
        return False

    def full_health_check(self) -> Dict[str, Any]:
        """
        Perform complete health check.

        Returns:
            Dictionary with health check results
        """
        health = {
            "connected": False,
            "apoc_available": False,
            "version": "unknown",
            "stats": {},
        }

        try:
            health["connected"] = self.check_connectivity()
            if health["connected"]:
                health["apoc_available"] = self.check_apoc_available()
                health["version"] = self.get_version()
                health["stats"] = self.get_database_stats()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health["error"] = str(e)

        return health
