# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Neo4j database setup repository for thesis work, using Docker Compose to run Neo4j 2025.09.0 with the APOC plugin. The project features:
- Simplified Neo4j setup and management designed for WSL environments
- Comprehensive test-driven development with unit, integration, and e2e tests
- Python API for Neo4j operations (connection, health checks, backup/restore)
- GitHub Actions CI/CD pipeline
- Backup/restore capabilities using APOC GraphML export

## Essential Commands

### Quick Commands (Make)

```bash
make help              # Show all available commands
make test-unit         # Run unit tests (fast)
make test-integration  # Run integration tests
make test-all          # Run all tests
make coverage          # Generate coverage report
make lint              # Run code quality checks
make format            # Format code with black
make docker-up         # Start Neo4j
make docker-down       # Stop Neo4j
```

### Starting and Stopping Neo4j

```bash
# Fix permissions first (important for WSL)
./scripts/fix-permissions.sh

# Start Neo4j with APOC
./scripts/start.sh

# Stop Neo4j
./scripts/stop.sh
# OR
./scripts/start.sh --stop
# OR
docker compose down
```

### Backup and Restore

```bash
# Create a backup (creates timestamped .graphml.gz file in ./backup/)
./scripts/create_backup.sh

# Restore from backup
./scripts/restore_backup.sh <backup_file.gz>
```

### Docker Operations

```bash
# View logs
docker compose logs neo4j

# View last 50 lines
docker compose logs neo4j --tail 50

# Check container status
docker compose ps

# Execute cypher-shell in container
docker exec $(docker compose ps -q neo4j) cypher-shell -u neo4j -p yourpassword "MATCH (n) RETURN count(n)"
```

## Testing Architecture

### Test Organization
The project follows TDD practices with three test levels:

1. **Unit Tests** (`tests/unit/`)
   - Fast, isolated tests with mocked dependencies
   - No external services required
   - Test individual classes and functions
   - Run with: `pytest tests/unit/` or `make test-unit`

2. **Integration Tests** (`tests/integration/`)
   - Require running Neo4j instance
   - Test actual database operations
   - Verify APOC functionality
   - Run with: `pytest tests/integration/` or `make test-integration`

3. **End-to-End Tests** (`tests/e2e/`)
   - Test complete workflows
   - Simulate real user scenarios
   - Test backup/restore cycles, CRUD operations
   - Run with: `pytest tests/e2e/` or `make test-e2e`

### Test Fixtures (conftest.py)
Common fixtures available to all tests:
- `neo4j_connection`: Fresh connection instance
- `connected_neo4j`: Connected instance
- `clean_neo4j`: Clean database (cleared before/after test)
- `health_checker`: HealthChecker instance
- `backup_manager`: BackupManager instance
- `sample_graph_data`: Sample test data

### Python Source Structure
- `src/neo4j_manager/connection.py`: Connection management and query execution
- `src/neo4j_manager/health_check.py`: Health checks and monitoring
- `src/neo4j_manager/backup.py`: Backup/restore operations (requires APOC)

All modules use:
- Type hints for better IDE support
- Comprehensive docstrings (self-documenting code)
- Context managers for resource cleanup
- Proper exception handling

## Architecture

### Docker Setup
- Single Neo4j service defined in `docker-compose.yml`
- Uses Neo4j 2025.09.0 with APOC plugin 2025.09.0
- Configured with memory limits: 8GB total, 4G heap, 2G page cache
- Runs with user/group IDs from `.env` to avoid permission issues
- GitHub Actions uses service containers for CI testing

### Directory Structure
- `scripts/` - Shell scripts for Neo4j management
  - `start.sh` - Main orchestration script (fixes permissions, sets up APOC, starts Neo4j, verifies health)
  - `stop.sh` - Stops the container
  - `fix-permissions.sh` - Fixes permissions on data/logs/plugins and creates/updates `.env` file
  - `create_backup.sh` - Exports database to GraphML format using APOC
  - `restore_backup.sh` - Restores from GraphML backup (includes APOC setup and verification)
- `src/neo4j_manager/` - Python package for Neo4j operations
  - `connection.py` - Connection management and query execution
  - `health_check.py` - Health monitoring utilities
  - `backup.py` - Backup/restore operations
- `tests/` - Test suite (unit, integration, e2e)
- `plugins/` - APOC JAR files (auto-downloaded by start.sh)
- `data/` - Neo4j database files
- `logs/` - Neo4j log files
- `backup/` - Backup files (.graphml.gz format)
- `.env` - Environment configuration (created automatically with user IDs, credentials, memory settings)
- `.github/workflows/test.yml` - CI/CD pipeline configuration

