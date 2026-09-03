#!/bin/bash

# GeoSuite Production Deployment Script

set -e

# Configuration
APP_NAME="geosuite"
ENVIRONMENT="${1:-production}"
DOCKER_REGISTRY="your-registry.com"
DOCKER_NAMESPACE="geosuite"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
    exit 1
}

# Check environment
check_environment() {
    log "Deploying to ${ENVIRONMENT} environment"
    
    if [ ! -f ".env.${ENVIRONMENT}" ]; then
        error "Environment file .env.${ENVIRONMENT} not found"
    fi
    
    # Load environment variables
    source ".env.${ENVIRONMENT}"
}

# Build and push Docker images
build_images() {
    log "Building Docker images..."
    
    # Build backend
    docker build \
        -t "${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/backend:${ENVIRONMENT}-latest" \
        -f backend/Dockerfile \
        ./backend
    
    # Build frontend
    docker build \
        -t "${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/frontend:${ENVIRONMENT}-latest" \
        -f frontend/Dockerfile \
        ./frontend
    
    log "Pushing images to registry..."
    
    docker push "${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/backend:${ENVIRONMENT}-latest"
    docker push "${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/frontend:${ENVIRONMENT}-latest"
}

# Deploy to Kubernetes (if using K8s)
deploy_kubernetes() {
    if [ -f "kubernetes/deployment.yaml" ]; then
        log "Deploying to Kubernetes..."
        
        # Update image tags
        sed -i "s|IMAGE_TAG|${ENVIRONMENT}-latest|g" kubernetes/deployment.yaml
        
        # Apply configuration
        kubectl apply -f kubernetes/namespace.yaml
        kubectl apply -f kubernetes/configmap.yaml
        kubectl apply -f kubernetes/secrets.yaml
        kubectl apply -f kubernetes/deployment.yaml
        kubectl apply -f kubernetes/service.yaml
        kubectl apply -f kubernetes/ingress.yaml
        
        # Wait for rollout
        kubectl rollout status deployment/${APP_NAME} -n ${APP_NAME}
    fi
}

# Deploy with Docker Compose
deploy_docker_compose() {
    log "Deploying with Docker Compose..."
    
    # Update docker-compose.yml with environment specific settings
    cp docker-compose.yml docker-compose.${ENVIRONMENT}.yml
    
    # Update image tags
    sed -i "s|image: backend|image: ${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/backend:${ENVIRONMENT}-latest|g" \
        docker-compose.${ENVIRONMENT}.yml
    sed -i "s|image: frontend|image: ${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/frontend:${ENVIRONMENT}-latest|g" \
        docker-compose.${ENVIRONMENT}.yml
    
    # Deploy
    docker-compose -f docker-compose.${ENVIRONMENT}.yml pull
    docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d
    
    # Health check
    sleep 30
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "Backend health check passed"
    else
        error "Backend health check failed"
    fi
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Get backend container ID
    BACKEND_CONTAINER=$(docker ps -q --filter "name=${APP_NAME}-backend")
    
    if [ -n "$BACKEND_CONTAINER" ]; then
        docker exec $BACKEND_CONTAINER python -m alembic upgrade head
    fi
}

# Backup existing data
backup_data() {
    log "Backing up existing data..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $BACKUP_DIR
    
    # Backup PostgreSQL
    docker exec ${APP_NAME}-postgres pg_dump -U geosuite geosuite > $BACKUP_DIR/database.sql
    
    # Backup uploaded files
    tar -czf $BACKUP_DIR/uploads.tar.gz data/uploads/
    
    log "Backup saved to $BACKUP_DIR"
}

# Main deployment process
main() {
    log "Starting deployment of ${APP_NAME}..."
    
    check_environment
    backup_data
    build_images
    
    if command -v kubectl &> /dev/null && [ -d "kubernetes" ]; then
        deploy_kubernetes
    else
        deploy_docker_compose
    fi
    
    run_migrations
    
    log "Deployment completed successfully!"
    
    # Display deployment info
    echo ""
    echo "Deployment Summary:"
    echo "==================="
    echo "Application: ${APP_NAME}"
    echo "Environment: ${ENVIRONMENT}"
    echo "Registry: ${DOCKER_REGISTRY}"
    echo "Images:"
    echo "  - ${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/backend:${ENVIRONMENT}-latest"
    echo "  - ${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/frontend:${ENVIRONMENT}-latest"
    echo ""
    echo "Services available at:"
    echo "  Frontend: http://your-domain.com"
    echo "  API: http://your-domain.com/api"
    echo "  Monitoring: http://your-domain.com/monitoring"
    echo ""
}

# Run main function
main "$@"