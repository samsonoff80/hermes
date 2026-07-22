# ИНЖЕНЕР — ПРАВИЛА (23.07.2026)

## ПЕРЕД ПРАВКОЙ
1. chmod 600 config.yaml
2. Бэкап: cp файл ~/backup_$(date +%Y%m%d_%H%M)/

## ПОСЛЕ ПРАВКИ
1. python3 -m py_compile файл
2. Выполнить ПОЛНЫЙ ПЕРЕЗАПУСК:
fuser -k 8765/tcp 2>/dev/null; pkill -9 -f "hermes_cli.main|hermes-agent gateway|consilium_server" 2>/dev/null; sleep 2; rm -f ~/.hermes/state.db* ~/.hermes/auth.json ~/.hermes/models_dev_cache.json ~/.hermes/hermes-agent/models_dev_cache.json 2>/dev/null; rm -rf ~/.hermes/sessions/* 2>/dev/null; rm -f ~/.hermes/skills/consilium/rate_limits.db ~/.hermes/skills/consilium/fallback_chain.json ~/.hermes/skills/consilium/provider_state.json 2>/dev/null; find ~/.hermes -name "__pycache__" -exec rm -rf {} + 2>/dev/null; systemctl --user restart hermes-consilium && sleep 2 && systemctl --user restart hermes-agent && sleep 2 && echo "Процессов: $(ps aux | grep '[h]ermes' | grep -v grep | wc -l)" && curl -s http://127.0.0.1:8765/health
3. chmod 444 config.yaml

## НЕ ТРОГАТЬ
- .env файлы (ключи)
- provider_state.json (сбрасывать только при проблемах)
- config.yaml без chmod 600

## ИЗВЕСТНЫЕ БАГИ
- update_all.py перезаписывает github.py → azureml://
- Hermes v0.19: 200 OK → "Provider failed" (основная проблема)
- COOLDOWN_STEPS: макс 21600с (6ч) → снизить
- Telegram токен скомпрометирован → сменить
