"""Pytest configuration and shared fixtures."""

import os
import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase
from src.neo4j_manager import Neo4jConnection, BackupManager, HealthChecker

# Load environment variables
load_dotenv()


@pytest.fixture(scope="session")
def neo4j_uri():
    """Get Neo4j URI from environment."""
    return os.getenv("NEO4J_URI", "bolt://localhost:7687")


@pytest.fixture(scope="session")
def neo4j_username():
    """Get Neo4j username from environment."""
    return os.getenv("NEO4J_USERNAME", "neo4j")


@pytest.fixture(scope="session")
def neo4j_password():
    """Get Neo4j password from environment."""
    return os.getenv("NEO4J_PASSWORD", "yourpassword")


@pytest.fixture(scope="session")
def neo4j_credentials(neo4j_uri, neo4j_username, neo4j_password):
    """Return Neo4j credentials as a dictionary."""
    return {
        "uri": neo4j_uri,
        "username": neo4j_username,
        "password": neo4j_password,
    }


@pytest.fixture
def neo4j_connection(neo4j_uri, neo4j_username, neo4j_password):
    """Create a Neo4j connection (function scope - new for each test)."""
    connection = Neo4jConnection(uri=neo4j_uri, username=neo4j_username, password=neo4j_password)
    yield connection
    connection.close()


@pytest.fixture
def connected_neo4j(neo4j_connection):
    """Create and connect to Neo4j."""
    neo4j_connection.connect()
    yield neo4j_connection


@pytest.fixture
def clean_neo4j(connected_neo4j):
    """
    Provide a clean Neo4j database for testing.
    Clears database before and after test.
    """
    # Clear before test
    connected_neo4j.clear_database()
    yield connected_neo4j
    # Clear after test
    connected_neo4j.clear_database()


@pytest.fixture
def health_checker(neo4j_connection):
    """Create a HealthChecker instance."""
    return HealthChecker(neo4j_connection)


@pytest.fixture
def backup_manager(neo4j_connection):
    """Create a BackupManager instance."""
    return BackupManager(neo4j_connection, backup_dir="./tests/test_backups")


@pytest.fixture
def sample_graph_data():
    """Provide sample graph data for testing."""
    return {
        "create_query": """
            CREATE (p1:Person {name: 'Alice', age: 30})
            CREATE (p2:Person {name: 'Bob', age: 25})
            CREATE (p3:Person {name: 'Charlie', age: 35})
            CREATE (c:Company {name: 'TechCorp'})
            CREATE (p1)-[:WORKS_AT]->(c)
            CREATE (p2)-[:WORKS_AT]->(c)
            CREATE (p1)-[:KNOWS]->(p2)
            CREATE (p2)-[:KNOWS]->(p3)
        """,
        "expected_nodes": 4,
        "expected_relationships": 4,
    }


@pytest.fixture(autouse=True)
def cleanup_test_backups():
    """Clean up test backup files after each test."""
    yield
    # Cleanup after test
    import shutil
    from pathlib import Path

    test_backup_dir = Path("./tests/test_backups")
    if test_backup_dir.exists():
        shutil.rmtree(test_backup_dir)
