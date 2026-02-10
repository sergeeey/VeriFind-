#!/bin/bash
#
# APE 2026 - Staging Deployment Script
# Развёртывание в staging окружении
#

set -e

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_DIR"

STAGING_COMPOSE="docker-compose.staging.yml"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           APE 2026 - Staging Deployment                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ==================== ПРОВЕРКИ ====================
echo -e "${BLUE}▶ Проверка окружения...${NC}"

if [ ! -f "$STAGING_COMPOSE" ]; then
    echo -e "${RED}❌ Файл $STAGING_COMPOSE не найден!${NC}"
    exit 1
fi

if [ ! -f .env ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    exit 1
fi

echo -e "${GREEN}   ✅ Все файлы на месте${NC}"
echo ""

# ==================== ОСТАНОВКА ====================
echo -e "${BLUE}▶ Остановка старого staging (если есть)...${NC}"
docker-compose -f "$STAGING_COMPOSE" down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}   ✅ Готово${NC}"
echo ""

# ==================== СБОРКА ====================
echo -e "${BLUE}▶ Сборка staging образов...${NC}"
echo "   Это может занять 3-5 минут..."
docker-compose -f "$STAGING_COMPOSE" build --no-cache 2>&1 | tee /tmp/staging-build.log | grep -E "(Step|Successfully|Error)" || true
echo -e "${GREEN}   ✅ Образы собраны${NC}"
echo ""

# ==================== ЗАПУСК ====================
echo -e "${BLUE}▶ Запуск staging сервисов...${NC}"
docker-compose -f "$STAGING_COMPOSE" up -d

# ==================== ОЖИДАНИЕ ====================
echo ""
echo -e "${BLUE}▶ Ожидание инициализации (45 сек)...${NC}"
sleep 45

# ==================== ПРОВЕРКА ====================
echo -e "${BLUE}▶ Проверка сервисов...${NC}"

SERVICES=("neo4j-staging" "timescaledb-staging" "redis-staging" "api-staging")
ALL_GOOD=true

for service in "${SERVICES[@]}"; do
    if docker ps | grep -q "$service"; then
        echo -e "   ${GREEN}✅ $service запущен${NC}"
    else
        echo -e "   ${RED}❌ $service не запущен${NC}"
        ALL_GOOD=false
    fi
done

echo ""

# ==================== HEALTH CHECK ====================
echo -e "${BLUE}▶ Health check API...${NC}"

STAGING_HEALTH="http://localhost:8001/health"
MAX_RETRIES=10
RETRY=0

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s "$STAGING_HEALTH" > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ API staging отвечает!${NC}"
        break
    else
        echo "   Попытка $((RETRY+1))/$MAX_RETRIES..."
        sleep 5
        ((RETRY++))
    fi
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}   ❌ API не отвечает${NC}"
    echo "   Смотрите логи: docker-compose -f $STAGING_COMPOSE logs api-staging"
    ALL_GOOD=false
fi

echo ""

# ==================== ИТОГ ====================
if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ✅ STAGING РАЗВЁРТЫВАНИЕ ГОТОВО!               ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Staging сервисы доступны:${NC}"
    echo "  🌐 API:            http://localhost:8001"
    echo "  📊 Grafana:        http://localhost:3002 (admin/admin123)"
    echo "  📈 Prometheus:     http://localhost:9091"
    echo "  🗄️  Neo4j:          http://localhost:7475"
    echo ""
    echo -e "${YELLOW}⚠️  ВАЖНО: Это staging - можно тестировать смело!${NC}"
    echo ""
    echo "Команды для управления:"
    echo "  Логи:     docker-compose -f $STAGING_COMPOSE logs -f api-staging"
    echo "  Остановка: docker-compose -f $STAGING_COMPOSE down"
    echo "  Перезапуск: docker-compose -f $STAGING_COMPOSE restart api-staging"
    echo ""
    echo "Следующий шаг - мониторинг:"
    echo -e "  ${YELLOW}bash scripts/deploy/monitor_staging.sh${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║          ❌ STAGING ЕСТЬ ПРОБЛЕМЫ                       ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Смотрите логи:"
    echo "  docker-compose -f $STAGING_COMPOSE logs"
    exit 1
fi
