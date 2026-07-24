# Другие платформы выставок (не icatalog)

## ITegroup (exhibitors-itegroup.exhibitoronlinemanual.com)

**WorldFood Moscow** использует ITegroup для каталога:
- URL: `https://exhibitors-itegroup.exhibitoronlinemanual.com/worldfood-moscow-2025/ru/Exhibitor`
- Данные грузятся через JS/AJAX — curl не работает
- Требуется браузер или Playwright для парсинга

## Modern Bakery Moscow (modern-bakery.ru)

- URL каталога: `https://modern-bakery.ru/exhibitors_list`
- **403 Forbidden** — доступ запрещён без специальных заголовков
- Контакт: confex-expo.ru

## Агропродмаш (agroprodmash-expo.ru)

- URL каталога: `https://www.agroprodmash-expo.ru/ru/exhibition/exhibitors/`
- Кодировка: windows-1251
- Данные могут грузиться через AJAX
- 914 строк в HTML (но формат неизвестен)

## Конфекс (confex-expo.ru)

- Выставка кондитерского дела
- Минимальные данные на сайте
- Нет публичного каталога участников

## WorldFood Moscow (world-food.ru)

- Новости о каталоге: `https://world-food.ru/ru/media/news/2025/august/01/worldfood-moscow-2025/`
- Каталог на ITegroup платформе

## FoodExpo Qazaqstan

- Есть PDF-каталог: `onsite.iteca.kz/img/files/foodexpo/2025/FEQ'25_Exhibitor_List_ru.pdf`
- Можно парсить через PyMuPDF
