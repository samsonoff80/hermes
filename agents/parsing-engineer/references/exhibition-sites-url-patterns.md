# Exhibition Site URL Patterns

## Паттерны URL для выставочных сайтов

### Проблема
sources_final.json содержит только "главные" URL выставок (например `/en/exhibitors`), но на практике выставочные сайты часто имеют **отдельную страницу со списком экспонентов**, которая отличается от основной.

### Обнаруженные паттерны

| Сайт | "Главный" URL (пустой/навигация) | Реальный URL списка |
|------|----------------------------------|---------------------|
| interfood.az | `/en/exhibitors` (только навигация) | `/en/exhibitors-list` (48KB даных) |
| uzfoodexpo.uz | `/` (главная) | `/en/exhibitors-list` (76KB данных) |
| worldfood-istanbul.com | `/en/katilimci-listesi` | тот же (SPA, нужен browser) |

### Правило при парсинге выставок
1. Сначала проверь основной URL из sources_final.json
2. Если HTML содержит только навигацию (menu, header, footer без списка компаний) → ищи альтернативные пути:
   - `/exhibitors-list`
   - `/exhibitors-list`
   - `/participants`
   - `/participants-list`
   - `/catalog`
   - `/companies`
3. Ищи ссылки на странице — часто в меню есть пункт "Exhibitors List" с правильным URL
4. Проверяй `len(html) > 5000` — если меньше, скорее всего это не страница с данными

### Пример: InterFood Azerbaijan
```bash
# Главный URL — только навигация:
curl -s "https://interfood.az/en/exhibitors" | grep -c "company"  # 0

# Правильный URL — 48KB с данными:
curl -s "https://interfood.az/en/exhibitors-list" | wc -c  # 48457
```

### Питфолл: Не полагайся на sources_final.json URL слепо
sources_final.json собирается Слоем 2 (scout) и может содержать устаревшие или неполные URL. Всегда проверяй:
1. Реальный HTML-контент (не только HTTP status)
2. Наличие данных компаний на странице
3. Альтернативные пути в навигации сайта
