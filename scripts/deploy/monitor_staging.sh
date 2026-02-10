#!/bin/bash
#
# APE 2026 - Staging Monitoring Script
# Мониторинг staging окружения
#

set -e

# Цвета
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

API_URL="http://localhost:8001"
DURATION=7200  # 2 часа по умолчанию
INTERVAL=30    # Проверка каждые 30 секунд

# Статистика
REQUESTS=0
SUCCESSES=0
FAILURES=0
TOTAL_TIME=0
START_TIME=$(date +%s)

# Создаём лог файл
LOG_FILE="staging_monitor_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         APE 2026 - Staging Monitoring                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "API URL: ${CYAN}$API_URL${NC}"
echo -e "Лог файл: ${CYAN}$LOG_FILE${NC}"
echo -e "Длительность: ${CYAN}$(($DURATION/3600)) часов${NC}"
echo ""
echo -e "${YELLOW}Нажмите Ctrl+C для остановки${NC}"
echo ""

# Функция логирования
log() {
    echo "$1" | tee -a "$LOG_FILE"
}

# Функция проверки
run_check() {
    local check_name="$1"
    local check_cmd="$2"
    
    if eval "$check_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $check_name${NC}"
        return 0
    else
        echo -e "${RED}❌ $check_name${NC}"
        return 1
    fi
}

