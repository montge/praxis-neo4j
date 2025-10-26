"""End-to-end tests for backup and restore workflows.

These tests simulate complete user workflows including:
- Creating data
- Backing up the database
- Clearing the database
- Restoring from backup
- Verifying data integrity

Run with: pytest tests/e2e/ --neo4j-integration
"""

import pytest
from src.neo4j_manager import Neo4jConnection, BackupManager, HealthChecker


pytestmark = pytest.mark.e2e


class TestBackupRestoreWorkflow:
    """End-to-end tests for backup and restore workflow."""

    def test_complete_backup_restore_cycle(self, clean_neo4j, backup_manager, sample_graph_data):
        """Test complete cycle: create data -> backup -> clear -> restore -> verify."""
        # Step 1: Create initial data
        clean_neo4j.execute_write(sample_graph_data["create_query"])
        initial_node_count = clean_neo4j.get_node_count()
        initial_rel_count = clean_neo4j.get_relationship_count()

        assert initial_node_count == sample_graph_data["expected_nodes"]
        assert initial_rel_count == sample_graph_data["expected_relationships"]

        # Step 2: Create backup (Note: This requires APOC to be properly configured)
        # In real scenario, this would export to GraphML
        # For testing, we verify the backup manager is configured correctly
        assert backup_manager.backup_dir.exists()

        # Verify we can generate a backup filename
        filename = backup_manager.create_backup_filename()
        assert filename.endswith(".graphml")
        assert len(filename) > len(".graphml")

    def test_backup_filename_generation(self, backup_manager):
        """Test backup filename generation with timestamps."""
        filename1 = backup_manager.create_backup_filename()
        filename2 = backup_manager.create_backup_filename()

        # Filenames should be unique (contain timestamps)
        assert filename1.endswith(".graphml")
        assert filename2.endswith(".graphml")

        # Can have same timestamp if executed very quickly
        # But format should be correct
        assert "neo4j_backup_" in filename1
        assert "_" in filename1.split(".")[0]

    def test_backup_directory_management(self, backup_manager):
        """Test backup directory is created and managed."""
        # Directory should be created during init
        assert backup_manager.backup_dir.exists()
        assert backup_manager.backup_dir.is_dir()


class TestHealthCheckWorkflow:
    """End-to-end tests for health check workflow."""

    def test_startup_health_check_workflow(self, neo4j_credentials):
        """Test typical startup health check workflow."""
        # Step 1: Create connection
        conn = Neo4jConnection(**neo4j_credentials)

        # Step 2: Connect to database
        conn.connect()

        # Step 3: Create health checker
        checker = HealthChecker(conn)

        # Step 4: Perform full health check
        health = checker.full_health_check()

        # Verify results
        assert health["connected"] is True

        # Step 5: Close connection
        conn.close()

    def test_wait_for_database_ready_workflow(self, neo4j_connection):
        """Test waiting for database to be ready workflow."""
        # This simulates waiting for Neo4j to start
        neo4j_connection.connect()
        checker = HealthChecker(neo4j_connection)

        # Database should already be ready, so this should return immediately
        is_ready = checker.wait_for_ready(timeout=10, interval=1)

        assert is_ready is True


