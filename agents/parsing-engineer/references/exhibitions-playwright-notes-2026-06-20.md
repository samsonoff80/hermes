# Парсинг выставок через Playwright HF — заметки 20.06.2026

## ⚠️ УСТАРЕЛО — Playwright HF НЕ работает (обновлено 18.06.2026)

**Playwright HF возвращает HTTP 206 для всех внешних сайтов.** Не используй его для парсинга.

Актуальные данные по каждому источнику см. `references/exhibitions-reality-check-2026-06-18.md`.

## Формат ответа Playwright HF (устарело)

Playwright HF (`https://playwright-browser.onrender.com/fetch?url=`) якобы возвращает HTML внутри JSON:

```python
r = requests.get(f"{PLAYWRIGHT_HF}{url}", timeout=45)
data = r.json()
html = data.get('html', data.get('content', ''))
```

**Но на практике возвращает 206 и HTML страницы Hugging Face.**

## Tilda-сайты — проблема

Сайты на Tilda (modern-bakery.ru и др.) загружают данные через API после рендеринга.
Даже если бы Playwright HF работал, он бы вернул HTML-каркас без данных компаний.

Признаки Tilda:
- В HTML есть `tildacdn.com` в ресурсах
- Селекторы `.t-name`, `.t-col`, `.t-item` содержат навигацию, а не данные
- Нет данных компаний в HTML

## Универсальный парсер выставок (устарел)

Скрипт `scripts/parsers/exhibitions_playwright.py` создан, но **не работает** из-за проблем с Playwright HF.
Требует переписывания для прямых запросов.

## Нормализация стран (country_map)

```python
country_map = {
    'Россия': ('RU', True), 'Russian Federation': ('RU', True),
    'Казахстан': ('KZ', True), 'Kazakhstan': ('KZ', True),
    'Узбекистан': ('UZ', True), 'Uzbekistan': ('UZ', True),
    'Азербайджан': ('AZ', True), 'Azerbaijan': ('AZ', True),
    'Армения': ('AM', True), 'Armenia': ('AM', True),
    'Грузия': ('GE', False), 'Georgia': ('GE', False),
    'Кыргызстан': ('KG', True), 'Kyrgyzstan': ('KG', True),
    'Таджикистан': ('TJ', True), 'Tajikistan': ('TJ', True),
    'Турция': ('TR', False), 'Turkey': ('TR', False),
    'ОАЭ': ('AE', False), 'UAE': ('AE', False),
    'Беларусь': ('BY', True), 'Belarus': ('BY', True),
    'Молдова': ('MD', True), 'Moldova': ('MD', True),
    'Туркменистан': ('TM', True), 'Turkmenistan': ('TM', True),
}
```

## Известные URL страниц участников выставок

| Выставка | URL списка участников |
|----------|----------------------|
| WorldFood Moscow | `https://exhibitors-itegroup.exhibitoronlinemanual.com/worldfood-moscow-2025/en/Exhibitor` |
| WorldFood Istanbul | `https://worldfood-istanbul.com/en/katilimci-listesi` |
| Gulfood Dubai | `https://exhibitors.gulfood.com/gulfood-2026/Sectorlist/world-food` |
| Modern Bakery Moscow | `https://www.modern-bakery.ru/` (Tilda) |
| FoodExpo Qazaqstan | `https://foodexpo.kz/` |
| InterFood Azerbaijan | `https://interfood.az/en/exhibitors` |
| UzFood | `https://uzfoodexpo.uz/en/exhibitors-list` |
| Bakery Expo KZ | `https://all-events.ru/events/bakery-expo-kazakhstan-2025` |
