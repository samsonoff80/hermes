# Парсинг выставок — справочник платформ

## ITE Group (WorldFood Moscow, Istanbul и др.)

**Платформа**: `exhibitors-itegroup.exhibitoronlinemanual.com`
**Метод**: Python Playwright (JS-SPA, requests не работает)

### Структура карточки
```html
<div class="card">
  <div class="card-img">...</div>
  <div class="card-body">
    <h5 class="card-title"><a>НАЗВАНИЕ</a></h5>
    <h6>Павильон X Зал Y</h6>
    <h6 class="card-subtitle">Стенд № - B1033</h6>
    <p class="card-text">СТРАНА</p>  <!-- ВОТ ТУТ СТРАНА! -->
  </div>
</div>
```

### Селекторы (подтверждено 06.2026)
- Название: `.card-title a` / `h5.card-title a`
- Страна: `.card-text` (НЕ `.country`!)
- Стенд: `.card-subtitle`
- Павильон/зал: `h6` (без класса)

### Пагинация
**ВСЕ карточки загружаются сразу на одну страницу!** НЕ листать по `?page=N`.
Нужен скролл вниз для lazy loading:
```python
for i in range(10):
    page.evaluate("window.scrollBy(0, 3000)")
    page.wait_for_timeout(2000)
```

### Примеры URL
- WorldFood Moscow 2025: `https://exhibitors-itegroup.exhibitoronlinemanual.com/worldfood-moscow-2025/ru/Exhibitor`
- WorldFood Istanbul: аналогично, но каталог может быть недоступен до выставки

## ITECA (Казахстан, Узбекистан, Армения)

**Статус**: ❌ HTTP 500 на все выставки (06.2026) — сервер сломан

**API (было)**: `https://reg.iteca.kz/list/exponent/auth_s.aspx?ExhCode=<название>`

**Пищевые выставки ITECA:**
- `FoodExpo Qazaqstan 2023/2024/2025` — ~300 компаний/год
- `InterFood Astana 2023/2024/2025` — ~65 компаний/год
- `Horex Qazaqstan 2023/2024/2025` — ~35 компаний/год (HoReCa)
- `Agroworld Qazaqstan 2023/2024/2025` — агро

## Агропродмаш (Россия)

**URL**: `https://icatalog.expocentr.ru/ru/exhibitions/<uuid>/list`
**Метод**: requests напрямую (timeout=300), НЕ Playwright

### UUID по годам
| Год | UUID | Компаний |
|-----|------|----------|
| 2023 | `ac7d68bf-c129-11eb-80cc-a0d3c1fab97f` | 844 |
| 2024 | `348532b3-e716-11ec-80cd-a0d3c1fab97f` | 920 |
| 2025 | `b67ac0af-40d1-11ee-80ce-a0d3c1fab97f` | 856 |

### Структура
- bootstrap-table, все данные в HTML (2MB на страницу)
- Клиентская пагинация (все данные уже в HTML)
- Колонки: name, country, pavilion, stand, rubrics
- Селектор: `table#fresh-table tbody tr`

## UzFood / AgroWorld (Узбекистан)

**URL**: `https://uzprint.uz/en/exhibitors-list` (зеркало uzfoodexpo.uz)
**Метод**: Python Playwright
**Кол-во**: ~10 компаний (реально мало!)
**Проблема**: Execution context destroyed при смене года

## Продэкспо (Россия)

**Источник**: PDF-каталог (Post Show Report на prod-expo.ru)
**Секции**: 10 (Кондитерские+хлебопекарная), 22 (ЗОЖ), 25 (Халяль), 29 (Мороженое)

## WorldFood Istanbul

**Статус**: Выставка 15-18 декабря 2026, каталога пока нет
**Post Show Report**: `/en/post-show-report` (PDF динамический, нужен Playwright)
