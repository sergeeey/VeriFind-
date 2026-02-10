#!/bin/bash
#
# APE 2026 - Deployment Readiness Check
# Проверка готовности к развёртыванию
#

set -e

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Счётчики
PASSED=0
FAILED=0
WARNINGS=0

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      APE 2026 - Проверка готовности к деплою             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Функция для проверки
check() {
    local name="$1"
    local command="$2"
    local optional="${3:-false}"
    
    echo -n "Проверка: $name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASSED++))
        return 0
    else
        if [ "$optional" = "true" ]; then
            echo -e "${YELLOW}⚠️  WARNING${NC} (опционально)"
            ((WARNINGS++))
        else
            echo -e "${RED}❌ FAIL${NC}"
            ((FAILED++))
        fi
        return 1
    fi
}

# ==================== ПРОВЕРКА 1: Docker ====================
echo -e "${BLUE}▶ Docker и контейнеризация${NC}"
check "Docker установлен" "docker --version"
check "Docker daemon запущен" "docker ps"
check "Docker Compose установлен" "docker-compose --version"
echo ""

# ==================== ПРОВЕРКА 2: Python ====================
echo -e "${BLUE}▶ Python окружение${NC}"
check "Python 3.11+" "python --version | grep -E '3\.(1[1-9]|[2-9][0-9])'"
check "pip установлен" "pip --version"
check "Виртуальное окружение активно" "python -c 'import sys; print(sys.prefix)' | grep -E 'venv|env|\.env'" "true"
echo ""

# ==================== ПРОВЕРКА 3: Файлы проекта ====================
echo -e "${BLUE}▶ Файлы проекта${NC}"
check "docker-compose.yml существует" "test -f docker-compose.yml"
check "requirements.txt существует" "test -f requirements.txt"
check "Папка src/ существует" "test -d src"
check "Папка tests/ существует" "test -d tests"
check "GETTING_STARTED.md существует" "test -f GETTING_STARTED.md"
echo ""

# ==================== ПРОВЕРКА 4: .env файл ====================
echo -e "${BLUE}▶ Конфигурация окружения${NC}"
if check ".env файл существует" "test -f .env"; then
    # Проверяем ключевые переменные
    check "SECRET_KEY установлен" "grep -q 'SECRET_KEY=' .env && ! grep -q 'SECRET_KEY=change-me' .env" "true"
    check "ANTHROPIC_API_KEY или DEEPSEEK_API_KEY" "grep -qE '(ANTHROPIC|DEEPSEEK|OPENAI)_API_KEY=' .env" "true"
    check "NEO4J_PASSWORD установлен" "grep -q 'NEO4J_PASSWORD=' .env" "true"
    check "POSTGRES_PASSWORD установлен" "grep -q 'POSTGRES_PASSWORD=' .env" "true"
else
    echo -e "${YELLOW}   Создайте .env из .env.example:${NC}"
    echo -e "   ${YELLOW}cp .env.example .env${NC}"
fi
echo ""

# ==================== ПРОВЕРКА 5: Зависимости ====================
echo -e "${BLUE}▶ Python зависимости${NC}"
if python -c "import fastapi" 2>/dev/null; then
    echo -e "FastAPI: ${GREEN}✅ установлен${NC}"
    ((PASSED++))
else
    echo -e "FastAPI: ${RED}❌ не найден${NC}"
    echo -e "   ${YELLOW}pip install -r requirements.txt${NC}"
    ((FAILED++))
fi

if python -c "import pytest" 2>/dev/null; then
    echo -e "Pytest: ${GREEN}✅ установлен${NC}"
    ((PASSED++))
else
    echo -e "Pytest: ${YELLOW}⚠️  не найден (опционально)${NC}"
    ((WARNINGS++))
fi
echo ""

# ==================== ПРОВЕРКА 6: Тесты ====================
echo -e "${BLUE}▶ Тесты${NC}"
if [ -f tests/integration/test_api_critical.py ]; then
    echo -e "Критические тесты: ${GREEN}✅ найдены${NC}"
    ((PASSED++))
else
    echo -e "Критические тесты: ${RED}❌ не найдены${NC}"
    ((FAILED++))
fi
echo ""

# ==================== ИТОГ ====================
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      РЕЗУЛЬТАТ                            ║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
printf "${BLUE}║${NC}  ✅ Успешно:   %-3d                                       ${BLUE}║${NC}\n" $PASSED
printf "${BLUE}║${NC}  ⚠️  Предупреждений: %-3d                                ${BLUE}║${NC}\n" $WARNINGS
printf "${BLUE}║${NC}  ❌ Ошибок:    %-3d                                       ${BLUE}║${NC}\n" $FAILED
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Рекомендации
if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}🎉 ВСЁ ГОТОВО К ДЕПЛОЮ!${NC}"
    echo ""
    echo "Следующий шаг:"
    echo -e "  ${GREEN}bash scripts/deploy/deploy_local.sh${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Готово с предупреждениями${NC}"
    echo "Можно деплоить, но обратите внимание на предупреждения выше."
    exit 0
else
    echo -e "${RED}❌ НЕ ГОТОВО К ДЕПЛОЮ${NC}"
    echo ""
    echo "Исправьте ошибки выше и запустите снова."
    exit 1
fi
