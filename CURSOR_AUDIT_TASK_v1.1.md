# ЗАДАНИЕ ДЛЯ CURSOR: Экспресс-аудит APE 2026 (VeriFind) v1.1

**Контекст:** Ты проводишь аудит финансового AI-проекта VeriFind (APE 2026). Нужны ФАКТЫ, не мнения. Выполни все шаги последовательно, результаты запиши в `audit/RESULTS.md`.

**Время:** 1 сессия (45-75 минут). Не планируй — выполняй.

**Версия:** 1.1 (Enhanced) - добавлены проверки response structure, LLM reality check, security scan

---

## ШАГ 0: Подготовка

```bash
mkdir -p audit/data
echo "# APE 2026 AUDIT RESULTS v1.1 — $(date +%Y-%m-%d)" > audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "**Audit Version:** 1.1 (Enhanced)" >> audit/RESULTS.md
echo "**Start Time:** $(date +%H:%M:%S)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 1: Smoke Test — работает ли система?

**Это самый важный шаг. Всё остальное вторично.**

```bash
echo "## 1. SMOKE TEST" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 1.1 Запуск системы

```bash
# Проверить запущен ли Docker
docker ps > /dev/null 2>&1 && echo "Docker running" || echo "Docker not running"

# Попытка запуска (если не запущен)
# docker-compose up -d 2>&1 | tee audit/data/docker_startup.log

# Подождать запуска
sleep 5
```

### 1.2 API Health Check

```bash
# Базовая проверка доступности
echo "### 1.2 API Availability" >> audit/RESULTS.md

curl -s -o /dev/null -w "HTTP Status: %{http_code}\nTime: %{time_total}s\n" \
  http://localhost:8000/health 2>&1 | tee audit/data/health_check.txt

cat audit/data/health_check.txt >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 1.3 Реальный AI запрос

```bash
echo "### 1.3 Real AI Query Test" >> audit/RESULTS.md

# Отправить запрос
curl -s -X POST http://localhost:8000/api/analyze-debate \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current price trend for AAPL and what are the key risks?"}' \
  -w "\nResponse Time: %{time_total}s\n" \
  > audit/data/smoke_test_response.json 2>&1

# Проверить статус
if [ $? -eq 0 ]; then
    echo "- ✅ Request sent successfully" >> audit/RESULTS.md
else
    echo "- ❌ Request failed" >> audit/RESULTS.md
fi
```

### 1.4 Response Structure Analysis (NEW)

```bash
echo "### 1.4 Response Structure Analysis" >> audit/RESULTS.md

python3 << 'PYEOF'
import json
import sys

