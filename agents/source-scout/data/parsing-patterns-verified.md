# Паттерны парсинга (проверенные 07.2026)

## fabricators.ru
- Пагинация: `?page=N` (N начинается с 0)
- Ссылки на компании: `/proizvoditel/<название>`
- Детали: телефон (`tel:`), сайт (внешняя ссылка), email (`mailto:`)
- ~624 кондитерских фабрик РФ

## productcenter.ru
- Пагинация: `/page-N` (НЕ `?page=N`!)
- Контейнер: `.cards` div, ссылки `/producers/<id>/<название>`
- Каталоги: кондитерские (427), мороженое (461), хлебобулочные (297)
- ~940 компаний

## Агропродмаш (icatalog.expocentr.ru)
- Все данные в HTML (2MB), requests с timeout=300
- Таблица: `table#fresh-table tbody tr`
- UUID: 2024=348532b3-e716-11ec-80cd-a0d3c1fab97f, 2025=b67ac0af-40d1-11ee-80ce-a0d3c1fab97f
- ~1875 компаний (2024+2025)

## Источники которые НЕ работают (07.2026)
- kazbrand.kz, madeinkz.kz, interfood.am, gulfoodistanbul.com — DNS не резолвится
- interfood.az, gulfood.com — timeout на requests
- uzfoodexpo.uz — 0 компаний (структура не найдена)
- belmarket.by — 404, products.by — 0 компаний

## Supabase ограничения
- `rpc/exec_sql` НЕ существует — таблицы создавать через Dashboard → SQL Editor
- REST API не поддерживает DDL
- `hermes_memory` таблица создана вручную через Dashboard