### Configuration via .env
The `.env` file controls:
- `NEO4J_USERNAME` / `NEO4J_PASSWORD` - Database credentials (default: neo4j/yourpassword)
- `USER_ID` / `GROUP_ID` - Container user IDs (auto-set to current user)
- `NEO4J_HEAP_MEMORY_INITIAL` / `NEO4J_HEAP_MEMORY_MAX` - JVM heap size (default: 4G)
- `NEO4J_PAGE_CACHE` - Page cache size (default: 2G)

### Neo4j Connection Information
- Web Interface: http://localhost:7474
- Bolt URI: bolt://localhost:7687
- Default credentials: neo4j/yourpassword (configurable in `.env`)

## Key Implementation Details

### APOC Setup
The `start.sh` script automatically:
1. Downloads APOC 2025.09.0 core JAR if not present
2. Mounts it via Docker volume to container's `/plugins/` directory
3. Configures Neo4j with unrestricted APOC procedures via environment variables
4. Verifies APOC is loaded by running a test query

Note: APOC version MUST match Neo4j version (year.month must be identical)

### Permission Handling
This repository is designed for WSL environments where permission issues are common:
- `fix-permissions.sh` uses sudo where possible but continues if it fails
- Sets ownership to current user's UID/GID
- The `.env` file captures these IDs for Docker container user mapping
- All scripts log warnings instead of failing on permission errors

### Backup Strategy
- Uses APOC's GraphML export (`apoc.export.graphml.all`)
- Backups are timestamped: `neo4j_backup_YYYYMMDD_HHMMSS.graphml.gz`
- Export happens in container's `/var/lib/neo4j/import/` directory
- Files are copied to host's `./backup/` and gzipped
- Restore process:
  1. Stops Neo4j and clears volumes
  2. Starts fresh container and sets up APOC
  3. Copies backup into container
  4. Uses `apoc.import.graphml` with test import first, then full import

### Health Checks
- Docker health check: HTTP probe to port 7474 every 10s
- Start script waits up to 60s for "(healthy)" status
- APOC verification uses `cypher-shell` to test procedure availability

## Development Notes

### Python Dependencies

**Supported Python Versions:** 3.11, 3.12, 3.13, 3.14
- All versions tested in CI/CD matrix
- LTS support until 2027-2029

Core:
- `neo4j>=5.26.0` - Neo4j Python driver
- `python-dotenv>=1.0.1` - Environment variable management

Development/Testing:
- `pytest>=8.3.0` - Test framework
- `pytest-cov>=6.0.0` - Coverage reporting
- `pytest-mock>=3.14.0` - Mocking utilities
- `black>=24.10.0` - Code formatter
- `flake8>=7.1.0` - Linter
- `mypy>=1.13.0` - Type checker

Install with: `pip install -r requirements.txt` or `pip install -e ".[dev]"`

### Virtual Environment
The project assumes a virtual environment at `./.venv` (symlinked to `../../.venv/`). The `start.sh` script will activate it if present.

### WSL Considerations
- Permission issues are expected and handled gracefully
- Scripts prefer `/var/lib/neo4j/` paths inside container
- File operations use explicit error handling for permission failures

### Neo4j Configuration
APOC is enabled via environment variables in `docker-compose.yml`:
- `NEO4J_dbms_security_procedures_unrestricted=apoc.*`
- `NEO4J_apoc_export_file_enabled=true`
- `NEO4J_apoc_import_file_enabled=true`
- `NEO4J_dbms_security_procedures_allowlist=apoc.*`

## Troubleshooting

### If Neo4j fails to start
1. Check logs: `docker compose logs neo4j --tail 50`
2. Verify permissions: `./scripts/fix-permissions.sh`
3. Check memory availability (needs ~8GB)
4. Ensure ports 7474 and 7687 are not in use

### If APOC verification fails
1. Verify plugin file exists: `docker exec $(docker compose ps -q neo4j) ls -l /plugins/`
2. Check Neo4j logs for plugin loading errors
3. Ensure version compatibility (Neo4j 2025.03.0 requires APOC 2025.03.0)
4. Verify volume mount in `docker-compose.yml`

### If backup/restore fails
- Ensure Neo4j is running: `docker compose ps`
- Check credentials in `.env` match what's used in scripts
- For restore: verify backup file is in `./backup/` directory and is valid gzipped GraphML
