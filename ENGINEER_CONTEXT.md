# ИНЖЕНЕР — ПРАВИЛА (23.07.2026 22:35)

## ПЕРЕД ПРАВКОЙ
1. chmod 600 config.yaml
2. Бэкап: mkdir -p ~/backup_$(date +%Y%m%d_%H%M) && cp файл ~/backup_$(date +%Y%m%d_%H%M)/

## ПОСЛЕ ПРАВКИ
1. python3 -m py_compile файл
2. ПОЛНЫЙ ПЕРЕЗАПУСК:
fuser -k 8765/tcp 2>/dev/null
pkill -9 -f "hermes_cli.main|hermes-agent gateway|consilium_server" 2>/dev/null
sleep 2
rm -f ~/.hermes/state.db* ~/.hermes/auth.json ~/.hermes/models_dev_cache.json ~/.hermes/hermes-agent/models_dev_cache.json 2>/dev/null
rm -rf ~/.hermes/sessions/* 2>/dev/null
rm -f ~/.hermes/skills/consilium/rate_limits.db ~/.hermes/skills/consilium/fallback_chain.json ~/.hermes/skills/consilium/provider_state.json 2>/dev/null
find ~/.hermes -name "__pycache__" -exec rm -rf {} + 2>/dev/null
systemctl --user restart hermes-consilium && sleep 2
systemctl --user restart hermes-agent && sleep 2
ps aux | grep "[h]ermes" | grep -v grep
curl -s http://127.0.0.1:8765/health
3. chmod 444 config.yaml

## НЕ ТРОГАТЬ
- .env файлы (ключи)
- config.yaml без chmod 600
- provider_state.json (сбрасывать только при проблемах)

## СТРУКТУРА ПРОЕКТА
consilium/ (5 файлов):
  consilium_server.py — System Prompt Filter + Task Router + Usage Logger
  model_registry.py — фильтр моделей (128K+, исключает embedding/audio)
  provider_stats.py — успешность провайдеров (компактный)
  dashboard.py — веб-интерфейс
  alerting.py — уведомления в Telegram (отключён)

## HERMES v0.19 (ЧТО ИСПОЛЬЗУЕМ)
- credential_pool_strategies: round_robin (groq, cloudflare, github, mistral, sambanova)
- fallback_providers: groq → cloudflare → github → mistral → sambanova → aihorde → openrouter
- custom_providers: groq, cloudflare, github, mistral, sambanova, aihorde
- Встроенные: openrouter, huggingface, deepseek
- 18 ключей в auth.json
- api_mode: chat_completions

## GITHUB
main: v8.0 (облегчённый)
v7.2: резервная копия

## ИЗВЕСТНЫЕ ПРОБЛЕМЫ
- Hermes v0.19: 200 OK → "Provider failed" (требуется отладка)
- Telegram бот токен скомпрометирован → сменить