try:
    with open('audit/data/smoke_test_response.json') as f:
        content = f.read()
        
        # Try to parse JSON
        try:
            data = json.loads(content)
            print("✅ Valid JSON response")
            
            # Check structure
            checks = {
                "Has 'recommendation' or 'analysis'": any(k in data for k in ['recommendation', 'analysis', 'result', 'answer']),
                "Has disclaimer": 'disclaimer' in data or 'not financial advice' in str(data).lower() or 'not investment advice' in str(data).lower(),
                "Has confidence score": any(k in data for k in ['confidence', 'confidence_score', 'certainty']),
                "Has data sources": any(k in data for k in ['sources', 'data_source', 'citations', 'references']),
                "Has debate views": any(k in data for k in ['bull', 'bear', 'arbiter', 'debate', 'agents']),
                "Has cost tracking": any(k in data for k in ['cost', 'cost_usd', 'total_cost', 'tokens']),
            }
            
            for check, result in checks.items():
                status = "✅" if result else "❌"
                print(f"{status} {check}")
            
            # Check if response looks like mock data
            response_str = str(data).lower()
            mock_indicators = ['mock', 'placeholder', 'example', 'lorem ipsum', 'test data']
            is_mock = any(indicator in response_str for indicator in mock_indicators)
            
            if is_mock:
                print("⚠️  WARNING: Response may contain mock data")
            else:
                print("✅ Response appears to be real (no mock indicators)")
            
            # Response size
            print(f"\nResponse size: {len(json.dumps(data))} bytes")
            
            # Top-level keys
            print(f"Top-level keys: {list(data.keys())}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            print(f"Response preview: {content[:200]}")
            
except FileNotFoundError:
    print("❌ Response file not found - API may not be running")
except Exception as e:
    print(f"❌ Error: {e}")
PYEOF

python3 << 'PYEOF' >> audit/RESULTS.md
import json
try:
    with open('audit/data/smoke_test_response.json') as f:
        content = f.read()
        try:
            data = json.loads(content)
            print("\n**Response Structure:**")
            checks = {
                "Valid JSON": True,
                "Has recommendation/analysis": any(k in data for k in ['recommendation', 'analysis', 'result', 'answer']),
                "Has disclaimer": 'disclaimer' in data or 'not financial advice' in str(data).lower(),
                "Has confidence": any(k in data for k in ['confidence', 'confidence_score']),
                "Has sources": any(k in data for k in ['sources', 'data_source', 'citations']),
                "Has debate views": any(k in data for k in ['bull', 'bear', 'arbiter', 'debate']),
                "Has cost tracking": any(k in data for k in ['cost', 'cost_usd', 'tokens']),
            }
            for k, v in checks.items():
                print(f"- {k}: {'✅ YES' if v else '❌ NO'}")
            
            # Mock detection
            response_str = str(data).lower()
            is_mock = any(x in response_str for x in ['mock', 'placeholder', 'example'])
            print(f"- Appears to be real data: {'❌ NO (mock detected)' if is_mock else '✅ YES'}")
            
        except json.JSONDecodeError:
            print("\n❌ Response is not valid JSON")
except:
    print("\n❌ Could not analyze response")
PYEOF

echo "" >> audit/RESULTS.md
```

### 1.5 Smoke Test Summary

```bash
echo "### 1.5 Smoke Test Summary" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "| Check | Status |" >> audit/RESULTS.md
echo "|-------|--------|" >> audit/RESULTS.md

# API доступен
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "| API accessible | ✅ YES |" >> audit/RESULTS.md
else
    echo "| API accessible | ❌ NO |" >> audit/RESULTS.md
fi

# Есть response
if [ -f audit/data/smoke_test_response.json ] && [ -s audit/data/smoke_test_response.json ]; then
    echo "| Response received | ✅ YES |" >> audit/RESULTS.md
else
    echo "| Response received | ❌ NO |" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 2: Реальное состояние кода

```bash
echo "## 2. CODEBASE HEALTH" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 2.1 Масштаб проекта

```bash
echo "### 2.1 Project Scale" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Backend LOC
backend_loc=$(find src/ -name "*.py" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
backend_files=$(find src/ -name "*.py" 2>/dev/null | wc -l)

# Tests LOC
test_loc=$(find tests/ -name "*.py" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
test_files=$(find tests/ -name "*.py" 2>/dev/null | wc -l)

# Frontend LOC (if exists)
frontend_loc=$(find frontend/ -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
frontend_files=$(find frontend/ \( -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" \) 2>/dev/null | wc -l)

echo "| Component | Files | Lines of Code |" >> audit/RESULTS.md
echo "|-----------|-------|---------------|" >> audit/RESULTS.md
echo "| Backend (src/) | $backend_files | $backend_loc |" >> audit/RESULTS.md
echo "| Tests | $test_files | $test_loc |" >> audit/RESULTS.md
echo "| Frontend | $frontend_files | $frontend_loc |" >> audit/RESULTS.md

# Test/Code ratio
if [ "$backend_loc" -gt 0 ]; then
    ratio=$(echo "scale=2; $test_loc * 100 / $backend_loc" | bc)
    echo "| **Test/Code ratio** | - | **${ratio}%** |" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 2.2 Критические заглушки (NotImplementedError)

```bash
echo "### 2.2 NotImplementedError (CRITICAL BLOCKERS)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Поиск NotImplementedError
grep -rn "NotImplementedError\|raise NotImplemented" src/ --include="*.py" > audit/data/not_implemented.txt 2>&1

nie_count=$(wc -l < audit/data/not_implemented.txt)

echo "**Total NotImplementedError found:** $nie_count" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

if [ "$nie_count" -gt 0 ]; then
    echo "**Details:**" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    head -20 audit/data/not_implemented.txt >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    
    if [ "$nie_count" -gt 3 ]; then
        echo "" >> audit/RESULTS.md
        echo "⚠️  **BLOCKER:** >3 NotImplementedError found - core functionality missing" >> audit/RESULTS.md
    fi
else
    echo "✅ No NotImplementedError found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 2.3 TODO/FIXME/HACK markers

```bash
echo "### 2.3 Technical Debt Markers" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

todo_count=$(grep -rc "TODO" src/ --include="*.py" 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
fixme_count=$(grep -rc "FIXME" src/ --include="*.py" 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
hack_count=$(grep -rc "HACK\|XXX" src/ --include="*.py" 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')

echo "| Marker | Count |" >> audit/RESULTS.md
echo "|--------|-------|" >> audit/RESULTS.md
echo "| TODO | $todo_count |" >> audit/RESULTS.md
echo "| FIXME | $fixme_count |" >> audit/RESULTS.md
echo "| HACK/XXX | $hack_count |" >> audit/RESULTS.md
echo "| **TOTAL** | **$((todo_count + fixme_count + hack_count))** |" >> audit/RESULTS.md

echo "" >> audit/RESULTS.md

# Sample critical TODOs
echo "<details>" >> audit/RESULTS.md
echo "<summary>Sample markers (first 15)</summary>" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo '```' >> audit/RESULTS.md
grep -rn "TODO\|FIXME\|HACK" src/ --include="*.py" 2>/dev/null | head -15 >> audit/RESULTS.md
echo '```' >> audit/RESULTS.md
echo "</details>" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 2.4 God Objects (files > 500 LOC)

```bash
echo "### 2.4 God Objects (>500 LOC)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

find src/ -name "*.py" -exec wc -l {} \; 2>/dev/null | \
  awk '$1 > 500 {print $0}' | \
  sort -rn > audit/data/large_files.txt

large_count=$(wc -l < audit/data/large_files.txt)

echo "**Files >500 LOC:** $large_count" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

if [ "$large_count" -gt 0 ]; then
    echo "| File | LOC |" >> audit/RESULTS.md
    echo "|------|-----|" >> audit/RESULTS.md
    cat audit/data/large_files.txt | head -10 | awk '{print "| " $2 " | " $1 " |"}' >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    
    if [ "$large_count" -gt 5 ]; then
        echo "⚠️  Multiple God Objects found - consider refactoring" >> audit/RESULTS.md
    fi
else
    echo "✅ No God Objects found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 2.5 Git состояние

```bash
echo "### 2.5 Git Status" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

current_branch=$(git branch --show-current 2>/dev/null)
last_commit=$(git log -1 --oneline 2>/dev/null)
uncommitted=$(git status --short 2>/dev/null | wc -l)
unmerged=$(git branch --no-merged master 2>/dev/null | wc -l)

echo "| Item | Value |" >> audit/RESULTS.md
echo "|------|-------|" >> audit/RESULTS.md
echo "| Current branch | \`$current_branch\` |" >> audit/RESULTS.md
echo "| Last commit | $last_commit |" >> audit/RESULTS.md
echo "| Uncommitted changes | $uncommitted files |" >> audit/RESULTS.md
echo "| Unmerged branches | $unmerged |" >> audit/RESULTS.md

echo "" >> audit/RESULTS.md

# Show unmerged branches
if [ "$unmerged" -gt 0 ]; then
    echo "**Unmerged branches:**" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    git branch --no-merged master 2>/dev/null >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
fi

# Recent commits
echo "<details>" >> audit/RESULTS.md
echo "<summary>Recent commits (last 10)</summary>" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo '```' >> audit/RESULTS.md
git log --oneline -10 2>/dev/null >> audit/RESULTS.md
echo '```' >> audit/RESULTS.md
echo "</details>" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 3: Тесты — реальная картина

```bash
echo "## 3. TESTING & QA" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 3.1 Запуск тестов

```bash
echo "### 3.1 Test Execution" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Run tests
pytest --tb=short -q 2>&1 | tee audit/data/test_results.txt

# Parse results
total=$(grep -oP '\d+(?= passed)' audit/data/test_results.txt | tail -1)
passed=$(grep -oP '\d+(?= passed)' audit/data/test_results.txt | tail -1)
failed=$(grep -oP '\d+(?= failed)' audit/data/test_results.txt | tail -1)
skipped=$(grep -oP '\d+(?= skipped)' audit/data/test_results.txt | tail -1)

# Defaults if not found
total=${total:-0}
passed=${passed:-0}
failed=${failed:-0}
skipped=${skipped:-0}

echo "| Metric | Count |" >> audit/RESULTS.md
echo "|--------|-------|" >> audit/RESULTS.md
echo "| Total | $total |" >> audit/RESULTS.md
echo "| ✅ Passed | $passed |" >> audit/RESULTS.md
echo "| ❌ Failed | $failed |" >> audit/RESULTS.md
echo "| ⏭️  Skipped | $skipped |" >> audit/RESULTS.md

if [ "$total" -gt 0 ]; then
    pass_rate=$(echo "scale=1; $passed * 100 / $total" | bc)
    echo "| **Pass Rate** | **${pass_rate}%** |" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md

if [ "$failed" -gt 0 ]; then
    echo "⚠️  **WARNING:** $failed tests failing" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
fi
```

### 3.2 Code Coverage

```bash
echo "### 3.2 Code Coverage" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Try to run coverage
pytest --cov=src --cov-report=term-missing -q 2>&1 | tee audit/data/coverage_results.txt > /dev/null 2>&1

# Parse coverage
coverage=$(grep -oP '\d+%' audit/data/coverage_results.txt | tail -1)

if [ -n "$coverage" ]; then
    echo "**Overall Coverage:** $coverage" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    
    # Show coverage by module
    echo "<details>" >> audit/RESULTS.md
    echo "<summary>Coverage by module</summary>" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    tail -30 audit/data/coverage_results.txt >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "</details>" >> audit/RESULTS.md
else
    echo "Coverage analysis not available" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 3.3 Моки vs реальные вызовы

```bash
echo "### 3.3 Mock vs Real Integration Analysis" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Count test files
total_test_files=$(find tests/ -name "test_*.py" 2>/dev/null | wc -l)

# Count files with mocks
mock_files=$(grep -rl "@patch\|Mock(\|MagicMock\|mock_\|@mock" tests/ --include="*.py" 2>/dev/null | wc -l)

# Count files with real API calls
real_api_files=$(grep -rl "httpx\|requests\.get\|requests\.post\|aiohttp\.ClientSession" tests/ --include="*.py" 2>/dev/null | wc -l)

echo "| Type | Count | Percentage |" >> audit/RESULTS.md
echo "|------|-------|------------|" >> audit/RESULTS.md
echo "| Total test files | $total_test_files | 100% |" >> audit/RESULTS.md
echo "| Files with mocks | $mock_files | $((mock_files * 100 / total_test_files))% |" >> audit/RESULTS.md
echo "| Files with real API calls | $real_api_files | $((real_api_files * 100 / total_test_files))% |" >> audit/RESULTS.md

echo "" >> audit/RESULTS.md

if [ "$mock_files" -gt "$((total_test_files * 80 / 100))" ]; then
    echo "⚠️  **WARNING:** >80% tests use mocks - limited real integration testing" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
fi
```

### 3.4 Golden Set

```bash
echo "### 3.4 Golden Set Validation" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Find golden set files
golden_files=$(find . -iname "*golden*" -o -iname "*baseline*" 2>/dev/null | grep -v ".git\|node_modules\|__pycache__" | head -10)

if [ -n "$golden_files" ]; then
    echo "**Golden Set files found:**" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "$golden_files" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    
    # Check for results
    if [ -f "tests/golden_set_results.json" ]; then
        echo "**Latest results found**" >> audit/RESULTS.md
        python3 << 'PYEOF' >> audit/RESULTS.md
import json
try:
    with open('tests/golden_set_results.json') as f:
        data = json.load(f)
        if 'accuracy' in data:
            print(f"- Accuracy: {data['accuracy']}")
        if 'total' in data:
            print(f"- Total queries: {data['total']}")
        if 'hit_rate' in data:
            print(f"- Hit rate: {data['hit_rate']}")
except:
    print("Could not parse results")
PYEOF
    fi
else
    echo "❌ No Golden Set files found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 4: LLM интеграции — ядро продукта

```bash
echo "## 4. LLM INTEGRATIONS (CORE PRODUCT)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 4.1 Environment Variables Check

```bash
echo "### 4.1 API Keys Configuration" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Check .env exists
if [ -f .env ]; then
    echo "✅ .env file exists" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    
    # Check for API keys (don't show values!)
    echo "| Provider | Configured |" >> audit/RESULTS.md
    echo "|----------|------------|" >> audit/RESULTS.md
    
    for provider in DEEPSEEK OPENAI ANTHROPIC GEMINI; do
        if grep -q "${provider}_API_KEY" .env 2>/dev/null; then
            echo "| $provider | ✅ YES |" >> audit/RESULTS.md
        else
            echo "| $provider | ❌ NO |" >> audit/RESULTS.md
        fi
    done
else
    echo "❌ .env file not found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 4.2 LLM Provider Implementation Status (NEW - ENHANCED)

```bash
echo "### 4.2 LLM Provider Reality Check" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Find LLM-related files
llm_files=$(find src/ -type f -name "*.py" 2>/dev/null | xargs grep -l "deepseek\|openai\|anthropic\|gemini\|claude" 2>/dev/null)

echo "**LLM-related files found:** $(echo "$llm_files" | wc -l)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Check implementation status for each provider
echo "| Provider | Status | Evidence |" >> audit/RESULTS.md
echo "|----------|--------|----------|" >> audit/RESULTS.md

for provider in deepseek openai anthropic gemini; do
    # Look for function definitions
    func_def=$(grep -rn "def.*$provider\|def.*call.*$provider" src/ --include="*.py" 2>/dev/null | head -1)
    
    if [ -n "$func_def" ]; then
        # Check if it's implemented or mocked
        file=$(echo "$func_def" | cut -d: -f1)
        
        # Check next 15 lines for NotImplementedError
        line_num=$(echo "$func_def" | cut -d: -f2)
        nie_check=$(sed -n "${line_num},$((line_num+15))p" "$file" 2>/dev/null | grep -c "NotImplementedError\|raise Exception\|pass  # TODO")
        
        # Check for mock/fake
        mock_check=$(sed -n "${line_num},$((line_num+15))p" "$file" 2>/dev/null | grep -c "mock\|fake\|placeholder")
        
        # Check for real API call
        real_check=$(sed -n "${line_num},$((line_num+20))p" "$file" 2>/dev/null | grep -c "requests\|httpx\|aiohttp\|openai\|anthropic")
        
        if [ "$nie_check" -gt 0 ]; then
            echo "| $provider | ❌ NOT IMPLEMENTED | NotImplementedError found |" >> audit/RESULTS.md
        elif [ "$mock_check" -gt 0 ]; then
            echo "| $provider | ⚠️  MOCK | Mock/placeholder detected |" >> audit/RESULTS.md
        elif [ "$real_check" -gt 0 ]; then
            echo "| $provider | ✅ REAL | Real API call found |" >> audit/RESULTS.md
        else
            echo "| $provider | ❓ UNCLEAR | Needs manual check |" >> audit/RESULTS.md
        fi
    else
        echo "| $provider | ❌ NOT FOUND | No implementation |" >> audit/RESULTS.md
    fi
done

echo "" >> audit/RESULTS.md

# Show sample implementations
echo "<details>" >> audit/RESULTS.md
echo "<summary>Sample LLM function signatures</summary>" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo '```python' >> audit/RESULTS.md
grep -rn "def.*deepseek\|def.*openai\|def.*anthropic\|def.*call.*llm" src/ --include="*.py" 2>/dev/null | head -10 >> audit/RESULTS.md
echo '```' >> audit/RESULTS.md
echo "</details>" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 4.3 Debate System

```bash
echo "### 4.3 Multi-Agent Debate System" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Find debate files
debate_files=$(find src/ -path "*debate*" -name "*.py" 2>/dev/null)

if [ -n "$debate_files" ]; then
    echo "**Debate system files found:** $(echo "$debate_files" | wc -l)" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    
    # Check for agents
    echo "**Agent Detection:**" >> audit/RESULTS.md
    for agent in bull bear neutral arbiter trust skeptic leader; do
        if grep -rqi "$agent.*agent\|${agent}Agent" src/ --include="*.py" 2>/dev/null; then
            echo "- ✅ $agent agent found" >> audit/RESULTS.md
        else
            echo "- ❌ $agent agent not found" >> audit/RESULTS.md
        fi
    done
    
    echo "" >> audit/RESULTS.md
    
    # Check debate files for NotImplementedError
    debate_nie=$(grep -rn "NotImplementedError" $debate_files 2>/dev/null | wc -l)
    echo "**NotImplementedError in debate system:** $debate_nie" >> audit/RESULTS.md
else
    echo "❌ No debate system files found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 4.4 Conformal Prediction

```bash
echo "### 4.4 Conformal Prediction (Phase 1)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Check for conformal prediction
conformal_files=$(find src/ -iname "*conformal*" -name "*.py" 2>/dev/null)

if [ -n "$conformal_files" ]; then
    echo "✅ Conformal prediction files found" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "$conformal_files" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    
    # Check tests
    conformal_tests=$(find tests/ -iname "*conformal*" -name "*.py" 2>/dev/null | wc -l)
    echo "- Conformal tests: $conformal_tests files" >> audit/RESULTS.md
    
    # Check for integration
    if grep -rq "conformal" src/predictions/ src/api/ 2>/dev/null; then
        echo "- Integration status: ✅ Integrated into pipeline" >> audit/RESULTS.md
    else
        echo "- Integration status: ⚠️  Standalone (not integrated)" >> audit/RESULTS.md
    fi
else
    echo "❌ Conformal prediction not found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 5: Базы данных — живые или пустые?

```bash
echo "## 5. DATABASES & STORAGE" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 5.1 TimescaleDB

```bash
echo "### 5.1 TimescaleDB" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

python3 << 'PYEOF' 2>&1 | tee audit/data/timescaledb_check.txt
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

async def check():
    try:
        # Try multiple env var names
        db_url = os.getenv('TIMESCALE_URL') or os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        if not db_url:
            print("❌ No database URL found in environment")
            return
        
        conn = await asyncpg.connect(db_url, timeout=5)
        print("✅ Connection successful")
        
        # Get tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
            ORDER BY table_name
        """)
        
        print(f"\n📊 Tables: {len(tables)}")
        
        for t in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {t['table_name']}")
                status = "✅" if count > 0 else "⚠️ "
                print(f"{status} {t['table_name']}: {count:,} rows")
            except Exception as e:
                print(f"❌ {t['table_name']}: Error - {e}")
        
        # Check for hypertables
        try:
            hypertables = await conn.fetch("SELECT hypertable_name FROM timescaledb_information.hypertables")
            if hypertables:
                print(f"\n⏰ Hypertables: {len(hypertables)}")
                for ht in hypertables:
                    print(f"  - {ht['hypertable_name']}")
            else:
                print("\n⚠️  No hypertables configured")
        except:
            print("\n⚠️  TimescaleDB extension not detected")
        
        await conn.close()
        
    except asyncio.TimeoutError:
        print("❌ Connection timeout")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(check())
PYEOF

cat audit/data/timescaledb_check.txt >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 5.2 Neo4j

```bash
echo "### 5.2 Neo4j" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

python3 << 'PYEOF' 2>&1 | tee audit/data/neo4j_check.txt
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()

try:
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', '')
    
    if not password:
        print("⚠️  No Neo4j password in environment")
    
    driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=5)
    
    with driver.session() as s:
        # Test connection
        s.run("RETURN 1").single()
        print("✅ Connection successful")
        
        # Node count
        nodes = s.run("MATCH (n) RETURN count(n) as c").single()['c']
        print(f"\n📊 Total nodes: {nodes:,}")
        
        # Nodes by label
        if nodes > 0:
            labels = s.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC LIMIT 10").data()
            print("\n🏷️  Top labels:")
            for l in labels:
                print(f"  - {l['label']}: {l['count']:,} nodes")
        
        # Relationship count
        rels = s.run("MATCH ()-[r]->() RETURN count(r) as c").single()['c']
        print(f"\n🔗 Total relationships: {rels:,}")
        
        # Relationships by type
        if rels > 0:
            rel_types = s.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC LIMIT 10").data()
            print("\n🔗 Top relationship types:")
            for r in rel_types:
                print(f"  - {r['type']}: {r['count']:,} relationships")
        
        # Orphaned nodes
        orphans = s.run("MATCH (n) WHERE NOT (n)--() RETURN count(n) as c").single()['c']
        if orphans > 0:
            print(f"\n⚠️  Orphaned nodes: {orphans:,} (nodes with no relationships)")
        
        # Check for indexes
        try:
            indexes = s.run("SHOW INDEXES").data()
            print(f"\n📇 Indexes: {len(indexes)}")
        except:
            print("\n⚠️  Could not query indexes")
    
    driver.close()
    
    if nodes == 0:
        print("\n❌ Database is EMPTY")
    
except Exception as e:
    print(f"❌ Error: {e}")
PYEOF

cat audit/data/neo4j_check.txt >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 5.3 Redis

```bash
echo "### 5.3 Redis" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

python3 << 'PYEOF' 2>&1 | tee audit/data/redis_check.txt
import redis
import os
from dotenv import load_dotenv
load_dotenv()

try:
    url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    r = redis.from_url(url, socket_connect_timeout=5)
    
    # Test connection
    if r.ping():
        print("✅ Connection successful")
    
    # Key count
    dbsize = r.dbsize()
    print(f"\n📊 Total keys: {dbsize:,}")
    
    # Memory info
    info = r.info('memory')
    print(f"💾 Memory used: {info['used_memory_human']}")
    print(f"💾 Memory peak: {info['used_memory_peak_human']}")
    
    # Sample keys
    if dbsize > 0:
        keys = r.keys('*')[:10]
        print(f"\n🔑 Sample keys (first 10):")
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            key_type = r.type(key).decode() if isinstance(r.type(key), bytes) else r.type(key)
            ttl = r.ttl(key)
            ttl_str = f"{ttl}s" if ttl > 0 else "no expiry" if ttl == -1 else "expired"
            print(f"  - {key_str} ({key_type}, TTL: {ttl_str})")
    
    # Stats
    stats = r.info('stats')
    print(f"\n📊 Total connections received: {stats.get('total_connections_received', 'N/A')}")
    print(f"📊 Total commands processed: {stats.get('total_commands_processed', 'N/A')}")
    
except redis.exceptions.ConnectionError:
    print("❌ Connection failed - Redis not running?")
except Exception as e:
    print(f"❌ Error: {e}")
PYEOF

cat audit/data/redis_check.txt >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 6: Compliance (юридический блокер)

```bash
echo "## 6. COMPLIANCE & LEGAL" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 6.1 Disclaimer Presence

```bash
echo "### 6.1 Financial Disclaimer" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Search in code
echo "**Backend (API responses):**" >> audit/RESULTS.md
backend_disclaimer=$(grep -ri "not financial advice\|not investment advice\|disclaimer" src/ --include="*.py" | wc -l)

if [ "$backend_disclaimer" -gt 0 ]; then
    echo "- ✅ Found in backend code ($backend_disclaimer occurrences)" >> audit/RESULTS.md
else
    echo "- ❌ NOT FOUND in backend code" >> audit/RESULTS.md
fi

# Search in frontend
echo "" >> audit/RESULTS.md
echo "**Frontend (UI):**" >> audit/RESULTS.md
frontend_disclaimer=$(grep -ri "not financial advice\|not investment advice\|disclaimer" frontend/ --include="*.tsx" --include="*.jsx" --include="*.ts" 2>/dev/null | wc -l)

if [ "$frontend_disclaimer" -gt 0 ]; then
    echo "- ✅ Found in frontend code ($frontend_disclaimer occurrences)" >> audit/RESULTS.md
else
    echo "- ❌ NOT FOUND in frontend code" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md

# Check actual API response (from smoke test)
if [ -f audit/data/smoke_test_response.json ]; then
    echo "**Live API Response Check:**" >> audit/RESULTS.md
    if grep -qi "not financial advice\|not investment advice\|disclaimer" audit/data/smoke_test_response.json; then
        echo "- ✅ Disclaimer PRESENT in actual API response" >> audit/RESULTS.md
    else
        echo "- ❌ Disclaimer MISSING in actual API response ⚠️  BLOCKER" >> audit/RESULTS.md
    fi
else
    echo "- ⚠️  Could not check live API response" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 6.2 Audit Trail

```bash
echo "### 6.2 Audit Trail & Traceability" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

audit_code=$(grep -ri "audit.*log\|audit.*trail\|AuditLog\|immutable.*log" src/ --include="*.py" | wc -l)

if [ "$audit_code" -gt 0 ]; then
    echo "- ✅ Audit logging code found ($audit_code occurrences)" >> audit/RESULTS.md
else
    echo "- ❌ No audit logging code found" >> audit/RESULTS.md
fi

# Check for data source attribution
echo "" >> audit/RESULTS.md
echo "**Data Source Attribution:**" >> audit/RESULTS.md
source_attr=$(grep -ri "source.*attribution\|data_source\|citation\|reference" src/ --include="*.py" | wc -l)

if [ "$source_attr" -gt 0 ]; then
    echo "- ✅ Source attribution code found ($source_attr occurrences)" >> audit/RESULTS.md
else
    echo "- ⚠️  No source attribution found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 6.3 Marketing Claims Check

```bash
echo "### 6.3 Marketing Claims Verification" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Check for dangerous claims
echo "**Checking for potentially problematic claims:**" >> audit/RESULTS.md

dangerous_claims=0

if grep -rqi "zero hallucination\|no hallucination\|100% accurate\|guaranteed" README.md docs/ frontend/ 2>/dev/null; then
    echo "- ⚠️  **WARNING**: Found 'zero hallucination' or similar absolute claims" >> audit/RESULTS.md
    dangerous_claims=$((dangerous_claims + 1))
fi

if grep -rqi "guaranteed returns\|guaranteed profit\|sure profit" README.md docs/ frontend/ 2>/dev/null; then
    echo "- ⚠️  **WARNING**: Found 'guaranteed returns' claims" >> audit/RESULTS.md
    dangerous_claims=$((dangerous_claims + 1))
fi

if [ "$dangerous_claims" -eq 0 ]; then
    echo "- ✅ No problematic absolute claims found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 7: Стоимость и зависимости

```bash
echo "## 7. COST TRACKING & DEPENDENCIES" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 7.1 Cost Tracking Implementation

```bash
echo "### 7.1 Cost Tracking" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Search for cost tracking code
cost_tracking=$(grep -ri "cost.*usd\|total_cost\|cost_per\|track.*cost" src/ --include="*.py" | wc -l)

if [ "$cost_tracking" -gt 0 ]; then
    echo "- ✅ Cost tracking code found ($cost_tracking occurrences)" >> audit/RESULTS.md
    
    # Look for middleware/logging
    if grep -rq "cost.*middleware\|cost.*logger" src/ --include="*.py"; then
        echo "- ✅ Cost tracking middleware/logger detected" >> audit/RESULTS.md
    fi
else
    echo "- ❌ No cost tracking code found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 7.2 Dependencies

```bash
echo "### 7.2 Dependencies" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Count dependencies
if [ -f requirements.txt ]; then
    dep_count=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l)
    echo "**Python dependencies:** $dep_count packages" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    
    # Check for critical ones
    echo "<details>" >> audit/RESULTS.md
    echo "<summary>Critical dependencies</summary>" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    grep -E "fastapi|langchain|langgraph|neo4j|timescale|redis|openai|anthropic" requirements.txt 2>/dev/null >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "</details>" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md

# Frontend dependencies
if [ -f frontend/package.json ]; then
    fe_dep_count=$(cat frontend/package.json | grep -c '".*":')
    echo "**Frontend dependencies:** ~$fe_dep_count packages" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 7.3 Docker

```bash
echo "### 7.3 Docker Infrastructure" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Check Docker images
if command -v docker &> /dev/null; then
    echo "**Docker images:**" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    docker images 2>/dev/null | grep -E "ape|verifind|REPOSITORY" | head -10 >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    
    # Running containers
    echo "**Running containers:**" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
else
    echo "Docker not available" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 8: Security Quick Scan (NEW)

```bash
echo "## 8. SECURITY SCAN (QUICK)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 8.1 Secrets in Code

```bash
echo "### 8.1 Hardcoded Secrets Check" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Look for potential hardcoded secrets
secret_patterns=$(grep -r "password.*=.*['\"].\{8,\}['\"]" src/ --include="*.py" 2>/dev/null | grep -v "getenv\|os.environ" | wc -l)

if [ "$secret_patterns" -gt 0 ]; then
    echo "⚠️  **WARNING:** Found $secret_patterns potential hardcoded secrets" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    echo "<details>" >> audit/RESULTS.md
    echo "<summary>Show findings</summary>" >> audit/RESULTS.md
    echo "" >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    grep -rn "password.*=.*['\"].\{8,\}['\"]" src/ --include="*.py" 2>/dev/null | grep -v "getenv\|os.environ" | head -10 >> audit/RESULTS.md
    echo '```' >> audit/RESULTS.md
    echo "</details>" >> audit/RESULTS.md
else
    echo "✅ No obvious hardcoded secrets found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 8.2 SQL Injection Risks

```bash
echo "### 8.2 SQL Injection Risk" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Look for string formatting in SQL
sql_risks=$(grep -rn "execute.*%\|execute.*format\|execute.*f\"" src/ --include="*.py" 2>/dev/null | wc -l)

if [ "$sql_risks" -gt 0 ]; then
    echo "⚠️  **WARNING:** Found $sql_risks potential SQL injection risks" >> audit/RESULTS.md
else
    echo "✅ No obvious SQL injection patterns found" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
```

### 8.3 Dependency Vulnerabilities

```bash
echo "### 8.3 Dependency Vulnerabilities" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

# Try pip-audit if available
if command -v pip-audit &> /dev/null; then
    echo "Running pip-audit..." >> audit/RESULTS.md
    pip-audit --format json > audit/data/security_audit.json 2>&1
    
    vulns=$(cat audit/data/security_audit.json | grep -c '"vulnerability"' 2>/dev/null || echo "0")
    echo "**Vulnerabilities found:** $vulns" >> audit/RESULTS.md
else
    echo "⚠️  pip-audit not installed - skipping vulnerability scan" >> audit/RESULTS.md
fi

echo "" >> audit/RESULTS.md
echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

---

## ШАГ 9: Финальный отчёт и оценка

```bash
echo "## 9. SUMMARY & FINAL ASSESSMENT" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 9.1 Итоговая таблица

```bash
echo "### 9.1 Component Status Matrix" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md

cat >> audit/RESULTS.md << 'TABLE'
| # | Component | Status | Grade | Blocker? |
|---|-----------|--------|-------|----------|
| 1 | API запускается | CHECK | /10 | |
| 2 | Real AI response (not mock) | CHECK | /10 | ⚠️ |
| 3 | DeepSeek integration | CHECK | /10 | ⚠️ |
| 4 | OpenAI integration | CHECK | /10 | |
| 5 | Anthropic integration | CHECK | /10 | |
| 6 | Debate system working | CHECK | /10 | |
| 7 | Conformal Prediction | CHECK | /10 | |
| 8 | Tests passing | CHECK | /10 | |
| 9 | TimescaleDB has data | CHECK | /10 | |
| 10 | Neo4j has data | CHECK | /10 | |
| 11 | Redis working | CHECK | /10 | |
| 12 | Disclaimer in responses | CHECK | /10 | ⚠️ BLOCKER |
| 13 | Audit trail implemented | CHECK | /10 | |
| 14 | Cost tracking working | CHECK | /10 | |
| 15 | NotImplementedError count | CHECK | /10 | ⚠️ if >3 |
| 16 | God Objects (>500 LOC) | CHECK | /10 | |
| 17 | Test coverage | CHECK | /10 | |
| 18 | Golden Set validated | CHECK | /10 | |

TABLE

echo "" >> audit/RESULTS.md
echo "**Instructions:** Review findings above and fill in CHECK values with actual status (✅/⚠️/❌)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 9.2 Critical Blockers

```bash
echo "### 9.2 TOP-5 CRITICAL BLOCKERS" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "Based on audit findings, identify and list the 5 most critical issues:" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "1. **[FILL IN]** - Priority: HIGH/CRITICAL" >> audit/RESULTS.md
echo "   - Impact: ___" >> audit/RESULTS.md
echo "   - Fix time: ___" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "2. **[FILL IN]** - Priority: HIGH/CRITICAL" >> audit/RESULTS.md
echo "   - Impact: ___" >> audit/RESULTS.md
echo "   - Fix time: ___" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "3. **[FILL IN]** - Priority: MEDIUM/HIGH" >> audit/RESULTS.md
echo "   - Impact: ___" >> audit/RESULTS.md
echo "   - Fix time: ___" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "4. **[FILL IN]** - Priority: MEDIUM" >> audit/RESULTS.md
echo "   - Impact: ___" >> audit/RESULTS.md
echo "   - Fix time: ___" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "5. **[FILL IN]** - Priority: MEDIUM/LOW" >> audit/RESULTS.md
echo "   - Impact: ___" >> audit/RESULTS.md
echo "   - Fix time: ___" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 9.3 Strengths

```bash
echo "### 9.3 TOP-5 STRENGTHS" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "1. **[FILL IN]** - What works well" >> audit/RESULTS.md
echo "2. **[FILL IN]** - Core capability" >> audit/RESULTS.md
echo "3. **[FILL IN]** - Quality indicator" >> audit/RESULTS.md
echo "4. **[FILL IN]** - Competitive advantage" >> audit/RESULTS.md
echo "5. **[FILL IN]** - Technical excellence" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 9.4 Overall Grade

```bash
echo "### 9.4 OVERALL PROJECT GRADE" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "**Grade:** ___/10" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "**Readiness for Production:** ⬜ Ready ⬜ Almost ⬜ Needs Work ⬜ Not Ready" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "**Readiness for Historical Context Engine:** ⬜ GO ⬜ GO with fixes ⬜ NO-GO" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 9.5 Recommendations

```bash
echo "### 9.5 RECOMMENDATIONS" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "Based on audit findings, recommended next steps:" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "**Immediate (Week 1):**" >> audit/RESULTS.md
echo "1. [FILL IN]" >> audit/RESULTS.md
echo "2. [FILL IN]" >> audit/RESULTS.md
echo "3. [FILL IN]" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "**Short-term (Weeks 2-4):**" >> audit/RESULTS.md
echo "1. [FILL IN]" >> audit/RESULTS.md
echo "2. [FILL IN]" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "**Long-term (Months 2-3):**" >> audit/RESULTS.md
echo "1. [FILL IN]" >> audit/RESULTS.md
echo "2. [FILL IN]" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
```

### 9.6 Metadata

```bash
echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "## AUDIT METADATA" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "- **Audit Version:** 1.1 (Enhanced)" >> audit/RESULTS.md
echo "- **Completion Time:** $(date +%Y-%m-%d\ %H:%M:%S)" >> audit/RESULTS.md
echo "- **Duration:** [FILL IN] minutes" >> audit/RESULTS.md
echo "- **Auditor:** Cursor AI + Human Review" >> audit/RESULTS.md
echo "- **Project Version:** $(git describe --tags 2>/dev/null || git log -1 --format=%h)" >> audit/RESULTS.md
echo "- **Files Generated:**" >> audit/RESULTS.md
echo "  - audit/RESULTS.md (main report)" >> audit/RESULTS.md
echo "  - audit/data/* (raw data)" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "---" >> audit/RESULTS.md
echo "" >> audit/RESULTS.md
echo "**End of Audit Report**" >> audit/RESULTS.md
```

---

## ПРАВИЛА ДЛЯ CURSOR (UPDATED)

1. **НЕ ПРИДУМЫВАЙ данные.** Если команда не сработала — запиши ошибку как есть.
2. **НЕ ПРИУКРАШИВАЙ.** Если 95% тестов на моках — так и напиши.
3. **НЕ ПЛАНИРУЙ.** Этот аудит — сбор фактов, не план действий.
4. **ВЫПОЛНЯЙ КОМАНДЫ РЕАЛЬНО.** Каждый `grep`, `pytest`, `curl` — запусти и запиши вывод.
5. **ЕСЛИ СЕРВИС НЕ ЗАПУЩЕН** — запиши "НЕ ЗАПУЩЕН" и продолжай с проверки кода.
6. **ФАЙЛ `audit/RESULTS.md`** — единственный deliverable. Всё остальное — промежуточное.
7. **ПОСЛЕ КАЖДОГО ШАГА** — проверяй что данные записались в RESULTS.md
8. **В КОНЦЕ** — заполни Summary таблицу и топ-5 списки на основе РЕАЛЬНЫХ находок

---

## ОЖИДАЕМОЕ ВРЕМЯ: 45-75 минут

**Версия 1.1 улучшения:**
- ✅ Response structure validation (Step 1.4)
- ✅ LLM reality check - real vs mock detection (Step 4.2)
- ✅ Live API response compliance check (Step 6.1)
- ✅ Security quick scan (Step 8)
- ✅ Better error handling in Python checks
- ✅ More detailed status tables
- ✅ Expandable details sections

Если за 75 минут не закончил — останови и отдай что есть с пометкой "INCOMPLETE" в незаконченных секциях.
