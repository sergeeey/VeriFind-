# Диагностика API
$API_URL = "http://localhost:8000"

Write-Host "=== ДИАГНОСТИКА API ===" -ForegroundColor Cyan

# 1. Проверка Circuit Breaker
Write-Host "`n1. Circuit Breaker Status" -ForegroundColor Yellow
try {
    # Проверим через метрики
    $metrics = Invoke-RestMethod -Uri "$API_URL/metrics" -TimeoutSec 5
    $cbState = $metrics -match "circuit_breaker_state"
    if ($cbState) {
        Write-Host "   Circuit Breaker: $cbState" -ForegroundColor Yellow
    } else {
        Write-Host "   Circuit Breaker: не найден в метриках" -ForegroundColor Gray
    }
} catch {
    Write-Host "   Не удалось получить метрики" -ForegroundColor Gray
}

# 2. Тест predictions (без LLM)
Write-Host "`n2. Тест /api/predictions/" -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "$API_URL/api/predictions/" -TimeoutSec 5
    Write-Host "   ✅ Работает! Найдено: $($resp.predictions.Count)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Тест track-record
Write-Host "`n3. Тест /api/predictions/track-record" -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "$API_URL/api/predictions/track-record" -TimeoutSec 5
    Write-Host "   ✅ Работает!" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Проверка ready
Write-Host "`n4. Readiness Check" -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "$API_URL/ready" -TimeoutSec 5
    Write-Host "   Ready: $($resp.ready)" -ForegroundColor $(if($resp.ready){'Green'}else{'Yellow'})
} catch {
    Write-Host "   ❌ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== РЕКОМЕНДАЦИИ ===" -ForegroundColor Cyan
Write-Host "Если Circuit Breaker OPEN:" -ForegroundColor Yellow
Write-Host "  Подождите 60 секунд (таймаут) и попробуйте снова" -ForegroundColor White
Write-Host "`nЕсли ошибки в analyze/query:" -ForegroundColor Yellow  
Write-Host "  Смотрите логи в окне uvicorn" -ForegroundColor White
Write-Host "`nДля перезапуска:" -ForegroundColor Yellow
Write-Host "  1. Ctrl+C в окне uvicorn" -ForegroundColor White
Write-Host "  2. uvicorn src.api.main:app --reload" -ForegroundColor White
