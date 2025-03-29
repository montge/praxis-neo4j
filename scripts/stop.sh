#!/bin/bash
# scripts/stop.sh
# Script to stop Neo4j container

# Function to log messages
log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1"
}

# Stop Neo4j
log_info "Stopping Neo4j container..."
docker compose down

# Check if the operation was successful
if [ $? -eq 0 ]; then
    log_info "Neo4j container stopped successfully"
    exit 0
else
    log_error "Failed to stop Neo4j container properly"
    log_info "Checking container status:"
    docker compose ps
    exit 1
fi 