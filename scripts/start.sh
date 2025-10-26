#!/bin/bash
# scripts/start.sh
# Simplified script to start Neo4j with APOC

# Function to handle errors
handle_exception() {
    local error_msg="$1"
    echo "ERROR: $error_msg"
    exit 1
}

# Function to log messages
log_info() {
    echo "[INFO] $1"
}

log_debug() {
    echo "[DEBUG] $1"
}

log_error() {
    echo "[ERROR] $1"
}

log_warning() {
    echo "[WARNING] $1"
}

# Function to clean up on script exit
cleanup() {
    log_info "Cleanup: Exiting script"
    # Add any cleanup tasks here if needed
}

# Setup APOC plugin
setup_apoc() {
    log_info "Setting up APOC plugin..."
    
    # Define APOC version
    APOC_VERSION="2025.09.0"
    APOC_FILE="apoc-${APOC_VERSION}-core.jar"
    APOC_URL="https://github.com/neo4j/apoc/releases/download/${APOC_VERSION}/${APOC_FILE}"
    
    # Create plugins directory if it doesn't exist
    mkdir -p plugins || handle_exception "Failed to create plugins directory"
    
    # Check if APOC file already exists
    if [ -f "plugins/${APOC_FILE}" ]; then
        log_info "APOC plugin (version ${APOC_VERSION}) already exists, skipping download"
    else
        # Download APOC Core
        log_info "Downloading APOC plugin version ${APOC_VERSION}..."
        wget -O "plugins/${APOC_FILE}" "${APOC_URL}"
        
        if [ $? -ne 0 ]; then
            log_error "Failed to download APOC plugin"
            log_info "Checking if the file was partially downloaded..."
            
            if [ -f "plugins/${APOC_FILE}" ]; then
                if [ -s "plugins/${APOC_FILE}" ]; then
                    log_warning "APOC plugin file exists but may be incomplete. Proceeding anyway."
                else
                    log_error "APOC plugin file exists but is empty"
                    return 1
                fi
            else
                return 1
            fi
        fi
    fi
    
    # Fix permissions on plugins directory
    log_info "Setting permissions on plugins directory..."
    
    # Try to set permissions (ignore errors in WSL environment)
    chmod -R 755 plugins/ 2>/dev/null || log_warning "Could not set chmod permissions on plugins directory (this is expected in WSL)"
    
    # Try to set ownership to current user
    chown -R $(id -u):$(id -g) plugins/ 2>/dev/null || log_warning "Could not change ownership of plugins directory (this is expected in WSL)"
    
    # Verify plugin file is readable
    if [ ! -r "plugins/${APOC_FILE}" ]; then
        log_warning "APOC plugin file may not be readable. You might need to manually fix permissions."
    else
        log_info "APOC plugin file is readable."
    fi
    
    log_info "APOC plugin setup completed"
    return 0
}

# Fix permissions using fix-permissions.sh script
fix_permissions() {
    log_info "Fixing permissions using fix-permissions.sh script..."
    
    if [ -x "./scripts/fix-permissions.sh" ]; then
        ./scripts/fix-permissions.sh
        log_info "Permission fix completed"
    else
        log_warning "fix-permissions.sh script not found or not executable"
        log_info "Continuing without fixing permissions"
    fi
}

# Ensure environment file exists
ensure_env_file() {
    if [ ! -f ".env" ]; then
        log_info "Creating .env file with current user IDs and default settings..."
        cat > .env << EOL
# Neo4j Authentication
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=yourpassword
NEO4J_AUTH=\${NEO4J_USERNAME}/\${NEO4J_PASSWORD}

# User and Group IDs for container permissions
USER_ID=$(id -u)
GROUP_ID=$(id -g)

# Neo4j Configuration
# Memory settings
NEO4J_HEAP_MEMORY_INITIAL=4G
NEO4J_HEAP_MEMORY_MAX=4G
NEO4J_PAGE_CACHE=2G
EOL
        log_info "Created .env file with default settings"
    else
        log_info ".env file already exists, using existing configuration"
    fi
    
    # Source the .env file to make variables available
    source .env
    log_info "Neo4j will start with username: ${NEO4J_USERNAME} and configured memory settings"
}

