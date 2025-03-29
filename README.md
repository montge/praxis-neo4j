# Neo4j with APOC - Simplified Setup

This repository contains scripts to simplify the setup and management of Neo4j with APOC for thesis work.

## Requirements

- Docker and Docker Compose
- Bash shell
- Python environment (optional, for more advanced scripts)

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
2. Set up the APOC plugin (version 2025.03.0)
3. Start Neo4j container (version 2025.03.0)
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

## Advanced Usage

For other options and help:

```bash
./scripts/start.sh --help
```
