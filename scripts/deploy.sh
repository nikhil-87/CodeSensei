#!/bin/bash
# =============================================================================
# Production Deployment Script for Public Use
#
# Usage: bash scripts/deploy.sh [environment]
#   environment: production (default) | staging | dev
#
# Prerequisites:
#   - Docker + Docker Compose v2.20+
#   - Git
#   - Domain + TLS certificate (or auto-generate with certbot)
#   - Public IP with inbound 80/443
#
# This script will:
#   1. Validate prerequisites
#   2. Generate secure secrets (.env file)
#   3. Pull AI models (one-time, ~15 min)
#   4. Start the full stack
#   5. Apply database migrations
#   6. Run health checks
#   7. Print access instructions
# =============================================================================

set -euo pipefail

ENVIRONMENT=${1:-production}
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

log_info() {
    echo -e "${BLUE}→${NC} $*"
}

log_success() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*"
    exit 1
}

# =============================================================================
# 1. Validate prerequisites
# =============================================================================

log_info "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || log_error "Docker not installed"
command -v git >/dev/null 2>&1 || log_error "Git not installed"

docker_version=$(docker --version | grep -oP '\d+\.\d+' | head -1)
log_info "Docker $docker_version found"

docker compose version > /dev/null 2>&1 || log_error "Docker Compose v2 not installed"

if [[ ! -f "docker-compose.yml" ]]; then
    log_error "Not in repo root (docker-compose.yml not found)"
fi

log_success "Prerequisites OK"

# =============================================================================
# 2. Generate or load configuration
# =============================================================================

if [[ -f ".env" ]]; then
    log_warn ".env already exists; using existing configuration"
    log_info "Edit .env manually to change settings"
else
    log_info "Generating .env with secure secrets..."
    cp .env.example .env

    # Generate random secrets
    SECRET_KEY=$(openssl rand -base64 32 || tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32)
    POSTGRES_PASSWORD=$(openssl rand -base64 24 || tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 24)
    REDIS_PASSWORD=$(openssl rand -base64 24 || tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 24)
    GRAFANA_PASSWORD=$(openssl rand -base64 24 || tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 24)

    # Replace placeholders in .env
    sed -i.bak \
        -e "s/APP_ENV=development/APP_ENV=$ENVIRONMENT/" \
        -e "s/APP_DEBUG=false/APP_DEBUG=false/" \
        -e "s/APP_SECRET_KEY=change-me-to-a-long-random-string-min-32-chars/APP_SECRET_KEY=$SECRET_KEY/" \
        -e "s/POSTGRES_PASSWORD=change-me-postgres-password/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" \
        -e "s/REDIS_PASSWORD=/REDIS_PASSWORD=$REDIS_PASSWORD/" \
        -e "s/GRAFANA_ADMIN_PASSWORD=admin/GRAFANA_ADMIN_PASSWORD=$GRAFANA_PASSWORD/" \
        .env
    rm -f .env.bak

    log_success "Generated .env with secure secrets"
    log_warn "SAVE THESE PASSWORDS SOMEWHERE SAFE (only shown once):"
    echo "  DB Password: $POSTGRES_PASSWORD"
    echo "  Redis Password: $REDIS_PASSWORD"
    echo "  Grafana Password: $GRAFANA_PASSWORD"
fi

# =============================================================================
# 3. Validate .env configuration
# =============================================================================

log_info "Validating .env..."

if ! grep -q "APP_SECRET_KEY=.*[A-Za-z0-9]" .env; then
    log_error "APP_SECRET_KEY not set in .env"
fi
if ! grep -q "POSTGRES_PASSWORD=.*[A-Za-z0-9]" .env; then
    log_error "POSTGRES_PASSWORD not set in .env"
fi

log_success ".env validation OK"

# =============================================================================
# 4. Validate compose stacks
# =============================================================================

log_info "Validating compose configuration..."

docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.prod.yml \
               --env-file .env config --quiet || log_error "Compose validation failed"

log_success "Compose stacks are valid"

# =============================================================================
# 5. Pull images
# =============================================================================

