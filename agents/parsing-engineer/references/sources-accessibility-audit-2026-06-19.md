# Sources Accessibility Audit — 19.06.2026

## Проблема
sources_final.json помечает 161 источник как "✅ прямой доступ (200)" или "✅ через прокси (200)", но реальная проверка показывает что многие из них — SPA с пустым HTML или требуют browser tool.

## Аудит 16 новых (не в Supabase) источников

| Источник | HTTP | Размер | Реальная структура | Парсится напрямую? |
|----------|------|--------|-------------------|-------------------|
| openinfo.uz | 200 | 261KB | Next.js SPA, без `__NEXT_DATA__`, API не найден в HTML | ❌ Нужен browser |
| orginfo.uz | 200 | 47KB | Статический HTML, данные в DOM | ✅ requests+BS4 |
| stat.gov.kz | 200 | 40KB | Вероятно редирект/защита (малый размер для реестра) | ⚠️ Проверить |
| e-ondiris.gov.kz | 200 | 915B | Редирект или защита | ❌ |
| napr.gov.ge | 200 | 840B | Редирект или защита | ❌ |
| taxes.gov.az | 302 | 352B | Редирект | ⚠️ Следовать редиректу |
| e-register.am | 301 | 1.4KB | Редирект | ⚠️ Следовать редиректу |
| pb.nalog.ru | 200 | 160KB | SPA, данные через API | ⚠️ Нужен анализ API |
| interfood.az | 200 | 48KB | Статический HTML со списком экспонентов | ✅ requests+BS4 |
| uzfoodexpo.uz | 200 | 77KB | Статический HTML | ✅ requests+BS4 |
| all-events.ru | 301 | 342B | Редирект | ⚠️ |
| foodexpo.kz | 301 | 0B | Недоступен | ❌ |
| gulfood.com | 200 | 244KB | AJAX SPA (skill doc подтверждает) | ❌ Нужен browser |
| modern-bakery.ru | 200 | 709KB | Tilda SPA, данные не в HTML | ❌ Нужен browser |
| opensanctions.org | 200 | 96KB | Bulk JSON dataset | ✅ Прямой JSON |

## Паттерн: Next.js SPA без __NEXT_DATA__
- **openinfo.uz** — Next.js app, данные загружаются через клиентский JS
- HTML содержит только `<script>` теги с chunks
- API endpoint не виден в HTML — нужно анализировать `_next/static/chunks/` или использовать browser tool
- **Решение**: искать `/_next/data/` путь или использовать browser tool

## Паттерн: Малый HTML (<2KB) при HTTP 200
- e-ondiris.gov.kz (915B), napr.gov.ge (840B), taxes.gov.az (352B after redirect)
- Вероятно: редирект через JS, защита, или пустой ответ
- **Решение**: проверять `Content-Length` и содержимое; если <2KB — помечать как подозрительный

## Обновление статусов в sources_final.json
Статусы "✅ прямой доступ (200)" означают только что HTTP 200, а не что данные доступны.
Нужно различать:
- `200 + данные в HTML` → реально парсится
- `200 + SPA/AJAX` → нужен browser tool
- `200 + малый body` → подозрительно, проверить вручную
- `301/302` → следовать редиректу
