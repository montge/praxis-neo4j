# Setup Guide

## Quick Setup for Development

### 1. Install Python Dependencies

```bash
# Activate your virtual environment (if using one)
source .venv/bin/activate  # or: .venv/Scripts/activate on Windows

# Install all dependencies
pip install -r requirements.txt

# Or install in development mode with extras
pip install -e ".[dev]"
```

### 2. Start Neo4j

```bash
# Fix permissions (important for WSL)
./scripts/fix-permissions.sh

# Start Neo4j
./scripts/start.sh

# Or use Make
make docker-up
```

### 3. Verify Installation

```bash
# Test Python imports
python3 -c "from src.neo4j_manager import Neo4jConnection; print('✓ Imports OK')"

# Run unit tests (no Neo4j needed)
make test-unit

# Run integration tests (Neo4j must be running)
make test-integration

# Run all tests
make test-all
```

### 4. Environment Configuration

Create a `.env` file (or it will be auto-created):

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=yourpassword
```

## Running Tests Locally

### Unit Tests (Fast - No Dependencies)
```bash
pytest tests/unit/ -v
# or
make test-unit
```

### Integration Tests (Requires Neo4j)
```bash
# Start Neo4j first
make docker-up

# Run tests
pytest tests/integration/ -v
# or
make test-integration
```

### E2E Tests (Requires Neo4j)
```bash
# Start Neo4j first
make docker-up

# Run tests
pytest tests/e2e/ -v
# or
make test-e2e
```

### All Tests with Coverage
```bash
make test-all
make coverage  # Opens HTML report
```

## Code Quality Checks

```bash
# Format code
make format

# Run linters
make lint

# Or manually:
black src/ tests/
flake8 src/ tests/
mypy src/
```

## Common Tasks

### Working with Neo4j
```bash
# Start
make docker-up

# Stop
make docker-down

# View logs
make docker-logs

# Open shell
make docker-shell
```

### Using Python API
```python
from src.neo4j_manager import Neo4jConnection, HealthChecker

# Simple connection
with Neo4jConnection() as conn:
    result = conn.execute_query("RETURN 1 as num")
    print(result)  # [{'num': 1}]

# Health check
with Neo4jConnection() as conn:
    checker = HealthChecker(conn)
    health = checker.full_health_check()
    print(f"Connected: {health['connected']}")
    print(f"APOC Available: {health['apoc_available']}")
```

## Troubleshooting

### Module Not Found
```bash
# Ensure you've installed dependencies
pip install -r requirements.txt

# Check PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Neo4j Connection Issues
```bash
# Check Neo4j is running
docker compose ps

# Check logs
docker compose logs neo4j --tail 50

# Restart Neo4j
make docker-down
make docker-up
```

### Permission Issues (WSL)
```bash
# Run fix script
./scripts/fix-permissions.sh

# Or manually
sudo chown -R $(id -u):$(id -g) data/ logs/ plugins/
```

## CI/CD Setup

GitHub Actions automatically runs tests on:
- Push to `main` or `develop`
- Pull requests
- Manual workflow dispatch

No additional setup needed - just push to GitHub!

## Next Steps

1. Review the test examples in `tests/` directories
2. Read `CLAUDE.md` for architectural overview
3. Check `README.md` for detailed testing documentation
4. Start writing your thesis code with TDD practices!
