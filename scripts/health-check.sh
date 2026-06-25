#!/bin/bash
# =============================================================================
# Quick Health Check & Status Report
#
# Run: bash scripts/health-check.sh
#
# Checks all services, databases, queues, and prints a summary report.
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_check() {
    echo -e "${BLUE}→${NC} $*"
}

log_ok() {
    echo -e "${GREEN}✓${NC} $*"
}

log_fail() {
    echo -e "${RED}✗${NC} $*"
}

echo
echo -e "${BLUE}CodeSensei — Health Check${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo

# =============================================================================
# Container Status
# =============================================================================

echo -e "${BLUE}1. Container Status${NC}"

docker compose ps

echo

# =============================================================================
# Network Connectivity
# =============================================================================

echo -e "${BLUE}2. Network Connectivity${NC}"

log_check "Backend → Postgres..."
if docker compose exec -T backend python -c "
import socket
try:
    socket.create_connection(('postgres', 5432), timeout=2)
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
" 2>/dev/null | grep -q "OK"; then
    log_ok "Postgres reachable"
else
    log_fail "Postgres unreachable"
fi

log_check "Backend → Redis..."
if docker compose exec -T backend python -c "
import socket
try:
    socket.create_connection(('redis', 6379), timeout=2)
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
" 2>/dev/null | grep -q "OK"; then
    log_ok "Redis reachable"
else
    log_fail "Redis unreachable"
fi

log_check "Backend → Ollama..."
if docker compose exec -T backend python -c "
import socket
try:
    socket.create_connection(('ollama', 11434), timeout=2)
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
" 2>/dev/null | grep -q "OK"; then
    log_ok "Ollama reachable"
else
    log_fail "Ollama unreachable"
fi

echo

# =============================================================================
# HTTP Endpoints
# =============================================================================

echo -e "${BLUE}3. HTTP Endpoints${NC}"

log_check "Backend health..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    log_ok "Backend responding"
else
    log_fail "Backend not responding (port 8000)"
fi

log_check "Frontend health..."
if curl -sf http://localhost:5173 > /dev/null 2>&1; then
    log_ok "Frontend dev server responding"
elif curl -sf http://localhost:8080 > /dev/null 2>&1; then
    log_ok "Frontend prod server responding"
else
    log_fail "Frontend not responding"
fi

log_check "Prometheus metrics..."
if curl -sf http://localhost:9090/api/v1/query?query=up > /dev/null 2>&1; then
    log_ok "Prometheus responding"
else
    log_fail "Prometheus not responding"
fi

echo

# =============================================================================
# Database Status
# =============================================================================

echo -e "${BLUE}4. Database Status${NC}"

log_check "Checking Postgres..."
DB_ALIVE=$(docker compose exec -T postgres psql -U codesensei -d codesensei -c "SELECT 1" 2>/dev/null | grep -c "1" || echo "0")
if [[ "$DB_ALIVE" == "1" ]]; then
    log_ok "Postgres responding"
    TABLE_COUNT=$(docker compose exec -T postgres psql -U codesensei -d codesensei -c "\dt" 2>/dev/null | grep -c "+" || echo "0")
    log_ok "Tables: $(($TABLE_COUNT - 2))"  # Subtract header lines
else
    log_fail "Postgres not responding"
fi

echo

# =============================================================================
# Queue Status
# =============================================================================

echo -e "${BLUE}5. Queue Status${NC}"

log_check "Redis queue info..."
if command -v redis-cli &> /dev/null; then
    QUEUE_SIZE=$(redis-cli -h localhost LLEN analysis-jobs 2>/dev/null || echo "0")
    log_ok "Jobs queued: $QUEUE_SIZE"
else
    log_ok "redis-cli not installed locally (queue status skipped)"
fi

echo

# =============================================================================
# Disk Usage
# =============================================================================

echo -e "${BLUE}6. Disk Usage${NC}"

log_check "Docker volumes..."
docker volume ls | grep codesensei | while read -r line; do
    vol_name=$(echo "$line" | awk '{print $NF}')
    log_ok "  $vol_name"
done

echo

# =============================================================================
# Service Logs (Last error, if any)
# =============================================================================

echo -e "${BLUE}7. Recent Errors (if any)${NC}"

for service in backend worker postgres redis ollama; do
    ERROR_COUNT=$(docker compose logs --tail=50 $service 2>/dev/null | grep -i "error\|exception\|failed" | wc -l || echo "0")
    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        log_fail "$service: $ERROR_COUNT errors in recent logs"
    else
        log_ok "$service: no errors"
    fi
done

echo

# =============================================================================
# Summary
# =============================================================================

echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Health check complete.${NC}"
echo
echo "For full logs, run:"
echo "  docker compose logs -f <service>"
echo
echo "For database queries, run:"
echo "  docker compose exec postgres psql -U codesensei -d codesensei"
echo
