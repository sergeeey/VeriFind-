# APE 2026 - Deployment Readiness Check (Windows PowerShell)
# Проверка готовности к развёртыванию

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      APE 2026 - Проверка готовности к деплою             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0
$warnings = 0

function Test-Condition {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [bool]$Optional = $false
    )
    
    Write-Host "Проверка: $Name... " -NoNewline
    
    try {
        $result = & $Test
        if ($result) {
            Write-Host "✅ PASS" -ForegroundColor Green
            $script:passed++
            return $true
        } else {
            throw "Test failed"
        }
    } catch {
        if ($Optional) {
            Write-Host "⚠️  WARNING (опционально)" -ForegroundColor Yellow
            $script:warnings++
        } else {
            Write-Host "❌ FAIL" -ForegroundColor Red
            $script:failed++
        }
        return $false
    }
}

# ==================== ПРОВЕРКА 1: Docker ====================
Write-Host "▶ Docker и контейнеризация" -ForegroundColor Cyan
Test-Condition "Docker установлен" { (docker --version) -match "Docker version" }
Test-Condition "Docker запущен" { (docker ps) -ne $null }
Test-Condition "Docker Compose" { (docker-compose --version) -match "docker-compose version" }
Write-Host ""

# ==================== ПРОВЕРКА 2: Python ====================
Write-Host "▶ Python окружение" -ForegroundColor Cyan
Test-Condition "Python установлен" { (python --version) -match "Python 3\.(1[1-9]|[2-9][0-9])" }
Test-Condition "pip установлен" { (pip --version) -match "pip" }
Write-Host ""

# ==================== ПРОВЕРКА 3: Файлы проекта ====================
Write-Host "▶ Файлы проекта" -ForegroundColor Cyan
Test-Condition "docker-compose.yml" { Test-Path "docker-compose.yml" }
Test-Condition "requirements.txt" { Test-Path "requirements.txt" }
Test-Condition "Папка src/" { Test-Path "src" }
Test-Condition "Папка tests/" { Test-Path "tests" }
Test-Condition "GETTING_STARTED.md" { Test-Path "GETTING_STARTED.md" }
Write-Host ""

# ==================== ПРОВЕРКА 4: .env ====================
Write-Host "▶ Конфигурация окружения" -ForegroundColor Cyan
if (Test-Condition ".env файл" { Test-Path ".env" }) {
    Test-Condition "SECRET_KEY установлен" { 
        (Get-Content ".env" | Select-String "SECRET_KEY=") -and 
        -not (Get-Content ".env" | Select-String "SECRET_KEY=change-me")
    } $true
    
    Test-Condition "API ключи" { 
        Get-Content ".env" | Select-String "(ANTHROPIC|DEEPSEEK|OPENAI)_API_KEY=" 
    } $true
} else {
    Write-Host "   Создайте .env из .env.example:" -ForegroundColor Yellow
    Write-Host "   copy .env.example .env" -ForegroundColor Yellow
}
Write-Host ""

# ==================== ПРОВЕРКА 5: Зависимости ====================
Write-Host "▶ Python зависимости" -ForegroundColor Cyan
try {
    python -c "import fastapi" 2>$null
    Write-Host "FastAPI: ✅ установлен" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "FastAPI: ❌ не найден" -ForegroundColor Red
    Write-Host "   pip install -r requirements.txt" -ForegroundColor Yellow
    $failed++
}

# ==================== ИТОГ ====================
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                      РЕЗУЛЬТАТ                            ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host ("║  ✅ Успешно:   {0,-3}                                       ║" -f $passed) -ForegroundColor Cyan
Write-Host ("║  ⚠️  Предупреждений: {0,-3}                                ║" -f $warnings) -ForegroundColor Cyan
Write-Host ("║  ❌ Ошибок:    {0,-3}                                       ║" -f $failed) -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($failed -eq 0 -and $warnings -eq 0) {
    Write-Host "🎉 ВСЁ ГОТОВО К ДЕПЛОЮ!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Следующий шаг:" -ForegroundColor White
    Write-Host "  .\scripts\deploy\deploy_local.ps1" -ForegroundColor Green
} elseif ($failed -eq 0) {
    Write-Host "⚠️  Готово с предупреждениями" -ForegroundColor Yellow
} else {
    Write-Host "❌ НЕ ГОТОВО К ДЕПЛОЮ" -ForegroundColor Red
}
