@echo off
echo.
echo ============================================
echo    Перезапуск API сервера APE 2026
echo ============================================
echo.

cd /d "E:\ПРЕДСКАЗАТЕЛЬНАЯ АНАЛИТИКА"

echo Останавливаем старый процесс...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Убиваем процесс %%a
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo.
echo Запускаем API сервер...
echo URL: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo.

start "APE API Server" cmd /k "python -m uvicorn src.api.main:app --reload --port 8000"

echo.
echo ✅ API сервер запущен в новом окне!
echo Проверка через 3 секунды...

timeout /t 3 /nobreak >nul

curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ API работает!
    curl -s http://localhost:8000/health
) else (
    echo ⚠️  API еще запускается, подождите...
)

echo.
echo Нажмите любую клавишу для выхода...
pause >nul
