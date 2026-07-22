# Прогресс Слоя 2

## ✅ ЗАВЕРШЕНО
- 7 групп × 25 источников в sources_final.json
- 50 источников проверено через curl
- Оценки A/B/C/D проставлены
- Файл передан в Слой 3

## 27.06.2026 — Consilium аудит (5 моделей) + проверка источников
- Добавлены ключевые слова `agro`, `prod` в food relevance для новых CIS-каталогов
- Consilium рекомендовал добавить: agro24.ru, foodbazaar.kz, uzfood.uz, agroexpo.ge
- Баг группировки (все источники во все группы) — не критичо, возможно задумка
- Проверены 15 "непроверенных" источников через curl:
  ✅ wiki-prom.ru (200), mkond.ru (200), b2b-fmcg.ru (200), allfoods.market (200), modern-bakery.ru (200)
  ✅ expo.am/ArmProdExpo (200), expogeorgia.ge (200)
  ❌ DairyNews.ru (404 — мёртв), Candy Russia (000 — DNS), B2BMap Turkey (403)
- Обновлён SOURCES_CONSENSUS.json: 7 источников переведены в ✅ проверен, 2 обновлены URL, 2 помечены мёртвыми
- Итого: 105 рабочих (было 110), 2 перемещены в dead, 7 новых добавлены в проверенные

## СЛЕДУЮЩИЙ ШАГ
Ждать результатов парсинга для обновления источников

## 15.06.2026 — Полная проверка 400 источников
- ✅ 272 прямых (уникальных: 34)
- 🔄 Через Proton Proxy: 8 (DairyNews, NutsUnion, Агропродмаш, productcenter, Россельхознадзор, andoz.tj, Асконд, ЕГРЮЛ)
- 🔧 curl_cffi: 1 (Союзмолоко)
- 📦 Wayback Machine: 1 (DairyTech)
- ❌ DNS не резолвится: Expofood Georgia, Candy Russia, ArmProdExpo, РосХлебПром

## Методы парсинга (для Слоя 3)
- requests + BS4: 34 источника
- requests через Proton Proxy: 8 источников
- curl_cffi (TLS spoofing): 1 источник
- Wayback Machine (архив): 1 источник
- Playwright (JS-SPA): пока не требовался

## 15.06.2026 — Consilium нашёл альтернативы
Замены для 4 мёртвых сайтов (все проверены, HTTP 200):
- expofood-georgia.com → expoagro.ge, expogeorgia.ge
- candy-russia.ru → confex-expo.ru
- armprodexpo.am → expo.am/ru/exhibition/armprodekspo
- roshlebprom.ru → modern-bakery.ru, world-food.ru

## 19.06.2026
- Проверено 127 источников по 9 странам СНГ
- ✅ Рабочих: 94 (74%)
- ❌ Мёртвых: 33 (26%)
- Слито в единый sources_final.json
- Лидеры: Россия (43), Казахстан (12), Узбекистан (11), Армения (7)
- Слепые зоны: Таджикистан (2 рабочих), Туркменистан (4)

## 19.06.2026 (Consilium)
- Consilium (2 модели: Mistral + Groq) нашла 70 новых источников
- curl-проверка: 21 рабочий + 12 через прокси = 33 новых ✅
- Топ находки:
  • WorldFood Azerbaijan (worldfood.az) — выставка, A, relevance 10
  • Made in Tajikistan — B2B каталог, A, relevance 9
  • Kompass Tajikistan — B2B каталог, A, relevance 8
  • AZPROMO Food Sector — экспортёры Азербайджана, A, relevance 8
  • Azexport.az — каталог экспортёров, A, relevance 8
- ИТОГО после объединения: 98 рабочих + 12 через прокси = 110 полезных источников
