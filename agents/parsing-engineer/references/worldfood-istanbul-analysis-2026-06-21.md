# WorldFood Istanbul — Анализ структуры (21.06.2026)

## Платформа
ERA Soft LLC — та же платформа что используется для других выставок

## Питфолл: URL `/en/exhibitors` — это ЛЕНДИНГ
- `/en/exhibitors` — страница с информацией об участии для экспонентов (100KB HTML)
- НЕ содержит списка компаний!
- Содержит навигацию, новости, статистику выставки

## Реальный список экспонентов
- **URL**: `/en/exhibitor-list` (59KB HTML)
- **Структура**: `div.card.h-100.logo-slide` — карточки с логотипами
- **Название компании**: `alt` атрибут тега `<img>` внутри карточки
- **Ссылка**: `href` на профиль компании
- **Логотип**: `src` или `data-src` изображения

## Селекторы
```python
# Все карточки экспонентов
cards = soup.select('div.card.h-100.logo-slide')

for card in cards:
    img = card.select_one('img[alt]')
    name = img['alt'] if img else None
    link = card.select_one('a[href]')
    url = link['href'] if link else None
```

## Статус
- HTML получен через Playwright (59KB)
- Парсинг НЕ завершён — требуется извлечение данных из logo-slide карточек
- Ожидается ~1,500 компаний (по данным разведчика)

## Следующие шаги
1. Написать скрипт `scripts/parsers/worldfood_istanbul.py`
2. Использовать Playwright для рендеринга `/en/exhibitor-list`
3. Извлечь `alt` текст из `logo-slide` карточек
4. Сохранить в `data/worldfood_istanbul_2026.json`
5. Загрузить в Supabase
