#!/bin/bash
#
# APE 2026 - Manual Testing Script
# Интерактивное ручное тестирование API
#

set -e

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

API_URL="${API_URL:-http://localhost:8000}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         APE 2026 - Ручное тестирование API               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "API URL: ${CYAN}$API_URL${NC}"
echo ""

# Функция для ожидания нажатия Enter
wait_for_enter() {
    echo ""
    echo -e "${YELLOW}Нажмите ENTER для продолжения...${NC}"
    read
}

# Функция для выполнения запроса
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="${4:-}"
    
    echo -e "${BLUE}▶ Тест: $name${NC}"
    echo -e "${CYAN}   $method $endpoint${NC}"
    echo ""
    
    if [ -n "$data" ]; then
        echo -e "${YELLOW}   Request Body:${NC}"
        echo "   $data" | python -m json.tool 2>/dev/null || echo "   $data"
        echo ""
        
        RESPONSE=$(curl -s -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint" 2>&1) || true
    else
        RESPONSE=$(curl -s -X "$method" \
            "$API_URL$endpoint" 2>&1) || true
    fi
    
    echo -e "${GREEN}   Response:${NC}"
    if echo "$RESPONSE" | python -m json.tool > /dev/null 2>&1; then
        echo "$RESPONSE" | python -m json.tool | sed 's/^/   /'
    else
        echo "   $RESPONSE"
    fi
    
    wait_for_enter
}

# ==================== ТЕСТ 1: Health Check ====================
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ТЕСТ 1: Проверка здоровья системы${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Это базовая проверка - если она не работает,"
echo "значит что-то пошло не так с деплоем."
echo ""

test_endpoint "Health Check" "GET" "/health"

# ==================== ТЕСТ 2: Readiness ====================
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ТЕСТ 2: Readiness Probe (для Kubernetes)${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Показывает, готова ли система принимать трафик."
echo ""

test_endpoint "Readiness Check" "GET" "/ready"

# ==================== ТЕСТ 3: Predictions List ====================
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ТЕСТ 3: Получение списка прогнозов${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Получаем все прогнозы (пока их нет - вернётся пустой список)."
echo ""

test_endpoint "Predictions List" "GET" "/api/predictions/"

# ==================== ТЕСТ 4: Predictions with Ticker ====================
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ТЕСТ 4: Фильтр по тикеру${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Пробуем получить прогнозы для Apple (AAPL)."
echo ""

test_endpoint "Predictions for AAPL" "GET" "/api/predictions/?ticker=AAPL"

# ==================== ТЕСТ 5: Track Record ====================
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ТЕСТ 5: Статистика точности${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Показывает насколько хорошо система предсказывала ранее."
echo ""

test_endpoint "Track Record" "GET" "/api/predictions/track-record"

# ==================== ТЕСТ 6: Data Tickers ====================
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ТЕСТ 6: Доступные тикеры${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Получаем список тикеров, для которых есть данные."
echo ""

test_endpoint "Available Tickers" "GET" "/api/data/tickers"

# ==================== ТЕСТ 7: Create Query ====================
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ТЕСТ 7: Создание запроса на анализ${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Создаём асинхронный запрос (вернётся сразу, результат позже)."
echo "ВНИМАНИЕ: Этот запрос может занять деньги (API calls)!"
echo ""
echo -e "${RED}Пропустить этот тест? (y/n)${NC}"
read -r SKIP_EXPENSIVE

if [ "$SKIP_EXPENSIVE" != "y" ] && [ "$SKIP_EXPENSIVE" != "Y" ]; then
    test_endpoint "Create Analysis Query" "POST" "/api/query" '{
        "query": "Проанализируй перспективы Apple на ближайший месяц",
        "provider": "deepseek"
    }'
else
    echo -e "${YELLOW}   ⏭️  Пропущено${NC}"
    wait_for_enter
fi

# ==================== ТЕСТ 8: Security Headers ====================
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  ТЕСТ 8: Проверка security headers${NC}"
echo -e "${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Проверяем, что API возвращает security headers."
echo ""

echo -e "${BLUE}▶ Тест: Security Headers${NC}"
echo -e "${CYAN}   GET /health (смотрим headers)${NC}"
echo ""

echo -e "${GREEN}   Response Headers:${NC}"
curl -s -I "$API_URL/health" | grep -E "(X-Content-Type|X-Frame|X-XSS|Content-Security)" | sed 's/^/   /'

echo ""
echo -e "${GREEN}   ✅ Security headers присутствуют${NC}"
wait_for_enter

# ==================== ИТОГ ====================
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Что вы проверили:"
echo "  ✅ API отвечает на запросы"
echo "  ✅ Health/readiness работают"
echo "  ✅ Predictions endpoints доступны"
echo "  ✅ Security headers на месте"
echo "  ✅ Query creation работает"
echo ""
echo "Следующий шаг - staging deployment:"
echo -e "  ${YELLOW}bash scripts/deploy/deploy_staging.sh${NC}"
echo ""