log_info "Pulling Docker images (this may take 5-10 min)..."

docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.prod.yml \
               --env-file .env pull

log_success "Docker images pulled"

# =============================================================================
# 6. Start services
# =============================================================================

log_info "Starting services..."

docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.prod.yml \
               --env-file .env up -d

log_success "Services started"

# =============================================================================
# 7. Wait for services to be healthy
# =============================================================================

log_info "Waiting for services to become healthy (this may take 2-3 min)..."

max_attempts=60
attempt=0
while [[ $attempt -lt $max_attempts ]]; do
    if docker compose ps | grep -q "healthy"; then
        log_success "Services are healthy"
        break
    fi
    echo -n "."
    sleep 2
    ((attempt++))
done

if [[ $attempt -eq $max_attempts ]]; then
    log_error "Services did not become healthy in time. Check logs:"
    docker compose logs --tail=20
fi

# =============================================================================
# 8. Apply database migrations
# =============================================================================

log_info "Applying database migrations..."

docker compose -f docker/docker-compose.yml \
               -f docker/docker-compose.prod.yml \
               --env-file .env exec -T backend alembic upgrade head

log_success "Database migrations applied"

# =============================================================================
# 9. Pull AI models (one-time, optional)
# =============================================================================

if docker compose exec -T ollama ollama list | grep -q "deepseek-coder"; then
    log_info "AI models already pulled"
else
    log_warn "Pulling AI models (first time, ~10-15 min, can skip and pull later)"
    read -p "Pull models now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Pulling deepseek-coder:6.7b..."
        docker compose exec -T ollama ollama pull deepseek-coder:6.7b

        log_info "Pulling nomic-embed-text..."
        docker compose exec -T ollama ollama pull nomic-embed-text

        log_success "AI models ready"
    else
        log_warn "Models will be pulled on-demand on first API request (slower)"
    fi
fi

# =============================================================================
# 10. Health checks
# =============================================================================

log_info "Running health checks..."

sleep 2

services=("backend" "frontend" "postgres" "redis")
for service in "${services[@]}"; do
    if docker compose ps | grep -q "$service.*Up"; then
        log_success "$service is up"
    else
        log_warn "$service may not be healthy"
    fi
done

# =============================================================================
# 11. Print access information
# =============================================================================

echo
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Deployment successful!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo

if [[ "$ENVIRONMENT" == "production" ]]; then
    echo -e "${YELLOW}Next steps for public access:${NC}"
    echo "  1. Configure TLS certificate:"
    echo "     sudo certbot certonly --standalone -d yourdomain.com"
    echo "     (then update infrastructure/nginx/prod.conf with cert paths)"
    echo
    echo "  2. Add Nginx to docker-compose.prod.yml:"
    echo "     See docs/Deployment-Guide.md section 2.1"
    echo
    echo "  3. Update .env with your domain:"
    echo "     APP_CORS_ORIGINS=https://yourdomain.com"
    echo "     VITE_API_BASE_URL=https://yourdomain.com"
    echo
    echo "  4. Restart services:"
    echo "     docker compose down && docker compose up -d"
    echo
else
    echo -e "${BLUE}Access the application:${NC}"
fi

echo "  Frontend:   http://localhost:8080"
echo "  Backend API: http://localhost:8000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  Grafana:    http://localhost:3000 (admin/see .env for password)"
echo "  Prometheus: http://localhost:9090"
echo

echo -e "${BLUE}Useful commands:${NC}"
echo "  View logs:        docker compose logs -f <service>"
echo "  Database shell:   docker compose exec postgres psql -U codesensei -d codesensei"
echo "  Worker queue:     docker compose exec backend python -m rq info"
echo "  Health check:     curl http://localhost:8000/health"
echo

echo -e "${YELLOW}Documentation:${NC}"
echo "  Deployment:     docs/Deployment-Guide.md"
echo "  Operations:     docs/Operational-Runbook.md"
echo "  Security:       docs/Security-Guide.md"
echo "  Troubleshooting:docs/Troubleshooting.md"
echo

log_success "Ready to analyze repositories!"
