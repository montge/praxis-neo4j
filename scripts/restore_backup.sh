#!/bin/bash
# scripts/restore_backup.sh
# Script to restore Neo4j backup from a gzipped GraphML file in the backup directory
# Usage: ./restore_backup.sh <backup_file.gz>

# Set up logging
LOG_FILE="restore.log"
exec 1> >(tee -a "$LOG_FILE") 2>&1

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
handle_error() {
    log "ERROR: $1"
    exit 1
}

# Function to setup APOC
setup_apoc() {
    local container_id=$1
    log "Setting up APOC plugin in container..."
    
    # Configure Neo4j for APOC
    log "Configuring Neo4j for APOC..."
    docker exec $container_id sh -c '
        echo "dbms.security.procedures.unrestricted=apoc.*" >> /var/lib/neo4j/conf/neo4j.conf && \
        echo "server.directories.plugins=/var/lib/neo4j/plugins" >> /var/lib/neo4j/conf/neo4j.conf && \
        echo "dbms.security.procedures.allowlist=apoc.*" >> /var/lib/neo4j/conf/neo4j.conf
    '
    
    # Use a single shell session to handle the download and setup
    docker exec $container_id sh -c '
        cd /var/lib/neo4j/plugins && \
        if [ ! -f apoc-5.26.0-core.jar ]; then
            echo "Downloading APOC plugin..." && \
            wget --no-verbose https://github.com/neo4j/apoc/releases/download/5.26.0/apoc-5.26.0-core.jar && \
            chown neo4j:neo4j apoc-5.26.0-core.jar && \
            chmod 644 apoc-5.26.0-core.jar && \
            echo "APOC plugin downloaded and configured"
        else
            echo "APOC plugin already exists"
        fi && \
        ls -l apoc-5.26.0-core.jar
    ' || handle_error "Failed to setup APOC plugin in container"
    
    # Restart Neo4j to load the plugin
    log "Restarting Neo4j to load APOC plugin..."
    docker compose restart neo4j || handle_error "Failed to restart Neo4j"
    
    # Wait for Neo4j to start
    log "Waiting for Neo4j to initialize..."
    sleep 20
    
    # Check if APOC is loaded with more specific check
    log "Verifying APOC is loaded..."
    if ! docker exec $container_id cypher-shell -u neo4j -p yourpassword \
        "CALL apoc.help('graphml') YIELD name WHERE name = 'apoc.import.graphml' RETURN count(*) as count" | grep -q "1"; then
        log "ERROR: APOC graphml import not available. Checking Neo4j logs..."
        docker exec $container_id sh -c '
            echo "=== Neo4j Logs ===" && \
            tail -n 50 /logs/neo4j.log && \
            echo "=== Plugin Directory Contents ===" && \
            ls -l /var/lib/neo4j/plugins/ && \
            echo "=== Neo4j Config ===" && \
            cat /var/lib/neo4j/conf/neo4j.conf
        ' || true
        handle_error "APOC graphml import not available. Check logs above for details."
    fi
    
    log "APOC setup completed successfully"
}

# Function to verify APOC installation
verify_apoc() {
    local container_id=$1
    
    log "Verifying APOC installation..."
    
    # Check if plugin exists in container
    log "Checking APOC plugin in container..."
    if ! docker exec $container_id sh -c 'test -f /var/lib/neo4j/plugins/apoc-5.26.0-core.jar'; then
        setup_apoc "$container_id"
    fi
    
    # Check Neo4j configuration
    log "Checking Neo4j plugin configuration..."
    docker exec $container_id sh -c '
        echo "=== Plugin Directory Contents ===" && \
        ls -l /var/lib/neo4j/plugins/ && \
        echo "=== Neo4j Plugin Settings ===" && \
        grep -i "plugin" /var/lib/neo4j/conf/neo4j.conf || echo "No plugin settings found"
    '
    
    # List available APOC procedures
    log "Listing available APOC procedures..."
    docker exec $container_id cypher-shell -u neo4j -p yourpassword \
        "SHOW PROCEDURES YIELD name WHERE name CONTAINS 'apoc' RETURN name ORDER BY name LIMIT 5" || \
        handle_error "Cannot list APOC procedures. Plugin may not be loaded correctly."
    
    log "APOC verification successful"
}

# Function to check Python dependencies
check_python_dependencies() {
    if ! command -v pip3 &> /dev/null; then
        log "ERROR: pip3 is not installed. Please install it with:"
        log "    sudo apt-get update && sudo apt-get install -y python3-pip"
        handle_error "Missing pip3. Please install it and try again."
    fi
    
    if ! python3 -c "import neo4j" &> /dev/null; then
        log "Installing neo4j-driver..."
        pip3 install --user neo4j || {
            log "Failed to install neo4j-driver with --user flag. Trying without..."
            pip3 install neo4j || handle_error "Failed to install neo4j-driver. Try: pip3 install --user neo4j"
        }
    fi
}

