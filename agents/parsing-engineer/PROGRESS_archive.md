=== PROGRESS.merged ===
--- ИЗ skills/layer3-parser (106 строк) ---
# Прогресс Слоя 3

## ✅ СДЕЛАНО (обновлено 22.06.2026)
- Продэкспо 2022-2026: 52,106 записей (prodexpo_2022..2026, prodexpo_full, prodexpo_icatalog_2024..2026)
- WorldFood Moscow 2025: 10,360 записей (AJAX API)
- WorldFood Istanbul: 478 записей (ERA Soft DataTables API)
- WorldFood PDF 2024-2025: 3,860 записей (PDF каталоги, загружено 22.06.2026)
- Gulfood Dubai: 264 записи (частично, AJAX POST с cookies)
- FoodExpo Qazaqstan 2025: 311 записей (iteca.kz iframe)
- Flagma.kz: 548 записей
- Fabricators.ru: 30 записей
- Асконд: 41 запись
- InterFood Azerbaijan: 14 записей
- Candy Factory: 24 записи
- Foodmarkets.ru: 11 записей
- Iteka.ru: 21 запись
- GeorgiaYP: 12 записей (загружено 22.06.2026)
- Web search (TJ, KG, UZ, AZ, AM, GE): 33 записи
- Tajtrade: 1, Trade.com.tm: 81

## 📊 СТАТУС НА 22.06.2026
- **Supabase raw_parsed_data: 58,823 записей, 31 источник**
- Все основные источники из sources_final.json обработаны

## 🔄 В ПРОЦЕССЕ
- Gulfood Dubai: 264 из ~3,255 (требует Playwright cookies + AJAX pagination)

## 27.06.2026 — Consilium аудит (5 моделей) + очистка дубликатов
- Удалены дубликаты prodexpo (3 версии: v1, v2, v3 → оставлен pdf_clean), gulfood (2 версии → оставлен v2), ascond, worldfood
- Consilium рекомендовал оставить по 1 финальной версии на источник
- Рекомендовано добавить: AgroFarm, FoodIngredient CIS, KazAgro, UzAgroExpo
- Проверено: нет импортов удалённых модулей в других скриптах
- Удалена parse_flagma_kz() из cis_catalogs.py (дублирует flagma_kz.py)
- Удалён universal_proxy.py (дублирует fabricators, candy-factory, factories.kz, flagma)
- Удалён exhibitions_playwright.py (дублирует gulfood, worldfood_istanbul, worldfood_moscow, agroprodmash)
- Удалена parse_productcenter() из parse_catalogs.py (дублирует productcenter.py)
- Итого убрано 9 файлов/функций, сокращено ~1200 строк кода

## ⏳ ОЖИДАЕТ / НЕДОСТУПНО
- Modern Bakery Moscow — Tilda SPA, требует browser tool
- UzFood — jQuery DataTables SPA, требует browser tool
- DairyTech — DEAD (DNS не резолвится)
- Агропродмаш — 404
- Bakery Expo Kazakhstan — календарь, не каталог
- productcenter.ru — общий каталог, не пищевой

## ✅ ПРОВЕРЕНЫ И РАБОТАЮТ (28.06.2026)
- wiki-prom.ru (200), mkond.ru (200), b2b-fmcg.ru (200), allfoods.market (200), modern-bakery.ru (200)
- expo.am/ArmProdExpo (200), expogeorgia.ge (200)
- **parse_catalogs.py** — универсальный парсер: Продэкспо 2025 = 1799 записей за 1 сек ✅
- **consilium_brain.py** — foodsuppliers.ru/sitemap/list → 192 записи, профиль создан ✅
- **auto_scout_v2.py** — 9 новых источников из web_search добавлены в source_profiles ✅

## ❌ МЁРТВЫЕ САЙТЫ (обновлено 28.06.2026)
- dairytechexpo.ru, agroprodmash-expo.ru/catalog
- flagma.uz (reCAPTCHA), world-food.ru (таймаут)
- DairyNews.ru (404), candy-russia.ru (DNS fail)
- **bozor.tj** — "Site under construction", 0 компаний → УДАЛЁН из parse_catalogs.py
- **inform.kg** — не бизнес-каталог (гороскоп/погода) → УДАЛЁН из parse_catalogs.py
- **georgiayp.com** — 404 на food-industry → УДАЛЁН из parse_catalogs.py
- **madeinuzbekistan.ru** — Tilda SPA, требует Playwright → УДАЛЁН из parse_catalogs.py
- **n4.biz** — нет ссылок / SPA → УДАЛЁН из parse_catalogs.py
- **parse_catalogs.py** — УДАЛЁН целиком (все 5 источников мертвы)

## 28.06.2026 — Сквозной тест всех слоёв
- Слой 1: ✅ работает (3/5 моделей, группы корректны)
- Слой 2: ✅ 105 рабочих + 13 прокси + 56 мёртвых = 174
- Слой 3: ❌ 3/5 парсеров в parse_catalogs.py мертвы → файл удалён
- Слой 4: ✅ работает (reject rate 15.5%, grey zone 45.5%)
- Итого удалено: 10 файлов + 2 функции, ~1300 строк кода с 27.06.2026

## 28.06.2026 — Consilium-Driven Architecture (НОВАЯ АРХИТЕКТУРА)

### Что изменилось
- **Удалены 15 индивидуальных парсеров** (agroprodmash, ascond, candy_factory, cis_catalogs, fabricators, flagma_kz, foodsuppliers, gulfood, prodexpo, prodexpo_pdf_clean, prodexpo_profile, productcenter, ru_catalogs, worldfood_istanbul, worldfood_moscow)
- **Создан универсальный parse_catalogs.py** — читает конфиг из Supabase source_profiles и парсит по нему
- **Создан consilium_brain.py** — анализирует HTML через 5 моделей, генерирует конфиг парсинга
- **Создан auto_scout_v2.py** — автоматический поиск новых источников через web_search
- **Бэкап**: ~/.hermes/backups/parsers-20260628/

### Архитектура
```
Consilium Brain (5 моделей) → source_profiles (Supabase) → parse_catalogs.py → raw_parsed_data
```

### Новые профили в source_profiles (9 найдено через auto_scout)
- wiki-prom.ru — Кондитерские фабрики России
- yellowpages.uz — Кондитерские фабрики Узбекистана
- goldenpages.uz — Кондитерские фабрики Ташкента
- areg.am — Кондитерские изделия Армении
- kataloq.gomap.az — Кондитерские Азербайджана
- productcenter.ru — Молочные заводы России
- xn--80aegj1b5e.xn--p1ai — Молочные заводы России (альт.)
- factories.kz — Молочная промышленность Казахстана
- manufacturers.ru — Заводы Таджикистана

### Файлы
- `scripts/parsers/parse_catalogs.py` — универсальный парсер (table/card/spa, pagination, detail pages)
- `scripts/consilium_brain.py` — мозг: HTML → Consilium → конфиг
- `scripts/auto_scout_v2.py` — поиск новых источников через web_search

### Статистика
- Парсеров: 15 → 2 (parse_catalogs.py + parse_pdf.py)
- Строк кода: ~3000 → ~500 (−83%)
- Новых источников найдено: 9
- Все парsers компилируются ✅
