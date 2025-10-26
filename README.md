# Neo4j with APOC - Simplified Setup

[![CI/CD](https://github.com/montge/praxis-neo4j/actions/workflows/test.yml/badge.svg)](https://github.com/montge/praxis-neo4j/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-98%25-brightgreen.svg)](https://github.com/montge/praxis-neo4j)
[![Neo4j 2025.09.0](https://img.shields.io/badge/Neo4j-2025.09.0-008CC1.svg)](https://neo4j.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This repository contains scripts to simplify the setup and management of Neo4j with APOC for thesis work, featuring comprehensive test-driven development practices with unit, integration, and end-to-end testing.

## Requirements

- Docker and Docker Compose
- Bash shell
- **Python 3.11, 3.12, 3.13, or 3.14** (supported versions, required for Python modules and testing)
- Make (optional, for convenience commands)

### Python Version Support

This project supports Python 3.11 through 3.14:
- ✅ **Python 3.11.x** (LTS until October 2027)
- ✅ **Python 3.12.x** (LTS until October 2028)
- ✅ **Python 3.13.x** (Released October 2024, LTS until October 2029)
- ✅ **Python 3.14.x** (Latest, released October 2025)

All tests run against all four versions in CI/CD.

## Quick Start

### Starting Neo4j

```bash
# Fix permissions first (helps with WSL environments)
./scripts/fix-permissions.sh

# Start Neo4j with APOC
./scripts/start.sh
```

This will:
1. Fix permissions on directories used by Neo4j
2. Set up the APOC plugin (version 2025.09.0)
3. Start Neo4j container (version 2025.09.0)
4. Wait for Neo4j to be healthy
5. Verify APOC installation
6. Display connection information

### Stopping Neo4j

Option 1: Use the stop option in the start script:
```bash
./scripts/start.sh --stop
```

Option 2: Use the dedicated stop script:
```bash
./scripts/stop.sh
```

Option 3: Use Docker Compose directly:
```bash
docker compose down
```

### Neo4j Connection Information

- **Web Interface**: http://localhost:7474
- **Bolt URI**: bolt://localhost:7687
- **Username**: neo4j (configurable in .env file)
- **Password**: yourpassword (configurable in .env file)

## Configuration

The setup uses environment variables stored in a `.env` file for configuration. This file is created automatically when you run `fix-permissions.sh` or `start.sh`.

### Default Environment Variables

```
# Neo4j Authentication
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=yourpassword
NEO4J_AUTH=${NEO4J_USERNAME}/${NEO4J_PASSWORD}

# User and Group IDs for container permissions
USER_ID=1002  # This will be your actual user ID
GROUP_ID=1002 # This will be your actual group ID

# Neo4j Configuration
# Memory settings
NEO4J_HEAP_MEMORY_INITIAL=4G
NEO4J_HEAP_MEMORY_MAX=4G
NEO4J_PAGE_CACHE=2G
```

### Customizing Configuration

You can modify these settings by editing the `.env` file directly. For example, to change the Neo4j password:

1. Edit the `.env` file:
```bash
# Change this line
NEO4J_PASSWORD=yournewpassword
```

2. Restart Neo4j:
```bash
./scripts/start.sh --stop
./scripts/start.sh
```

## Directory Structure

- `scripts/` - Contains utility scripts
  - `start.sh` - Main script for starting Neo4j with APOC
  - `stop.sh` - Script to stop Neo4j
  - `fix-permissions.sh` - Script to fix permissions for Neo4j directories
  - `restore_backup.sh` - Script for restoring Neo4j backups (if needed)
- `plugins/` - Directory for Neo4j plugins (APOC is stored here)
- `data/` - Neo4j data directory
- `logs/` - Neo4j logs
- `.env` - Environment variables for configuration
- `.env.example` - Example environment file for reference

## Troubleshooting

### Permission Issues

If you encounter permission issues when setting up APOC, try these solutions:

1. Run the permission fix script:
```bash
./scripts/fix-permissions.sh
```

2. Manually fix permissions:
```bash
sudo chown -R $(id -u):$(id -g) plugins/ data/ logs/
sudo chmod -R 755 plugins/ data/ logs/
```

3. For WSL environments, ensure the directories are on Linux file system, not the Windows mount.

### APOC Verification Failed

If APOC verification fails, check that:
1. The plugins directory is correctly mounted in `docker-compose.yml`
2. The APOC plugin file exists and is accessible
3. The APOC version (2025.03.0) is compatible with Neo4j version (2025.03.0)

### Invalid Username/Password

If you cannot log in to Neo4j, check:
1. The values in your `.env` file match what you're using to connect
2. If you've changed the password, make sure you've restarted Neo4j afterward

## Python Development

### Installation

```bash
# Create and activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install with development dependencies
pip install -e ".[dev]"
```

### Using the Python API

```python
from src.neo4j_manager import Neo4jConnection, HealthChecker, BackupManager

# Connect to Neo4j
with Neo4jConnection(uri="bolt://localhost:7687",
                     username="neo4j",
                     password="yourpassword") as conn:
    # Execute queries
    result = conn.execute_query("MATCH (n) RETURN count(n) as count")
    print(f"Node count: {result[0]['count']}")

    # Health checks
    checker = HealthChecker(conn)
    health = checker.full_health_check()
    print(f"Connected: {health['connected']}")
    print(f"APOC Available: {health['apoc_available']}")

    # Backup operations
    backup_mgr = BackupManager(conn)
    # backup_mgr.export_to_graphml()  # Requires APOC
```

## Testing

This project follows test-driven development practices with comprehensive test coverage.

### Coverage Requirements

- **Minimum per module**: 80%
- **Overall target**: 95%
- **Current coverage**: 98% ✅

All modules exceed the 80% minimum threshold.

### Test Structure

- **Unit Tests** (`tests/unit/`): Fast, isolated tests with mocked dependencies
- **Integration Tests** (`tests/integration/`): Tests requiring Neo4j instance
- **End-to-End Tests** (`tests/e2e/`): Full workflow tests

### Running Tests

#### Using Make (Recommended)

```bash
# Run unit tests only (fast, no Neo4j needed)
make test-unit

# Run integration tests (requires Neo4j running)
make test-integration

# Run end-to-end tests (requires Neo4j running)
make test-e2e

# Run all tests
make test-all

# Generate coverage report
make coverage

# Run code quality checks
make lint

# Format code
make format
```

#### Using pytest directly

```bash
# Run unit tests only
pytest tests/unit/ -v

# Run integration tests (Neo4j must be running)
pytest tests/integration/ -v

# Run e2e tests (Neo4j must be running)
pytest tests/e2e/ -v

# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run tests by marker
pytest -m unit  # Unit tests only
pytest -m integration  # Integration tests only
pytest -m e2e  # E2E tests only
```

### Continuous Integration

Tests run automatically on GitHub Actions for:
- Every push to `main` or `develop` branches
- Every pull request
- Manual workflow dispatch

The CI pipeline includes:
1. **Unit Tests**: Fast tests with no external dependencies
2. **Integration Tests**: Tests with Neo4j service container
3. **E2E Tests**: Complete workflow tests
4. **Code Quality**: Black, Flake8, and mypy checks

### Test Configuration

- `pytest.ini`: Pytest configuration and markers
- `pyproject.toml`: Black, mypy, and project configuration
- `.env.test`: Test environment variables template
- `tests/conftest.py`: Shared fixtures and test utilities

### Writing Tests

When adding new functionality, follow TDD practices:

1. Write tests first (unit → integration → e2e)
2. Use descriptive test names following `test_<what>_<condition>` pattern
3. Follow AAA pattern: Arrange → Act → Assert
4. Use appropriate fixtures from `conftest.py`
5. Mark tests with appropriate markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`

Example:
```python
import pytest

@pytest.mark.unit
def test_connection_initialization_with_defaults():
    """Test Neo4jConnection initializes with default values."""
    conn = Neo4jConnection()
    assert conn.uri == "bolt://localhost:7687"
    assert conn.username == "neo4j"
```

## Advanced Usage

For other options and help:

```bash
./scripts/start.sh --help
```

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### Third-Party Software

This project uses the following third-party software:
- **Neo4j Community Edition** (GPLv3) - Not redistributed, used as external database
- **APOC** (Apache 2.0) - Not redistributed, downloaded during setup
- **Neo4j Python Driver** (Apache 2.0)

See [NOTICE](NOTICE) file for complete attribution.

## Attribution

This project includes code that was generated or assisted by [Claude Code](https://claude.com/claude-code) and [Cursor AI](https://cursor.ai/) tools.