# Function to get container ID by service name
get_container_id() {
    local service_name=$1
    local container_id=$(docker compose ps -q $service_name)
    echo $container_id
}

# Function to cleanup temporary files
cleanup() {
    log "Cleaning up temporary files..."
    if [ -f "$TEMP_UNZIPPED_FILE" ]; then
        rm -f "$TEMP_UNZIPPED_FILE"
    fi
}

# Function to create and import test sample
test_import() {
    local container_id=$1
    local import_path=$2
    
    log "Creating test sample from GraphML file..."
    
    # Create a sample GraphML file with just a few nodes and edges
    docker exec $container_id sh -c "
        # Extract header
        head -n 20 /var/lib/neo4j/import/$import_path > /var/lib/neo4j/import/test_sample.graphml && \
        # Add a few nodes (first 5)
        grep -m 5 -A 1 '<node' /var/lib/neo4j/import/$import_path >> /var/lib/neo4j/import/test_sample.graphml && \
        # Add a few edges (first 5)
        grep -m 5 -A 1 '<edge' /var/lib/neo4j/import/$import_path >> /var/lib/neo4j/import/test_sample.graphml && \
        # Close the graphml tag
        echo '</graphml>' >> /var/lib/neo4j/import/test_sample.graphml"
    
    log "Test sample created. Attempting test import..."
    
    # Try importing the test sample
    local test_query="
    CALL apoc.import.graphml('file:///test_sample.graphml', {
        readLabels: true,
        storeNodeIds: false,
        defaultRelationshipType: 'RELATED',
        batchSize: 100,
        useTypes: false
    })"
    
    # Execute test import with full error output
    log "Executing test import..."
    docker exec $container_id cypher-shell -u neo4j -p yourpassword "$test_query"
    
    # Check results
    log "Checking test import results..."
    docker exec $container_id cypher-shell -u neo4j -p yourpassword \
        "MATCH (n) RETURN count(n) as nodes, collect(distinct labels(n)) as label_types"
    
    docker exec $container_id cypher-shell -u neo4j -p yourpassword \
        "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
    
    # Show sample of imported data
    log "Sample of imported test data:"
    docker exec $container_id cypher-shell -u neo4j -p yourpassword \
        "MATCH (n) RETURN n LIMIT 1"
}

# Function to import GraphML using Cypher
import_graphml() {
    local container_id=$1
    local import_path=$2
    
    # First run a test import
    log "Running test import with sample data..."
    test_import "$container_id" "$import_path"
    
    log "Test import completed. Press Enter to continue with full import, or Ctrl+C to abort..."
    read -r
    
    # Clear test data
    log "Clearing test data..."
    docker exec $container_id cypher-shell -u neo4j -p yourpassword "MATCH (n) DETACH DELETE n"
    
    # Continue with original import code...
    log "Proceeding with full import..."
    verify_apoc "$container_id"
    
    log "Checking complete GraphML file structure..."
    docker exec $container_id sh -c "echo 'Node count in GraphML:' && grep -c '<node' /var/lib/neo4j/import/$import_path"
    docker exec $container_id sh -c "echo 'Edge count in GraphML:' && grep -c '<edge' /var/lib/neo4j/import/$import_path"
    
    log "Attempting full GraphML import..."
    local import_query="
    CALL apoc.import.graphml('file:///$import_path', {
        readLabels: true,
        storeNodeIds: false,
        defaultRelationshipType: 'RELATED',
        batchSize: 1000,
        useTypes: false
    })"
    
    # Execute import
    docker exec $container_id cypher-shell -u neo4j -p yourpassword "$import_query" || {
        log "Import failed. Checking for errors..."
        docker exec $container_id sh -c "tail -n 50 /logs/neo4j.log"
        handle_error "GraphML import failed. Check the logs above."
    }
    
    # Verify results without detailed output
    log "Verifying import results..."
    local node_count=$(docker exec $container_id cypher-shell -u neo4j -p yourpassword \
        "MATCH (n) RETURN count(n) as count" | grep -oE '[0-9]+')
    
    if [ "$node_count" -eq "0" ]; then
        handle_error "Import completed but no data was imported."
    else
        log "Successfully imported $node_count nodes"
    fi
}

# Set up cleanup on script exit
trap cleanup EXIT

# Check Python dependencies
log "Checking Python dependencies..."
check_python_dependencies

