# Парсинг ITE Group выставок (WorldFood и др.)

## Платформа

ITE Group использует `exhibitors-itegroup.exhibitoronlinemanual.com`.
JS-SPA — **requests не работает**, нужен Playwright.

## WorldFood Moscow 2025

**URL:** `https://exhibitors-itegroup.exhibitoronlinemanual.com/worldfood-moscow-2025/ru/Exhibitor`

### Структура карточки
```html
<div class="card">
  <div class="card-body">
    <h5 class="card-title"><a href="...">НАЗВАНИЕ</a></h5>
    <h6>Павильон 3 Зал 15</h6>
    <h6 class="card-subtitle">Стенд № - B1033</h6>
    <p class="card-text">Россия</p>
  </div>
</div>
```

### Селекторы
- **Название**: `.card-title a` или `h5.card-title a`
- **Страна**: `.card-text` (p-элемент, НЕ `.country`!)
- **Стенд**: `.card-subtitle` (h6)

### Пагинация

**НЕ через URL параметры!** `?page=N` не работает.

Кнопки используют `onclick="searchFilter(N)"`:
```html
<a class="page-link" onclick="searchFilter(24)">2</a>
<a class="page-link" onclick="searchFilter(48)">3</a>
<a class="page-link">»</a>
```

**Алгоритм:**
```python
for page_num in range(1, max_pages):
    # Парсим карточки...
    nxt = page_num + 1
    btn = page.query_selector(f'a.page-link >> text="{nxt}"')
    if not btn:
        btn = page.query_selector('a.page-link >> text="»"')
    if btn:
        btn.click()
        page.wait_for_timeout(3000)
        page.wait_for_selector('.card', timeout=10000)
    else:
        break
```

### Скролл НЕ РАБОТАЕТ
Сайт использует пагинацию, а не infinite scroll.

### Количество данных
- WorldFood Moscow 2025: ~335 компаний (14 страниц по 24)
- Страны: Россия ~195, Китай ~45, Индия ~22, Кыргызстан ~19

## Другие выставки ITE Group

Тот же паттерн: `exhibitors-itegroup.exhibitoronlinemanual.com/<exhibition>/ru/Exhibitor`

| Выставка | Статус |
|----------|--------|
| WorldFood Moscow 2025 | ✅ Спарсено (335) |
| WorldFood Istanbul | ❌ Каталог не опубликован (выставка 15-18 дек 2026) |
