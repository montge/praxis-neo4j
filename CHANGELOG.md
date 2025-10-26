# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2025-10-26

### Added
- **Test-Driven Development Infrastructure**
  - Comprehensive test suite with unit, integration, and e2e tests
  - Test coverage reporting with pytest-cov
  - Test fixtures for common Neo4j operations (conftest.py)
  - Pytest markers for organizing tests (unit, integration, e2e, slow, apoc)

- **Python API Package** (`src/neo4j_manager/`)
  - `Neo4jConnection`: Connection management with context manager support
  - `HealthChecker`: Database health monitoring and APOC verification
  - `BackupManager`: Backup and restore operations (GraphML via APOC)
  - Type hints and comprehensive docstrings throughout
  - Proper exception handling and logging

- **GitHub Actions CI/CD Pipeline**
  - Automated unit tests (fast, no dependencies)
  - Integration tests with Neo4j service container
  - End-to-end workflow tests
  - Code quality checks (Black, Flake8, mypy)
  - Coverage reporting to Codecov
  - Runs on push to main/develop and on pull requests

- **Development Tools**
  - Makefile with common commands (test, lint, format, docker management)
  - pyproject.toml for project configuration
  - pytest.ini for test configuration
  - .flake8 for linting rules
  - .env.test template for test environment variables

- **Documentation**
  - Comprehensive testing guide in README.md
  - Python API usage examples
  - Updated CLAUDE.md with testing architecture
  - TDD best practices and guidelines

### Changed
- **Updated Dependencies**
  - Neo4j Docker image: 2025.03.0 → 2025.09.0
  - APOC plugin: 2025.03.0 → 2025.09.0
  - Python neo4j driver: Updated to >=5.26.0
  - Added comprehensive testing dependencies

- **Enhanced Documentation**
  - README.md now includes testing instructions
  - Added Python API usage examples
  - Documented CI/CD pipeline
  - Added development workflow guidelines

### Technical Details

**Test Statistics:**
- 3 test categories: unit, integration, e2e
- 20+ test files covering core functionality
- Fixtures for Neo4j connection, health checks, and backup operations
- Mock-based unit tests for isolated testing

**Code Quality:**
- Self-documenting code with type hints
- 100-character line length (Black formatter)
- Flake8 linting with project-specific rules
- mypy type checking for Python 3.11+

**CI/CD:**
- 4 parallel jobs: unit tests, integration tests, e2e tests, code quality
- Neo4j service containers for integration testing
- Automatic APOC plugin installation in CI
- Coverage reporting integration

## [1.0.0] - Initial Release

### Added
- Basic Neo4j Docker Compose setup
- Shell scripts for starting, stopping, and managing Neo4j
- APOC plugin auto-download and configuration
- Backup and restore scripts using GraphML
- WSL-compatible permission handling
- Environment-based configuration
