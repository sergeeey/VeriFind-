# Диагностика ошибки 503
$API_URL = "http://localhost:8000"

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  ДИАГНОСТИКА: Ошибка 503 Service Unavailable             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Проверка 1: Health
Write-Host "▶ Проверка 1: Health endpoint" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$API_URL/health" -TimeoutSec 5
    Write-Host "   Status: $($health.status)" -ForegroundColor $(if($health.status -eq "healthy"){"Green"}else{"Yellow"})
    Write-Host "   Components:" -ForegroundColor Gray
    $health.components.PSObject.Properties | ForEach-Object {
        $color = if($_.Value -eq "up"){"Green"}elseif($_.Value -eq "degraded"){"Yellow"}else{"Red"}
        Write-Host "      $($_.Name): $($_.Value)" -ForegroundColor $color
    }
} catch {
    Write-Host "   ❌ Не отвечает: $_" -ForegroundColor Red
}
Write-Host ""

# Проверка 2: Простые endpoints
Write-Host "▶ Проверка 2: Простые endpoints (без AI)" -ForegroundColor Yellow

try {
    $tickers = Invoke-RestMethod -Uri "$API_URL/api/data/tickers" -TimeoutSec 5
    Write-Host "   ✅ /api/data/tickers: $($tickers.tickers.Count) тикеров" -ForegroundColor Green
} catch {
    Write-Host "   ❌ /api/data/tickers: Ошибка" -ForegroundColor Red
}

try {
    $preds = Invoke-RestMethod -Uri "$API_URL/api/predictions/" -TimeoutSec 5
    Write-Host "   ✅ /api/predictions/: $($preds.predictions.Count) прогнозов" -ForegroundColor Green
} catch {
    Write-Host "   ❌ /api/predictions/: Ошибка" -ForegroundColor Red
}
Write-Host ""

# Проверка 3: Environment
Write-Host "▶ Проверка 3: Переменные окружения" -ForegroundColor Yellow
$envPath = ".env"
if (Test-Path $envPath) {
    $content = Get-Content $envPath -Raw
    
    # Проверяем ключи
    $hasDeepSeek = $content -match "DEEPSEEK_API_KEY=sk-[a-zA-Z0-9]+"
    $hasAnthropic = $content -match "ANTHROPIC_API_KEY=sk-ant-[a-zA-Z0-9]+"
    
    Write-Host "   DEEPSEEK_API_KEY: $(if($hasDeepSeek){'✅ Найден'}else{'❌ Не найден или пустой'})" -ForegroundColor $(if($hasDeepSeek){'Green'}else{'Red'})
    Write-Host "   ANTHROPIC_API_KEY: $(if($hasAnthropic){'✅ Найден'}else{'⚠️ Не найден (опционально)'})" -ForegroundColor $(if($hasAnthropic){'Green'}else{'Yellow'})
} else {
    Write-Host "   ❌ Файл .env не найден!" -ForegroundColor Red
}
Write-Host ""

# Проверка 4: Circuit Breaker
Write-Host "▶ Проверка 4: Circuit Breaker" -ForegroundColor Yellow
Write-Host "   Если DeepSeek падал несколько раз, Circuit Breaker мог открыться" -ForegroundColor Gray
Write-Host "   Решение: перезапуск сервера (Ctrl+C → запустить снова)" -ForegroundColor White
Write-Host ""

# Итог
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                      РЕКОМЕНДАЦИИ                        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Если DEEPSEEK_API_KEY не найден:" -ForegroundColor Red
Write-Host "   1. Откройте файл .env" -ForegroundColor White
Write-Host "   2. Добавьте: DEEPSEEK_API_KEY=sk-ваш_ключ" -ForegroundColor White
Write-Host "   3. Перезапустите сервер" -ForegroundColor White
Write-Host ""
Write-Host "Если ключ есть но 503:" -ForegroundColor Yellow
Write-Host "   1. Проверьте логи в окне uvicorn (там будет точная ошибка)" -ForegroundColor White
Write-Host "   2. Возможно Circuit Breaker открыт - перезапустите сервер" -ForegroundColor White
Write-Host "   3. Проверьте баланс на DeepSeek: https://platform.deepseek.com" -ForegroundColor White
Write-Host ""
Write-Host "Для перезапуска:" -ForegroundColor Green
Write-Host "   Ctrl+C в окне uvicorn" -ForegroundColor Gray
Write-Host "   uvicorn src.api.main:app --reload" -ForegroundColor Gray
