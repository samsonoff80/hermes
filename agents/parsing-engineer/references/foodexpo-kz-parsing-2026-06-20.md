# FoodExpo Qazaqstan — парсинг 20.06.2026

## Источник
- **Сайт**: https://foodexpo.kz/
- **Список участников**: https://foodexpo.kz/ru/2025ru
- **iframe**: https://reg.iteca.kz/list/exponent/auth_s.aspx?ExhCode=FoodExpo%20Qazaqstan%202025
- **PDF каталог**: https://onsite.iteca.kz/img/files/foodexpo/2025/FEQ'25_Exhibitor_List_ru.pdf (0.1MB, 8 стр)

## Результаты
- **iframe HTML**: 808KB, 336 строк в таблице
- **Извлечено**: 311 компаний
- **Файл**: `data/foodexpo_kz_2025.json`
- **Поля**: name, country, stand, categories, source, source_year

## Структура данных
Данные в одной ячейке таблицы (не разнесены по колонкам):
```
<td>ACRYLICON CENTRAL ASIAКазахстан11-348</td>
```

## PDF каталог
- 8 страниц, ~300+ компаний
- Структура: КОМПАНИЯ -> СТРАНА -> ПРОДУКТЫ (многострочный формат)
- Сложность: строки компаний чередуются с организаторами региональных групп
- Статус: PDF скачан, требует до-парсинга

## Статус загрузки в Supabase
⏳ Требует загрузки (311 записей в data/foodexpo_kz_2025.json)
