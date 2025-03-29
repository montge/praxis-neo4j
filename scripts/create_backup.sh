#!/bin/bash
# scripts/create_backup.sh
# Script to create a backup of Neo4j database using APOC and save it with timestamp

# Set up logging
LOG_FILE="backup.log"
exec 1> >(tee -a "$LOG_FILE") 2>&1

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to handle errors
handle_exception() {
    local error_msg="$1"
    log "ERROR: $error_msg"
    exit 1
}

# Function to get container ID by service name
get_container_id() {
    local service_name=$1
    local container_id=$(docker compose ps -q $service_name)
    echo $container_id
}

# Ensure backup directory exists
ensure_backup_dir() {
    local backup_dir="./backup"
    if [ ! -d "$backup_dir" ]; then
        log "Creating backup directory..."
        mkdir -p "$backup_dir" || handle_exception "Failed to create backup directory"
    fi
    log "Backup directory exists at: $backup_dir"
}

# Verify APOC is installed and working
verify_apoc() {
    local container_id=$1
    local username=${NEO4J_USERNAME:-neo4j}
    local password=${NEO4J_PASSWORD:-yourpassword}
    
    log "Verifying APOC installation..."
    if ! docker exec $container_id cypher-shell -u "$username" -p "$password" \
        "CALL apoc.help('export') YIELD name WHERE name CONTAINS 'graphml' RETURN count(*) as count" | grep -q "[0-9]"; then
        handle_exception "APOC export functions not available. Please ensure APOC is properly installed."
    fi
    log "APOC export functions are available"
}

# Generate a filename with timestamp
generate_filename() {
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    echo "neo4j_backup_${timestamp}.graphml"
}

# Create backup using APOC
create_backup() {
    local container_id=$1
    local output_file=$2
    local username=${NEO4J_USERNAME:-neo4j}
    local password=${NEO4J_PASSWORD:-yourpassword}
    
    log "Creating backup of Neo4j database..."
    
    # First, ensure the import directory exists in the container
    docker exec $container_id mkdir -p /var/lib/neo4j/import || handle_exception "Failed to create import directory"
    
    # Export to GraphML using APOC - note that the path is relative to the import directory
    local export_query="CALL apoc.export.graphml.all('temp_backup.graphml', {useTypes: true, readLabels: true, storeNodeIds: false})"
    
    log "Executing export query..."
    if ! docker exec $container_id cypher-shell -u "$username" -p "$password" "$export_query"; then
        handle_exception "Failed to export database to GraphML"
    fi
    
    # Copy the file from container to host - file will be in the import directory
    log "Copying backup file from container to host..."
    docker cp "$container_id:/var/lib/neo4j/import/temp_backup.graphml" "./backup/$output_file" || \
        handle_exception "Failed to copy backup file from container"
    
    # Clean up the temporary file in the container
    log "Cleaning up temporary files in container..."
    docker exec $container_id rm -f /var/lib/neo4j/import/temp_backup.graphml
    
    # Check if the file exists and has content
    if [ ! -s "./backup/$output_file" ]; then
        handle_exception "Backup file is empty or does not exist"
    fi
    
    log "Successfully created backup file: ./backup/$output_file"
    return 0
}

# Compress the backup file
compress_backup() {
    local file_path="$1"
    
    log "Compressing backup file..."
    gzip -f "$file_path" || handle_exception "Failed to compress backup file"
    log "Compression complete: ${file_path}.gz"
    return 0
}

# Verify backup file
verify_backup() {
    local file_path="$1"
    
    log "Verifying backup file..."
    
    # Check if file exists and is not empty
    if [ ! -s "$file_path" ]; then
        handle_exception "Backup verification failed: File is empty or does not exist: $file_path"
    fi
    
    # For compressed files, test the archive integrity
    if [[ "$file_path" == *.gz ]]; then
        log "Testing gzip archive integrity..."
        gzip -t "$file_path" || handle_exception "Backup verification failed: Invalid gzip archive: $file_path"
        
        # Get file size
        local file_size=$(du -h "$file_path" | cut -f1)
        log "Compressed backup size: $file_size"
    fi
    
    log "Backup verification successful"
    return 0
}

# Display backup statistics
display_stats() {
    local backup_dir="./backup"
    
    # Count number of backups
    local backup_count=$(ls -1 $backup_dir/*.gz 2>/dev/null | wc -l)
    
    # Get total size
    local total_size=$(du -sh $backup_dir | cut -f1)
    
    # Get latest backup
    local latest_backup=$(ls -t $backup_dir/*.gz 2>/dev/null | head -1)
    
    log "Backup Statistics:"
    log "Total backups: $backup_count"
    log "Backup directory size: $total_size"
    log "Latest backup: $latest_backup"
    
    return 0
}

# Main function
main() {
    log "Starting Neo4j backup process..."
    
    # Source .env file if exists
    if [ -f ".env" ]; then
        log "Loading environment variables from .env..."
        source .env
    fi
    
    # Ensure backup directory exists
    ensure_backup_dir
    
    # Get Neo4j container ID
    log "Getting Neo4j container ID..."
    NEO4J_CONTAINER=$(get_container_id neo4j)
    
    if [ -z "$NEO4J_CONTAINER" ]; then
        handle_exception "Neo4j container not found. Is Neo4j running?"
    fi
    
    # Verify Neo4j is running and APOC is available
    verify_apoc "$NEO4J_CONTAINER"
    
    # Generate backup filename with timestamp
    backup_filename=$(generate_filename)
    
    # Create backup
    create_backup "$NEO4J_CONTAINER" "$backup_filename"
    
    # Compress backup
    compress_backup "./backup/$backup_filename"
    
    # Verify backup
    verify_backup "./backup/${backup_filename}.gz"
    
    # Display backup statistics
    display_stats
    
    log "Neo4j backup process completed successfully!"
    log "Backup file created: ./backup/${backup_filename}.gz"
}

# Execute main function
main 