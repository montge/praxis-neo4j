#!/bin/bash
# scripts/fix-permissions.sh
# Script to fix permissions for Neo4j directories

# Function to log messages
log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1"
}

log_warning() {
    echo "[WARNING] $1"
}

# Fix permissions for Neo4j directories
fix_permissions() {
    local dirs=("plugins" "data" "logs")
    
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            log_info "Fixing permissions for $dir directory..."
            
            # Try to set ownership (ignore errors in WSL environment)
            sudo chown -R $(id -u):$(id -g) "$dir" 2>/dev/null
            if [ $? -ne 0 ]; then
                log_warning "Could not change ownership of $dir directory with sudo. Trying without sudo..."
                chown -R $(id -u):$(id -g) "$dir" 2>/dev/null || log_warning "Could not change ownership of $dir directory"
            fi
            
            # Try to set permissions
            sudo chmod -R 755 "$dir" 2>/dev/null
            if [ $? -ne 0 ]; then
                log_warning "Could not set permissions on $dir directory with sudo. Trying without sudo..."
                chmod -R 755 "$dir" 2>/dev/null || log_warning "Could not set permissions on $dir directory"
            fi
            
            log_info "Completed permission fixes for $dir"
        else
            log_info "Directory $dir does not exist, creating it..."
            mkdir -p "$dir"
            
            # Set permissions for new directory
            sudo chown -R $(id -u):$(id -g) "$dir" 2>/dev/null || chown -R $(id -u):$(id -g) "$dir" 2>/dev/null || log_warning "Could not set ownership on new $dir directory"
            sudo chmod -R 755 "$dir" 2>/dev/null || chmod -R 755 "$dir" 2>/dev/null || log_warning "Could not set permissions on new $dir directory"
        fi
    done
    
    log_info "All permissions have been fixed"
}

# Extract value from .env file
get_env_value() {
    local key="$1"
    local default_value="$2"
    local env_file=".env"
    
    if [ -f "$env_file" ] && grep -q "^$key=" "$env_file"; then
        grep "^$key=" "$env_file" | sed "s/^$key=//"
    else
        echo "$default_value"
    fi
}

# Create or update environment file
create_env_file() {
    log_info "Creating/updating .env file..."
    
    # Get current user ID and group ID
    local user_id=$(id -u)
    local group_id=$(id -g)
    
    # Check if .env file exists
    if [ -f ".env" ]; then
        log_info ".env file exists, preserving existing settings and updating user/group IDs..."
        
        # Read existing values to preserve them
        neo4j_username=$(get_env_value "NEO4J_USERNAME" "neo4j")
        neo4j_password=$(get_env_value "NEO4J_PASSWORD" "yourpassword")
        heap_initial=$(get_env_value "NEO4J_HEAP_MEMORY_INITIAL" "4G")
        heap_max=$(get_env_value "NEO4J_HEAP_MEMORY_MAX" "4G")
        page_cache=$(get_env_value "NEO4J_PAGE_CACHE" "2G")
        
    else
        # Use default values
        log_info "Creating new .env file with defaults..."
        neo4j_username="neo4j"
        neo4j_password="yourpassword"
        heap_initial="4G"
        heap_max="4G"
        page_cache="2G"
    fi
    
    # Create a new .env file with updated values
    cat > .env << EOL
# Neo4j Authentication
NEO4J_USERNAME=$neo4j_username
NEO4J_PASSWORD=$neo4j_password
NEO4J_AUTH=\${NEO4J_USERNAME}/\${NEO4J_PASSWORD}

# User and Group IDs for container permissions
USER_ID=$user_id
GROUP_ID=$group_id

# Neo4j Configuration
# Memory settings
NEO4J_HEAP_MEMORY_INITIAL=$heap_initial
NEO4J_HEAP_MEMORY_MAX=$heap_max
NEO4J_PAGE_CACHE=$page_cache
EOL
    
    log_info "Environment file updated with USER_ID=$user_id and GROUP_ID=$group_id"
    log_info "Neo4j will use username: $neo4j_username"
}

# Main execution
main() {
    log_info "Starting permission fix process..."
    
    # Fix directory permissions
    fix_permissions
    
    # Create environment file
    create_env_file
    
    log_info "Permission fix completed. You can now run: ./scripts/start.sh"
}

# Execute main function
main 