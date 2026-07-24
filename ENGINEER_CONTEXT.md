# ИНЖЕНЕР — ПРАВИЛА РАБОТЫ С КОДОМ (24.07.2026)

## ПЕРЕД ПРАВКОЙ
- chmod 600 для config.yaml
- Бэкап: cp file.py file.py.bak

## ПОСЛЕ ПРАВКИ
1. python3 -m py_compile file.py
2. Очистить кэш + перезапустить:
   pkill -9 -f "consilium_server" && sleep 1
   rm -f rate_limits.db
   systemctl --user restart hermes-consilium
3. Проверить: curl -s http://127.0.0.1:8765/health
4. chmod 444 config.yaml

## ПРОВЕРКА ПРОВАЙДЕРОВ
cd ~/.hermes/skills/consilium
python3 -c "
import requests, time
env = {}
with open('.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k,v = line.strip().split('=',1)
            env[k] = v
# Проверить groq
key = env.get('GROQ_API_KEY_1','')
r = requests.post('https://api.groq.com/openai/v1/chat/completions',
    headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},
    json={'model':'llama-3.3-70b-versatile','messages':[{'role':'user','content':'test'}],'max_tokens':5})
print(f'groq: {r.status_code}')
"

## СБРОС ЛИМИТОВ
rm -f ~/.hermes/skills/consilium/rate_limits.db
systemctl --user restart hermes-consilium

## АРХИТЕКТУРА
- consilium_server.py — точка входа (FastAPI)
- fallback_manager.py — цепочки провайдеров
- rate_limiter.py — per-key RPD/TPD
- circuit_breaker.py — защита от падений
- provider_stats.py — DPS-статистика
- model_registry.py — каталог моделей
- providers/*.py — 12 модульных провайдеров
- update_all.py — автообновление моделей

## ИЗВЕСТНЫЕ БАГИ
- 401/402/403 — проблема ключей, не кода
- 413 — system prompt слишком большой (денилист это чинит)
- openrouter 429 — дневной лимит 50 запросов
