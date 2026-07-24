# WorldFood Moscow 2025

## URL
https://exhibitors-itegroup.exhibitoronlinemanual.com/worldfood-moscow-2025/en/Exhibitor

## Статус: ✅ ПОЛНОСТЬЮ ДОСТУПЕН ЧЕРЕЗ REQUESTS

**Playwright НЕ нужен!** Данные приходят в статическом HTML через обычный requests.

## Структура HTML

Каждая компания — `<div class="card h-100">`:
```html
<div class="card h-100">
  <div class="card-img">
    <a href=".../ExbDetails/MjQ3NQ==">
      <img class="card-img-top" src="...">
    </a>
  </div>
  <div class="card-body">
    <h5 class="card-title">COMPANY NAME</h5>
    <h6> Pavilion 3 Hall 15<br/>
    <h6 class="card-subtitle">Stand No - B1033</h6>
    <p class="card-text">Russia</p>
  </div>
  <div class="card-footer">
    <a href=".../ExbDetails/MjQ3NQ==/product">Products</a>
  </div>
</div>
```

## Селекторы

- **Карточки**: `.card.h-100` (24 на страницу)
  - ⚠️ НЕ `.card` — он совпадёт с фильтрами!
- **Название**: `.card-title a` (text-transform: uppercase)
- **Страна**: `.card-text` (текст страны)
- **Павильон/Зал**: `.card-body h6` (первый)
- **Номер стенда**: `.card-subtitle`
- **Детальная страница**: `/ExbDetails/{base64_id}`
- **Продукты**: `/ExbDetails/{id}/product`

## Пагинация

- 34+ страниц, 24 компании на страницу
- Ожидаемый объём: ~800 компаний
- Класс пагинации: `.pagination`

## Парсинг детальной страницы

Каждая компания имеет детальную страницу по адресу:
`https://exhibitors-itegroup.exhibitoronlinemanual.com/worldfood-moscow-2025/en/ExbDetails/{id}`

Эти страницы содержат полную информацию: описание, продукты, контакты.

## Supabase source name

Используй `worldfood_moscow_2025` как source при загрузке.
