#!/usr/bin/env python3
"""
Полная диагностика APE-2026
Запускать: python scripts/full_diagnose.py
"""

import sys
import os
import subprocess
import json

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def check_color(text, success=True):
    """Цветной вывод"""
    if success:
        return f"✅ {text}"
    else:
        return f"❌ {text}"

def main():
    print("=" * 60)
    print("APE-2026: ПОЛНАЯ ДИАГНОСТИКА")
    print("=" * 60)
    print()
    
    errors = []
    warnings = []
    
    # 1. Проверка .env
    print("1. Проверка .env файла...")
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_content = f.read()
        
        # Проверяем DEEPSEEK_API_KEY
        if 'DEEPSEEK_API_KEY=sk-' in env_content:
            print(f"   {check_color('DEEPSEEK_API_KEY найден', True)}")
        elif 'DEEPSEEK_API_KEY=' in env_content:
            print(f"   {check_color('DEEPSEEK_API_KEY пустой или неверный', False)}")
            errors.append("DEEPSEEK_API_KEY не настроен правильно")
        else:
            print(f"   {check_color('DEEPSEEK_API_KEY не найден', False)}")
            errors.append("DEEPSEEK_API_KEY отсутствует в .env")
    else:
        print(f"   {check_color('.env файл не найден!', False)}")
        errors.append("Файл .env отсутствует")
    
    print()
    
    # 2. Проверка кода LangGraphOrchestrator
    print("2. Проверка кода...")
    try:
        from src.orchestration.langgraph_orchestrator import LangGraphOrchestrator
        import inspect
        sig = inspect.signature(LangGraphOrchestrator.__init__)
        params = list(sig.parameters.keys())
        
        if 'claude_api_key' in params:
            print(f"   {check_color('LangGraphOrchestrator принимает claude_api_key', True)}")
        else:
            print(f"   {check_color('LangGraphOrchestrator: параметры - ' + str(params), False)}")
            
        if 'llm_provider' in params:
            print(f"   {check_color('Поддержка llm_provider', True)}")
        else:
            print(f"   {check_color('llm_provider не поддерживается', False)}")
            
    except Exception as e:
        print(f"   {check_color(f'Ошибка импорта: {e}', False)}")
        errors.append(f"Ошибка импорта LangGraphOrchestrator: {e}")
    
    print()
    
    # 3. Проверка API endpoints
    print("3. Проверка API...")
    import requests
    
    try:
        # Health check
        r = requests.get('http://localhost:8000/health', timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"   {check_color(f'Health: {data.get(\"status\", \"unknown\")}', True)}")
        else:
            print(f"   {check_color(f'Health: HTTP {r.status_code}', False)}")
            errors.append(f"Health endpoint вернул {r.status_code}")
    except Exception as e:
        print(f"   {check_color(f'Health: {e}', False)}")
        errors.append(f"API не отвечает: {e}")
    
    # Проверка /api/analyze
    print("   Проверка POST /api/analyze...")
    try:
        r = requests.post(
            'http://localhost:8000/api/analyze',
            json={"query": "test"},
            timeout=10
        )
        if r.status_code == 200:
            print(f"   {check_color('Analyze: OK (200)', True)}")
            data = r.json()
            if data.get('_provider') == 'deepseek':
                print(f"   {check_color('DeepSeek работает!', True)}")
            elif data.get('_provider') == 'mock':
                print(f"   {check_color('Работает mock (не DeepSeek)', False)}")
                warnings.append("Используется mock вместо DeepSeek")
        elif r.status_code == 503:
            print(f"   {check_color('Analyze: 503 Service Unavailable', False)}")
            errors.append("POST /api/analyze возвращает 503")
        else:
            print(f"   {check_color(f'Analyze: HTTP {r.status_code}', False)}")
            errors.append(f"Analyze вернул {r.status_code}")
    except Exception as e:
        print(f"   {check_color(f'Analyze: {e}', False)}")
        errors.append(f"Analyze не работает: {e}")
    
    print()
    
    # 4. Проверка процесса uvicorn
    print("4. Проверка процессов...")
    try:
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        if 'python.exe' in result.stdout or 'uvicorn' in result.stdout:
            print(f"   {check_color('Python/uvicorn процесс найден', True)}")
        else:
            print(f"   {check_color('Python/uvicorn не найден в процессах', False)}")
            warnings.append("API может быть не запущен")
    except:
        pass
    
    print()
    print("=" * 60)
    print("РЕЗУЛЬТАТ ДИАГНОСТИКИ")
    print("=" * 60)
    
    if errors:
        print(f"\n❌ ОШИБКИ ({len(errors)}):")
        for e in errors:
            print(f"   - {e}")
    
    if warnings:
        print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    
    if not errors and not warnings:
        print("\n✅ ВСЁ РАБОТАЕТ!")
        return 0
    elif not errors:
        print("\n⚠️  Работает с предупреждениями")
        return 0
    else:
        print("\n❌ ЕСТЬ КРИТИЧЕСКИЕ ОШИБКИ!")
        print("\n🔧 РЕКОМЕНДАЦИИ:")
        
        if any("DEEPSEEK_API_KEY" in e for e in errors):
            print("   1. Добавьте DEEPSEEK_API_KEY в .env файл")
            print("      DEEPSEEK_API_KEY=sk-ваш_ключ")
        
        if any("503" in e for e in errors):
            print("   2. Перезапустите API:")
            print("      Ctrl+C в окне uvicorn")
            print("      uvicorn src.api.main:app --reload")
        
        if any("LangGraphOrchestrator" in e for e in errors):
            print("   3. Проверьте параметры LangGraphOrchestrator")
            print("      Должно быть: claude_api_key=..., llm_provider='deepseek'")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