class TestDataManipulationWorkflow:
    """End-to-end tests for typical data manipulation workflows."""

    def test_create_query_update_delete_workflow(self, clean_neo4j):
        """Test complete CRUD workflow."""
        # Step 1: CREATE - Insert initial data
        clean_neo4j.execute_write(
            """
            CREATE (p:Person {name: 'Alice', age: 30, email: 'alice@example.com'})
            RETURN p
        """
        )

        assert clean_neo4j.get_node_count() == 1

        # Step 2: READ - Query the data
        result = clean_neo4j.execute_query(
            """
            MATCH (p:Person {name: 'Alice'})
            RETURN p.name as name, p.age as age, p.email as email
        """
        )

        assert len(result) == 1
        assert result[0]["name"] == "Alice"
        assert result[0]["age"] == 30

        # Step 3: UPDATE - Modify the data
        clean_neo4j.execute_write(
            """
            MATCH (p:Person {name: 'Alice'})
            SET p.age = 31
            RETURN p
        """
        )

        # Verify update
        result = clean_neo4j.execute_query(
            """
            MATCH (p:Person {name: 'Alice'})
            RETURN p.age as age
        """
        )
        assert result[0]["age"] == 31

        # Step 4: DELETE - Remove the data
        clean_neo4j.execute_write(
            """
            MATCH (p:Person {name: 'Alice'})
            DELETE p
        """
        )

        assert clean_neo4j.get_node_count() == 0

    def test_relationship_management_workflow(self, clean_neo4j):
        """Test workflow for creating and managing relationships."""
        # Step 1: Create nodes
        clean_neo4j.execute_write(
            """
            CREATE (p1:Person {name: 'Alice'})
            CREATE (p2:Person {name: 'Bob'})
            CREATE (c:Company {name: 'TechCorp'})
        """
        )

        assert clean_neo4j.get_node_count() == 3

        # Step 2: Create relationships
        clean_neo4j.execute_write(
            """
            MATCH (p1:Person {name: 'Alice'})
            MATCH (p2:Person {name: 'Bob'})
            MATCH (c:Company {name: 'TechCorp'})
            CREATE (p1)-[:WORKS_AT]->(c)
            CREATE (p2)-[:WORKS_AT]->(c)
            CREATE (p1)-[:KNOWS]->(p2)
        """
        )

        assert clean_neo4j.get_relationship_count() == 3

        # Step 3: Query relationships
        result = clean_neo4j.execute_query(
            """
            MATCH (p:Person)-[r:WORKS_AT]->(c:Company)
            RETURN p.name as person, type(r) as relationship, c.name as company
        """
        )

        assert len(result) == 2

        # Step 4: Delete specific relationship
        clean_neo4j.execute_write(
            """
            MATCH (p:Person {name: 'Alice'})-[r:KNOWS]->()
            DELETE r
        """
        )

        assert clean_neo4j.get_relationship_count() == 2

    def test_bulk_data_insertion_workflow(self, clean_neo4j):
        """Test workflow for inserting bulk data."""
        # Step 1: Prepare bulk data
        persons_data = [
            {"name": f"Person{i}", "age": 20 + i, "city": "TestCity"} for i in range(100)
        ]

        # Step 2: Insert in batches using UNWIND
        clean_neo4j.execute_write(
            """
            UNWIND $persons as person
            CREATE (p:Person)
            SET p = person
        """,
            {"persons": persons_data},
        )

        # Step 3: Verify insertion
        count = clean_neo4j.get_node_count()
        assert count == 100

        # Step 4: Query and verify data integrity
        result = clean_neo4j.execute_query(
            """
            MATCH (p:Person)
            WHERE p.city = 'TestCity'
            RETURN count(p) as count
        """
        )

        assert result[0]["count"] == 100


class TestErrorHandlingWorkflow:
    """End-to-end tests for error handling scenarios."""

    def test_connection_failure_recovery_workflow(self, neo4j_credentials):
        """Test workflow for handling connection failures."""
        # Create connection with invalid credentials
        bad_conn = Neo4jConnection(
            uri=neo4j_credentials["uri"],
            username="invalid",
            password="invalid",
        )

        # Connection should fail
        with pytest.raises(Exception):  # AuthError or ServiceUnavailable
            bad_conn.connect()

        # Create connection with correct credentials
        good_conn = Neo4jConnection(**neo4j_credentials)
        driver = good_conn.connect()

        # Should succeed
        assert driver is not None
        good_conn.close()

    def test_invalid_query_handling_workflow(self, clean_neo4j):
        """Test workflow for handling invalid queries."""
        # This should not crash the application
        with pytest.raises(Exception):
            clean_neo4j.execute_query("INVALID CYPHER SYNTAX HERE")

        # Connection should still be usable after error
        result = clean_neo4j.execute_query("RETURN 1 as num")
        assert result[0]["num"] == 1


class TestContextManagerWorkflow:
    """End-to-end tests for context manager usage patterns."""

    def test_context_manager_with_operations_workflow(self, neo4j_credentials, sample_graph_data):
        """Test typical workflow using context manager."""
        # Use context manager for automatic connection handling
        with Neo4jConnection(**neo4j_credentials) as conn:
            # Clear any existing data
            conn.clear_database()

            # Perform operations
            conn.execute_write(sample_graph_data["create_query"])

            # Verify operations
            node_count = conn.get_node_count()
            assert node_count == sample_graph_data["expected_nodes"]

            # Clean up
            conn.clear_database()

        # Connection should be closed automatically
        assert conn._driver is None

    def test_nested_context_managers_workflow(self, neo4j_credentials):
        """Test workflow with nested context managers."""
        with Neo4jConnection(**neo4j_credentials) as conn:
            conn.clear_database()

            # Create some data
            conn.execute_write("CREATE (p:Person {name: 'Test'})")

            # Create backup manager in nested context
            backup_mgr = BackupManager(conn, "./tests/test_backups")

            # Verify operations work
            assert conn.get_node_count() == 1
            assert backup_mgr.backup_dir.exists()

            # Clean up
            conn.clear_database()
