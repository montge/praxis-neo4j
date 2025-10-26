"""Unit tests for Neo4jConnection class."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from neo4j.exceptions import ServiceUnavailable, AuthError
from src.neo4j_manager.connection import Neo4jConnection


class TestNeo4jConnectionInit:
    """Test Neo4jConnection initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        conn = Neo4jConnection()
        assert conn.uri == "bolt://localhost:7687"
        assert conn.username == "neo4j"
        assert conn.password == "yourpassword"
        assert conn._driver is None

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        conn = Neo4jConnection(uri="bolt://custom:7687", username="admin", password="secret")
        assert conn.uri == "bolt://custom:7687"
        assert conn.username == "admin"
        assert conn.password == "secret"


class TestNeo4jConnectionConnect:
    """Test connection establishment."""

    @patch("src.neo4j_manager.connection.GraphDatabase")
    def test_connect_success(self, mock_graphdb):
        """Test successful connection."""
        mock_driver = Mock()
        mock_graphdb.driver.return_value = mock_driver

        conn = Neo4jConnection()
        driver = conn.connect()

        assert driver == mock_driver
        mock_graphdb.driver.assert_called_once_with(
            "bolt://localhost:7687", auth=("neo4j", "yourpassword")
        )
        mock_driver.verify_connectivity.assert_called_once()

    @patch("src.neo4j_manager.connection.GraphDatabase")
    def test_connect_service_unavailable(self, mock_graphdb):
        """Test connection failure when service is unavailable."""
        mock_driver = Mock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable("Connection failed")
        mock_graphdb.driver.return_value = mock_driver

        conn = Neo4jConnection()
        with pytest.raises(ServiceUnavailable):
            conn.connect()

    @patch("src.neo4j_manager.connection.GraphDatabase")
    def test_connect_auth_error(self, mock_graphdb):
        """Test connection failure with authentication error."""
        mock_driver = Mock()
        mock_driver.verify_connectivity.side_effect = AuthError("Auth failed")
        mock_graphdb.driver.return_value = mock_driver

        conn = Neo4jConnection()
        with pytest.raises(AuthError):
            conn.connect()


class TestNeo4jConnectionQueries:
    """Test query execution methods."""

    def test_execute_query_structure(self):
        """Test execute_query returns proper structure."""
        conn = Neo4jConnection()
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = Mock()

        # Mock record behavior
        mock_record = {"name": "Alice", "age": 30}
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        conn._driver = mock_driver

        result = conn.execute_query("MATCH (n) RETURN n")

        assert isinstance(result, list)
        mock_session.run.assert_called_once()

    def test_execute_query_with_parameters(self):
        """Test execute_query with parameters."""
        conn = Neo4jConnection()
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))

        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        conn._driver = mock_driver

        params = {"name": "Alice"}
        conn.execute_query("MATCH (n {name: $name}) RETURN n", params)

        mock_session.run.assert_called_once_with("MATCH (n {name: $name}) RETURN n", params)


class TestNeo4jConnectionContextManager:
    """Test context manager functionality."""

    @patch("src.neo4j_manager.connection.GraphDatabase")
    def test_context_manager(self, mock_graphdb):
        """Test using connection as context manager."""
        mock_driver = Mock()
        mock_graphdb.driver.return_value = mock_driver

        conn = Neo4jConnection()

        with conn as c:
            assert c == conn
            assert conn._driver is not None

        mock_driver.close.assert_called_once()


class TestNeo4jConnectionClose:
    """Test connection closure."""

    def test_close_when_connected(self):
        """Test closing an active connection."""
        conn = Neo4jConnection()
        mock_driver = Mock()
        conn._driver = mock_driver

        conn.close()

        mock_driver.close.assert_called_once()
        assert conn._driver is None

    def test_close_when_not_connected(self):
        """Test closing when no connection exists."""
        conn = Neo4jConnection()
        conn.close()  # Should not raise exception
        assert conn._driver is None
