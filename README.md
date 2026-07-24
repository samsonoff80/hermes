# Consilium v7.2 — LLM прокси для Hermes Agent v0.19

## Железо
Khadas VIM4 ARM64 8GB RAM, Ubuntu 24.04

## Архитектура
Telegram → Hermes Agent v0.19 → Consilium (:8765) → 12 провайдеров

## Возможности
- System Prompt Filter — денилист блоков Hermes (~500 символов)
- Task Router — chat/code/search/analysis
- Fallback Manager — DPS-приоритет (success_rate + latency)
- Rate Limiter — per-key RPD/TPD, cooldown 90с→6ч
- Circuit Breaker — 5 ошибок → 60с
- Provider Statistics — адаптивный приоритет
- Request ID — трассировка запросов
- Dashboard — :8765/
- Alerting — Telegram уведомления
- Model Registry — автообновление (update_all.py)

## Провайдеры (24.07.2026)
| # | Провайдер | Модели |
|---|-----------|--------|
| 1 | groq (3 ключа) | llama-3.1-8b-instant, llama-3.3-70b-versatile |
| 2 | github (3 ключа) | gpt-4o-mini, gpt-4o |
| 3 | cloudflare (3 ключа) | gpt-oss-120b, llama-3.2-3b-instruct |
| 4 | mistral (1 ключ) | codestral, mistral-small, magistral-small |
| 5 | sambanova (2 ключа) | DeepSeek-V3.1, Meta-Llama-3.3-70B-Instruct |
| 6 | openrouter (3 ключа) | 12 моделей :free |

## Ошибки
| Код | Действие |
|-----|----------|
| 401 | cooldown 1ч |
| 402/403 | disabled |
| 413 | следующий |
| 429 | cooldown 90с→6ч |

## Команды
systemctl --user restart hermes-consilium && systemctl --user restart hermes-agent
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/usage/today
cd ~/.hermes/skills/consilium && python3 update_all.py

## Статус (24.07.2026)
12 правок применено. Требуется сброс rate_limits.db.
