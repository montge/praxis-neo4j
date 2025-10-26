"""Integration tests for Neo4j operations.

These tests require a running Neo4j instance.
Run with: pytest tests/integration/ --neo4j-integration
"""

import pytest
from src.neo4j_manager import Neo4jConnection


pytestmark = pytest.mark.integration


class TestNeo4jConnectionIntegration:
    """Integration tests for Neo4jConnection."""

    def test_connect_to_real_database(self, neo4j_connection):
        """Test connecting to actual Neo4j instance."""
        driver = neo4j_connection.connect()
        assert driver is not None

        # Verify we can execute a simple query
        result = neo4j_connection.execute_query("RETURN 1 as num")
        assert result[0]["num"] == 1

    def test_execute_create_and_match_query(self, clean_neo4j):
        """Test creating and querying nodes."""
        # Create a node
        clean_neo4j.execute_write(
            "CREATE (p:Person {name: $name, age: $age})",
            {"name": "Alice", "age": 30},
        )

        # Query the node
        result = clean_neo4j.execute_query(
            "MATCH (p:Person {name: $name}) RETURN p.name as name, p.age as age",
            {"name": "Alice"},
        )

        assert len(result) == 1
        assert result[0]["name"] == "Alice"
        assert result[0]["age"] == 30

    def test_get_node_count(self, clean_neo4j, sample_graph_data):
        """Test getting node count."""
        # Create sample data
        clean_neo4j.execute_write(sample_graph_data["create_query"])

        # Get count
        count = clean_neo4j.get_node_count()
        assert count == sample_graph_data["expected_nodes"]

    def test_get_relationship_count(self, clean_neo4j, sample_graph_data):
        """Test getting relationship count."""
        # Create sample data
        clean_neo4j.execute_write(sample_graph_data["create_query"])

        # Get count
        count = clean_neo4j.get_relationship_count()
        assert count == sample_graph_data["expected_relationships"]

    def test_clear_database(self, connected_neo4j):
        """Test clearing database."""
        # Create some data
        connected_neo4j.execute_write("CREATE (p:Person {name: 'Test'})")

        # Verify data exists
        assert connected_neo4j.get_node_count() > 0

        # Clear database
        connected_neo4j.clear_database()

        # Verify database is empty
        assert connected_neo4j.get_node_count() == 0

    def test_context_manager_integration(self, neo4j_credentials):
        """Test using connection as context manager."""
        with Neo4jConnection(**neo4j_credentials) as conn:
            result = conn.execute_query("RETURN 1 as num")
            assert result[0]["num"] == 1

        # Connection should be closed after context
        assert conn._driver is None


class TestHealthCheckerIntegration:
    """Integration tests for HealthChecker."""

    def test_check_connectivity_real_database(self, connected_neo4j, health_checker):
        """Test connectivity check with real database."""
        result = health_checker.check_connectivity()
        assert result is True

    def test_check_apoc_available_real_database(self, connected_neo4j, health_checker):
        """Test APOC availability check with real database."""
        result = health_checker.check_apoc_available()
        # Should be True if APOC is properly configured
        assert isinstance(result, bool)

    def test_get_version_real_database(self, connected_neo4j, health_checker):
        """Test getting Neo4j version from real database."""
        version = health_checker.get_version()
        assert version != "unknown"
        assert "2025" in version or "5." in version  # Neo4j version format

    def test_get_database_stats_real_database(self, clean_neo4j, health_checker, sample_graph_data):
        """Test getting database statistics from real database."""
        # Create sample data
        clean_neo4j.execute_write(sample_graph_data["create_query"])

        # Get stats
        stats = health_checker.get_database_stats()

        assert stats["node_count"] == sample_graph_data["expected_nodes"]
        assert stats["relationship_count"] == sample_graph_data["expected_relationships"]
        assert "Person" in stats["labels"]
        assert "Company" in stats["labels"]

    def test_full_health_check_real_database(self, connected_neo4j, health_checker):
        """Test full health check with real database."""
        health = health_checker.full_health_check()

        assert health["connected"] is True
        assert "version" in health
        assert health["version"] != "unknown"
        assert "stats" in health
        assert "error" not in health


class TestTransactionsIntegration:
    """Integration tests for transaction handling."""

    def test_transaction_rollback_on_error(self, clean_neo4j):
        """Test that transactions rollback on error."""
        initial_count = clean_neo4j.get_node_count()

        try:
            # This should fail due to syntax error
            clean_neo4j.execute_write("INVALID CYPHER QUERY")
        except Exception:
            pass

        # Count should remain unchanged
        final_count = clean_neo4j.get_node_count()
        assert final_count == initial_count

    def test_multiple_operations_in_transaction(self, clean_neo4j):
        """Test multiple operations in a single transaction."""
        query = """
        CREATE (p1:Person {name: 'Alice'})
        CREATE (p2:Person {name: 'Bob'})
        CREATE (p1)-[:KNOWS]->(p2)
        RETURN p1, p2
        """

        result = clean_neo4j.execute_write(query)
        assert len(result) == 1

        # Verify both nodes were created
        assert clean_neo4j.get_node_count() == 2
        assert clean_neo4j.get_relationship_count() == 1


class TestComplexQueries:
    """Integration tests for complex Cypher queries."""

    def test_aggregation_query(self, clean_neo4j):
        """Test aggregation queries."""
        # Create test data
        for i in range(5):
            clean_neo4j.execute_write(
                "CREATE (p:Person {name: $name, age: $age})",
                {"name": f"Person{i}", "age": 20 + i},
            )

        # Aggregate query
        result = clean_neo4j.execute_query(
            "MATCH (p:Person) RETURN avg(p.age) as avg_age, count(p) as total"
        )

        assert result[0]["total"] == 5
        assert result[0]["avg_age"] == 22.0  # (20+21+22+23+24)/5

    def test_pattern_matching_query(self, clean_neo4j, sample_graph_data):
        """Test pattern matching queries."""
        # Create sample data
        clean_neo4j.execute_write(sample_graph_data["create_query"])

        # Pattern match: People who work at companies
        result = clean_neo4j.execute_query(
            """
            MATCH (p:Person)-[:WORKS_AT]->(c:Company)
            RETURN p.name as person, c.name as company
            ORDER BY p.name
        """
        )

        assert len(result) == 2
        assert result[0]["company"] == "TechCorp"
        assert result[1]["company"] == "TechCorp"

    def test_path_query(self, clean_neo4j, sample_graph_data):
        """Test path-based queries."""
        # Create sample data
        clean_neo4j.execute_write(sample_graph_data["create_query"])

        # Find path length
        result = clean_neo4j.execute_query(
            """
            MATCH path = (p1:Person {name: 'Alice'})-[:KNOWS*]-(p2:Person {name: 'Charlie'})
            RETURN length(path) as path_length
            ORDER BY path_length
            LIMIT 1
        """
        )

        assert len(result) > 0
        assert result[0]["path_length"] >= 2  # Alice -> Bob -> Charlie
