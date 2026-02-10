#!/bin/bash
#
# APE 2026 - Local Deployment Script
# Локальное развёртывание для тестирования
#

set -e

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        APE 2026 - Локальное развёртывание                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ==================== ШАГ 1: Остановка старых контейнеров ====================
echo -e "${BLUE}▶ Шаг 1/5: Остановка старых контейнеров...${NC}"
docker-compose down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}   ✅ Готово${NC}"
echo ""

# ==================== ШАГ 2: Проверка .env ====================
echo -e "${BLUE}▶ Шаг 2/5: Проверка конфигурации...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}   ❌ Файл .env не найден!${NC}"
    echo "   Создайте его из .env.example:"
    echo "   cp .env.example .env"
    exit 1
fi
echo -e "${GREEN}   ✅ .env найден${NC}"
echo ""

# ==================== ШАГ 3: Сборка образов ====================
echo -e "${BLUE}▶ Шаг 3/5: Сборка Docker образов...${NC}"
echo "   Это может занять 3-5 минут..."
docker-compose build --no-cache --progress=plain 2>&1 | tee /tmp/docker-build.log | while read line; do
    echo "   $line"
done
echo -e "${GREEN}   ✅ Образы собраны${NC}"
echo ""

# ==================== ШАГ 4: Запуск сервисов ====================
echo -e "${BLUE}▶ Шаг 4/5: Запуск сервисов...${NC}"

# Запускаем инфраструктуру сначала
echo "   Запуск Neo4j, TimescaleDB, Redis..."
docker-compose up -d neo4j timescaledb redis

# Ждём инициализации
echo "   Ожидание инициализации баз данных (30 сек)..."
sleep 30

# Проверяем, что БД готовы
echo "   Проверка Neo4j..."
until curl -s http://localhost:7474 > /dev/null 2>&1; do
    echo "     Ожидание Neo4j..."
    sleep 5
done
echo -e "${GREEN}   ✅ Neo4j готов${NC}"

# Запускаем API
echo "   Запуск API..."
docker-compose up -d api

# Ждём API
echo "   Ожидание API (15 сек)..."
sleep 15

echo -e "${GREEN}   ✅ Все сервисы запущены${NC}"
echo ""

# ==================== ШАГ 5: Проверка здоровья ====================
echo -e "${BLUE}▶ Шаг 5/5: Проверка здоровья системы...${NC}"

HEALTH_URL="http://localhost:8000/health"
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "$HEALTH_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ API отвечает!${NC}"
        break
    else
        echo "   Попытка $((RETRY_COUNT+1))/$MAX_RETRIES..."
        sleep 5
        ((RETRY_COUNT++))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}   ❌ API не отвечает после $MAX_RETRIES попыток${NC}"
    echo "   Смотрите логи: docker-compose logs api"
    exit 1
fi

# Показываем результат health check
echo ""
echo -e "${BLUE}   Результат health check:${NC}"
curl -s "$HEALTH_URL" | python -m json.tool 2>/dev/null || curl -s "$HEALTH_URL"
echo ""

# ==================== ИТОГ ====================
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅ ЛОКАЛЬНОЕ РАЗВЁРТЫВАНИЕ ГОТОВО!            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Доступные сервисы:"
echo "  🌐 API Docs:      http://localhost:8000/docs"
echo "  🔍 Health Check:  http://localhost:8000/health"
echo "  📊 Grafana:       http://localhost:3001 (admin/admin123)"
echo "  📈 Prometheus:    http://localhost:9090"
echo "  🗄️  Neo4j Browser: http://localhost:7474"
echo ""
echo "Команды для управления:"
echo "  Просмотр логов:   docker-compose logs -f api"
echo "  Остановка:        docker-compose down"
echo "  Перезапуск:       docker-compose restart api"
echo ""
echo "Следующий шаг - тестирование:"
echo -e "  ${YELLOW}bash scripts/deploy/test_manual.sh${NC}"