# Функция API health check
check_api() {
    local start=$(date +%s%N)
    local response
    local http_code
    
    response=$(curl -s -w "\n%{http_code}" "$API_URL/health" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    
    local end=$(date +%s%N)
    local duration_ms=$(( (end - start) / 1000000 ))
    
    ((REQUESTS++))
    
    if [ "$http_code" = "200" ]; then
        ((SUCCESSES++))
        echo "$duration_ms"
        return 0
    else
        ((FAILURES++))
        echo "-1"
        return 1
    fi
}

# Главный цикл мониторинга
main_loop() {
    local iteration=0
    local latencies=()
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - START_TIME))
        
        if [ $elapsed -ge $DURATION ]; then
            echo ""
            echo -e "${GREEN}✅ Мониторинг завершён (достигнут лимит времени)${NC}"
            break
        fi
        
        ((iteration++))
        
        clear
        echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║         APE 2026 - Staging Monitor                       ║${NC}"
        echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
        printf "${BLUE}║${NC}  Итерация: %-5d | Время: %-8s                       ${BLUE}║${NC}\n" "$iteration" "$(date +%H:%M:%S)"
        echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
        echo ""
        
        # Проверка контейнеров
        echo -e "${BLUE}▶ Контейнеры:${NC}"
        run_check "api-staging" "docker ps | grep -q api-staging"
        run_check "neo4j-staging" "docker ps | grep -q neo4j-staging"
        run_check "timescaledb-staging" "docker ps | grep -q timescaledb-staging"
        run_check "redis-staging" "docker ps | grep -q redis-staging"
        echo ""
        
        # API Health Check
        echo -e "${BLUE}▶ API Health Check:${NC}"
        local latency=$(check_api)
        
        if [ "$latency" != "-1" ]; then
            echo -e "   ${GREEN}✅ API отвечает${NC} (${latency}ms)"
            latencies+=($latency)
            
            # Считаем среднее
            local sum=0
            for l in "${latencies[@]}"; do
                sum=$((sum + l))
            done
            local avg=$((sum / ${#latencies[@]}))
            echo -e "   Средняя latency: ${CYAN}${avg}ms${NC}"
            
            # Проверяем пороги
            if [ $avg -lt 100 ]; then
                echo -e "   Статус: ${GREEN}🟢 ОТЛИЧНО${NC}"
            elif [ $avg -lt 500 ]; then
                echo -e "   Статус: ${YELLOW}🟡 ХОРОШО${NC}"
            else
                echo -e "   Статус: ${RED}🟠 МЕДЛЕННО${NC}"
            fi
        else
            echo -e "   ${RED}❌ API не отвечает!${NC}"
            echo -e "   ${YELLOW}Логи: docker-compose -f docker-compose.staging.yml logs api-staging${NC}"
        fi
        echo ""
        
        # Статистика
        echo -e "${BLUE}▶ Статистика запросов:${NC}"
        printf "   Всего:    %d\n" "$REQUESTS"
        printf "   Успешно:  ${GREEN}%d${NC}\n" "$SUCCESSES"
        printf "   Ошибок:   ${RED}%d${NC}\n" "$FAILURES"
        
        if [ $REQUESTS -gt 0 ]; then
            local success_rate=$((SUCCESSES * 100 / REQUESTS))
            if [ $success_rate -ge 98 ]; then
                echo -e "   Success rate: ${GREEN}${success_rate}%${NC}"
            elif [ $success_rate -ge 90 ]; then
                echo -e "   Success rate: ${YELLOW}${success_rate}%${NC}"
            else
                echo -e "   Success rate: ${RED}${success_rate}%${NC} ⚠️"
            fi
        fi
        echo ""
        
        # Использование ресурсов
        echo -e "${BLUE}▶ Ресурсы (Docker Stats):${NC}"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -E "(NAME|staging)" | sed 's/^/   /'
        echo ""
        
        # Последние ошибки
        echo -e "${BLUE}▶ Последние ошибки (если есть):${NC}"
        docker-compose -f docker-compose.staging.yml logs --tail=3 api-staging 2>/dev/null | grep -iE "(error|exception|fail)" | head -5 | sed 's/^/   /' || echo -e "   ${GREEN}Нет ошибок ✅${NC}"
        echo ""
        
        # Оценка готовности к production
        echo -e "${BLUE}▶ Оценка готовности к production:${NC}"
        local ready=true
        
        if [ ${#latencies[@]} -gt 0 ]; then
            local avg_lat=${latencies[-1]}
            [ $avg_lat -lt 2000 ] || ready=false
        fi
        
        if [ $REQUESTS -gt 0 ]; then
            local rate=$((SUCCESSES * 100 / REQUESTS))
            [ $rate -ge 95 ] || ready=false
        fi
        
        if [ "$ready" = true ] && [ $iteration -gt 10 ]; then
            echo -e "   ${GREEN}✅ ВЫГЛЯДИТ СТАБИЛЬНО${NC}"
        else
            echo -e "   ${YELLOW}⏳ НАБЛЮДЕНИЕ...${NC}"
        fi
        
        echo ""
        echo -e "${YELLOW}Обновление через $INTERVAL сек... (Ctrl+C для остановки)${NC}"
        
        sleep $INTERVAL
    done
}

# Завершение
cleanup() {
    echo ""
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              📊 ФИНАЛЬНЫЙ ОТЧЁТ                         ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Лог сохранён: ${CYAN}$LOG_FILE${NC}"
    echo ""
    echo "Итоговая статистика:"
    printf "  Запросов:   %d\n" "$REQUESTS"
    printf "  Успешно:    ${GREEN}%d${NC}\n" "$SUCCESSES"
    printf "  Ошибок:     ${RED}%d${NC}\n" "$FAILURES"
    
    if [ $REQUESTS -gt 0 ]; then
        local rate=$((SUCCESSES * 100 / REQUESTS))
        printf "  Success:    %d%%\n" "$rate"
        
        if [ $rate -ge 98 ]; then
            echo ""
            echo -e "${GREEN}🎉 СИСТЕМА СТАБИЛЬНА - ГОТОВА К PRODUCTION!${NC}"
        elif [ $rate -ge 90 ]; then
            echo ""
            echo -e "${YELLOW}⚠️  НЕПЛОХО, НО МОЖНО ЛУЧШЕ${NC}"
        else
            echo ""
            echo -e "${RED}❌ ЕСТЬ ПРОБЛЕМЫ - НУЖНО ИСПРАВИТЬ${NC}"
        fi
    fi
    
    echo ""
    exit 0
}

# Перехват Ctrl+C
trap cleanup INT

# Запуск
main_loop