# Check if backup file is provided
if [ -z "$1" ]; then
    handle_error "Backup file not provided. Usage: ./restore_backup.sh <backup_file.gz>"
fi

# Ensure the backup directory exists
BACKUP_DIR="./backup"
if [ ! -d "$BACKUP_DIR" ]; then
    handle_error "Backup directory does not exist. Please create $BACKUP_DIR directory"
fi

# Get the backup filename and validate it's in the backup directory
BACKUP_FILE="$1"
BACKUP_PATH="$BACKUP_DIR/$(basename "$BACKUP_FILE")"

# Validate backup file exists and is in backup directory
if [ ! -f "$BACKUP_PATH" ]; then
    handle_error "Backup file not found at: $BACKUP_PATH. Please place the backup file in the $BACKUP_DIR directory"
fi

# Validate file is a gzip file
if [[ ! "$BACKUP_PATH" =~ \.gz$ ]]; then
    handle_error "Backup file must be a gzipped file (*.gz)"
fi

file_type=$(file -b "$BACKUP_PATH")
if [[ ! $file_type == *"gzip compressed data"* ]]; then
    handle_error "File is not a valid gzip file: $BACKUP_PATH"
fi

# Create temporary file for unzipped content
TEMP_UNZIPPED_FILE=$(mktemp)
log "Unzipping backup file..."
gunzip -c "$BACKUP_PATH" > "$TEMP_UNZIPPED_FILE" || handle_error "Failed to unzip backup file"

# Stop and remove existing Neo4j container and volumes
log "Stopping Neo4j service and cleaning up data..."
docker compose down -v || handle_error "Failed to stop Neo4j and clean volumes"

# Create required directories
mkdir -p ./data
mkdir -p ./plugins

# Start Neo4j container
log "Starting Neo4j service..."
docker compose up -d neo4j || handle_error "Failed to start Neo4j container"

# Get Neo4j container ID early
NEO4J_CONTAINER=$(get_container_id neo4j)
if [ -z "$NEO4J_CONTAINER" ]; then
    handle_error "Neo4j container not found"
fi

# Wait for initial startup with more detailed logging
log "Waiting for initial Neo4j startup..."
sleep 15  # Give more time for initial startup

# Setup APOC in container
setup_apoc "$NEO4J_CONTAINER"

# Check Neo4j logs for plugin loading
log "Checking Neo4j logs for plugin loading..."
docker compose logs neo4j | grep -i "apoc" || log "WARNING: No APOC-related messages found in logs"
docker compose logs neo4j | grep -i "plugin" || log "WARNING: No plugin-related messages found in logs"

# Wait for Neo4j to be healthy
log "Waiting for Neo4j to be ready..."
python3 scripts/neo4j_health_check.py || handle_error "Neo4j failed to start properly"

# Copy unzipped backup file to container's import directory and set permissions
log "Copying backup file to container..."
docker exec $NEO4J_CONTAINER mkdir -p /var/lib/neo4j/import
docker cp "$TEMP_UNZIPPED_FILE" "$NEO4J_CONTAINER:/var/lib/neo4j/import/backup.graphml" || handle_error "Failed to copy backup file"
docker exec $NEO4J_CONTAINER chown -R neo4j:neo4j /var/lib/neo4j/import || handle_error "Failed to set file permissions"
docker exec $NEO4J_CONTAINER chmod 644 /var/lib/neo4j/import/backup.graphml || handle_error "Failed to set file permissions"

# Verify file exists and is readable
log "Verifying backup file in container..."
docker exec $NEO4J_CONTAINER ls -l /var/lib/neo4j/import/backup.graphml || handle_error "Cannot access backup file in container"

# Check file content
log "Checking backup file content..."
docker exec $NEO4J_CONTAINER sh -c 'head -n 20 /var/lib/neo4j/import/backup.graphml' || handle_error "Cannot read backup file"

# Clear existing data before import
log "Clearing existing graph data..."
docker exec $NEO4J_CONTAINER cypher-shell -u neo4j -p yourpassword "MATCH (n) DETACH DELETE n" || handle_error "Failed to clear existing data"

# Import the GraphML file
log "Importing GraphML backup..."
import_graphml "$NEO4J_CONTAINER" "backup.graphml"

# Restart Neo4j to ensure clean state
log "Restarting Neo4j..."
docker compose restart neo4j || handle_error "Failed to restart Neo4j"

# Wait for Neo4j to be healthy again
log "Waiting for Neo4j to be ready after restore..."
python3 scripts/neo4j_health_check.py || handle_error "Neo4j failed to start after restore"

log "Backup restoration completed successfully!" 