# Start Neo4j
start_neo4j() {
    log_info "Starting Neo4j container..."
    
    # Check if Neo4j is already running
    if docker compose ps neo4j | grep -q "Up"; then
        log_info "Neo4j is already running"
        return 0
    fi
    
    # Start Neo4j
    docker compose up -d neo4j || handle_exception "Failed to start Neo4j container"
    
    # Wait for Neo4j to be healthy using container health check
    log_info "Waiting for Neo4j to be healthy..."
    for i in {1..30}; do
        if docker compose ps neo4j | grep -q "(healthy)"; then
            log_info "Neo4j is healthy!"
            return 0
        fi
        log_debug "Still waiting for Neo4j to be healthy (attempt $i/30)..."
        sleep 2
    done
    
    log_error "Neo4j failed to become healthy in the allocated time"
    log_info "Checking container logs:"
    docker compose logs neo4j --tail 50
    return 1
}

# Verify APOC installation
verify_apoc() {
    log_info "Verifying APOC installation..."
    local NEO4J_CONTAINER=$(docker compose ps -q neo4j)
    
    if [ -z "$NEO4J_CONTAINER" ]; then
        log_error "Neo4j container not found"
        return 1
    fi
    
    # First check if plugins directory exists in the container
    docker exec $NEO4J_CONTAINER ls -l /plugins/ 2>/dev/null
    if [ $? -ne 0 ]; then
        log_warning "Plugins directory not found in container"
        
        # Check the volumes in the docker-compose.yml
        log_info "Make sure your docker-compose.yml has the plugins volume set up correctly:"
        log_info "Example: - ./plugins:/plugins"
        return 1
    fi
    
    # Load username and password from environment
    local username=${NEO4J_USERNAME:-neo4j}
    local password=${NEO4J_PASSWORD:-yourpassword}
    
    # Try to verify APOC installation
    if docker exec $NEO4J_CONTAINER cypher-shell -u "$username" -p "$password" \
        "CALL apoc.help('text');" >/dev/null 2>&1; then
        log_info "APOC verification successful!"
        return 0
    else
        log_error "APOC verification failed"
        log_info "Checking APOC version in container:"
        docker exec $NEO4J_CONTAINER ls -la /plugins/
        return 1
    fi
}

# Function to display Neo4j information
display_info() {
    # Load username and password from environment
    local username=${NEO4J_USERNAME:-neo4j}
    local password=${NEO4J_PASSWORD:-yourpassword}
    
    log_info "Neo4j Information:"
    log_info "==================="
    log_info "Web Interface: http://localhost:7474"
    log_info "Bolt URI: bolt://localhost:7687"
    log_info "Username: $username"
    log_info "Password: $password"
    log_info "==================="
    log_info "To stop Neo4j: docker compose down"
}

# Handle stop signal
function stop_neo4j() {
    log_info "Stopping Neo4j..."
    docker compose down
    log_info "Neo4j stopped"
    exit 0
}

# Main execution
main() {
    # Set up trap for cleanup
    trap cleanup EXIT
    trap stop_neo4j SIGINT SIGTERM
    
    # Display help if requested
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        log_info "Usage: $0 [--help|-h|--stop]"
        log_info "  --help, -h: Display this help message"
        log_info "  --stop: Stop Neo4j container"
        exit 0
    fi
    
    # Stop Neo4j if requested
    if [ "$1" = "--stop" ]; then
        stop_neo4j
    fi
    
    # Activate Python virtual environment if exists
    if [ -d ".venv" ]; then
        log_info "Activating Python virtual environment..."
        source .venv/bin/activate || log_warning "Could not activate virtual environment"
    fi
    
    # Fix permissions first
    fix_permissions
    
    # Ensure environment file exists
    ensure_env_file
    
    # Setup APOC
    setup_apoc
    if [ $? -ne 0 ]; then
        log_warning "APOC setup encountered issues, but will attempt to continue"
    fi
    
    # Start Neo4j
    start_neo4j
    if [ $? -ne 0 ]; then
        handle_exception "Failed to start Neo4j properly"
    fi
    
    # Verify APOC
    verify_apoc
    if [ $? -ne 0 ]; then
        log_warning "APOC verification failed, but Neo4j is running."
        log_info "Check docker-compose.yml to ensure the plugins volume is correctly mounted."
    fi
    
    # Display information
    display_info
}

# Execute main function with all arguments
main "$@" 