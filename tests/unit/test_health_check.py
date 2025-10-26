"""Unit tests for HealthChecker class."""

import pytest
from unittest.mock import Mock, patch
from neo4j.exceptions import ServiceUnavailable
from src.neo4j_manager.health_check import HealthChecker
from src.neo4j_manager.connection import Neo4jConnection


class TestHealthCheckerInit:
    """Test HealthChecker initialization."""

    def test_init(self):
        """Test initialization."""
        mock_conn = Mock(spec=Neo4jConnection)
        checker = HealthChecker(mock_conn)
        assert checker.connection == mock_conn


class TestHealthCheckerConnectivity:
    """Test connectivity checks."""

    def test_check_connectivity_success(self):
        """Test successful connectivity check."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_driver = Mock()
        mock_conn.driver = mock_driver

        checker = HealthChecker(mock_conn)
        result = checker.check_connectivity()

        assert result is True
        mock_driver.verify_connectivity.assert_called_once()

    def test_check_connectivity_failure(self):
        """Test failed connectivity check."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_driver = Mock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable("Failed")
        mock_conn.driver = mock_driver

        checker = HealthChecker(mock_conn)
        result = checker.check_connectivity()

        assert result is False


class TestHealthCheckerApoc:
    """Test APOC availability checks."""

    def test_check_apoc_available_success(self):
        """Test APOC is available."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = [{"count": 1}]

        checker = HealthChecker(mock_conn)
        result = checker.check_apoc_available()

        assert result is True

    def test_check_apoc_available_failure(self):
        """Test APOC is not available."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.side_effect = Exception("APOC not found")

        checker = HealthChecker(mock_conn)
        result = checker.check_apoc_available()

        assert result is False


class TestHealthCheckerVersion:
    """Test version retrieval."""

    def test_get_version_success(self):
        """Test getting Neo4j version."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = [{"version": "2025.09.0"}]

        checker = HealthChecker(mock_conn)
        version = checker.get_version()

        assert version == "2025.09.0"

    def test_get_version_no_result(self):
        """Test getting version when no result."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.execute_query.return_value = []

        checker = HealthChecker(mock_conn)
        version = checker.get_version()

        assert version == "unknown"


class TestHealthCheckerStats:
    """Test database statistics."""

    def test_get_database_stats(self):
        """Test getting database statistics."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_conn.get_node_count.return_value = 100
        mock_conn.get_relationship_count.return_value = 50
        mock_conn.execute_query.return_value = [{"labels": ["Person", "Company"]}]

        checker = HealthChecker(mock_conn)
        stats = checker.get_database_stats()

        assert stats["node_count"] == 100
        assert stats["relationship_count"] == 50
        assert stats["labels"] == ["Person", "Company"]


class TestHealthCheckerWaitForReady:
    """Test wait for ready functionality."""

    @patch("src.neo4j_manager.health_check.time.sleep")
    def test_wait_for_ready_immediate(self, mock_sleep):
        """Test when Neo4j is immediately ready."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_driver = Mock()
        mock_conn.driver = mock_driver

        checker = HealthChecker(mock_conn)
        result = checker.wait_for_ready(timeout=10, interval=1)

        assert result is True
        mock_sleep.assert_not_called()

    @patch("src.neo4j_manager.health_check.time.sleep")
    @patch("src.neo4j_manager.health_check.time.time")
    def test_wait_for_ready_timeout(self, mock_time, mock_sleep):
        """Test timeout when Neo4j doesn't become ready."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_driver = Mock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable("Not ready")
        mock_conn.driver = mock_driver

        # Simulate time progression to force timeout
        # Mock time to always return values that exceed timeout
        time_values = [0.0, 5.0, 11.0]  # start, during, exceeded
        mock_time.side_effect = iter(time_values * 10)  # Repeat to handle multiple calls

        checker = HealthChecker(mock_conn)
        result = checker.wait_for_ready(timeout=10, interval=1)

        assert result is False


class TestHealthCheckerFullCheck:
    """Test full health check."""

    def test_full_health_check_success(self):
        """Test full health check with all checks passing."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_driver = Mock()
        mock_conn.driver = mock_driver
        mock_conn.execute_query.side_effect = [
            [{"count": 1}],  # APOC check
            [{"version": "2025.09.0"}],  # Version
            [{"labels": ["Person"]}],  # Labels
        ]
        mock_conn.get_node_count.return_value = 10
        mock_conn.get_relationship_count.return_value = 5

        checker = HealthChecker(mock_conn)
        health = checker.full_health_check()

        assert health["connected"] is True
        assert health["apoc_available"] is True
        assert health["version"] == "2025.09.0"
        assert health["stats"]["node_count"] == 10

    def test_full_health_check_with_error(self):
        """Test full health check when connection fails."""
        mock_conn = Mock(spec=Neo4jConnection)
        mock_driver = Mock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable("Failed")
        mock_conn.driver = mock_driver

        checker = HealthChecker(mock_conn)
        health = checker.full_health_check()

        assert health["connected"] is False
        assert health["apoc_available"] is False
        assert health["version"] == "unknown"
