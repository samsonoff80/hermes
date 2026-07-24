# Полный список ресурсов для парсинга B2B-клиентов (СНГ + Турция + ОАЭ, 2024-2026)

## Часть 1: ВЫСТАВКИ (с онлайн-каталогами)

### 🇷🇺 РОССИЯ

| Выставка | Период | URL каталога | Платформа | Метод парсинга |
|---|---|---|---|---|
| Продэкспо | Февраль, Москва | prod-expo.ru/ru/participants/ | Собственный сайт | ⚠️ PDF не публикуется, нужен парсинг HTML |
| Агропродмаш | Октябрь, Москва | icatalog.expocentr.ru/ru/exhibitions/<uuid>/list | Expocentr (bootstrap-table) | ✅ requests + BeautifulSoup |
| WorldFood Moscow | Сентябрь, Москва | exhibitors-itegroup.exhibitoronlinemanual.com/worldfood-moscow-<year>/ru/Exhibitor | ITE Group (JS-SPA) | ✅ Playwright |
| ПИР Экспо | Сентябрь, Москва | pirexpo.ru/ru/exhibitors/ | Собственный | ⚠️ Playwright |
| Petfood & Vetfood Expo | Март, Москва | icatalog.expocentr.ru | Expocentr | ✅ requests |
| Milk & Dairy | Июнь, Москва | milk-dairy.ru/exhibitors/ | Собственный | ⚠️ Playwright |
| Хлебозавод России | Ноябрь, Москва | bread-expo.ru | Собственный | ⚠️ Playwright |

UUID для Агропродмаш:
- 2024: 348532b3-e716-11ec-80cd-a0d3c1fab97f
- 2025: b67ac0af-40d1-11ee-80ce-a0d3c1fab97f

### 🇰🇿 КАЗАХСТАН

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| FoodExpo Kazakhstan | Ноябрь, Алматы | foodexpo.kz/ru/2025ru → PDF каталог | ITECA (PDF) | ✅ curl + PyMuPDF |
| WorldFood Kazakhstan | Сентябрь, Алматы | exhibitors-itegroup.../worldfood-kazakhstan-<year>/ru/Exhibitor | ITE Group | ✅ Playwright |
| HoReCa Kazakhstan | Апрель, Алматы | horeca-kazakhstan.com/exhibitors/ | Собственный | ⚠️ Playwright |
| AgriTek | Май, Алматы | agritek.kz/exhibitors/ | Собственный | ⚠️ Playwright |
| Dairy & Meat Industry | Октябрь, Алматы | dairy-meat.kz | Собственный | ⚠️ Playwright |

PDF FoodExpo KZ: https://onsite.iteca.kz/img/files/foodexpo/2025/FEQ'25_Exhibitor_List_ru.pdf

### 🇺🇿 УЗБЕКИСТАН

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| UzFood | Октябрь, Ташкент | uzfoodexpo.uz/en/exhibitors-list | Собственный (JS) | ✅ Playwright |
| AgroWorld Uzbekistan | Ноябрь, Ташкент | agroworld.uz/exhibitors/ | Собственный | ⚠️ Playwright |
| UzAgroExpo | Сентябрь, Ташкент | uzagroexpo.uz | Собственный | ⚠️ Playwright |

### 🇦🇿 АЗЕРБАЙДЖАН

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| Caspian Agro | Май, Баку | caspianagroweek.az/ru/official-catalogue → PDF | ERA SOFT + PDF | ✅ Playwright + PyMuPDF |
| InterFood Azerbaijan | Октябрь, Баку | interfood.az/en/exhibitors-list/year/<year> | ERA SOFT (DataTables) | ✅ Playwright |
| WorldFood Azerbaijan | Ноябрь, Баку | worldfood-az.com/exhibitors/ | ERA SOFT | ✅ Playwright |

### 🇦🇲 АРМЕНИЯ

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| InterFood Armenia | Октябрь, Ереван | interfood.am/en/exhibitors-list/year/<year> | ERA SOFT | ✅ Playwright |
| FoodExpo Armenia | Май, Ереван | foodexpo.am/exhibitors/ | Собственный | ⚠️ Playwright |

### 🇬🇪 ГРУЗИЯ

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| FoodExpo Georgia | Ноябрь, Тбилиси | foodexpo.ge/exhibitors/ | Собственный | ⚠️ Playwright |

### 🇧🇾 БЕЛАРУСЬ

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| Продэкспо Беларусь | Октябрь, Минск | prodexpo.by/exhibitors/ | Собственный | ⚠️ Playwright |

### 🇰🇬 КЫРГЫЗСТАН

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| KyrgyzAgro | Сентябрь, Бишкек | kyrgyzagro.kg | Собственный | ⚠️ Playwright |

### 🇹🇯 ТАДЖИКИСТАН

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| TajikAgro | Октябрь, Душанбе | tajikagro.tj | Собственный | ⚠️ Playwright |

### 🇹🇷 ТУРЦИЯ

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| Gulfood Istanbul | Март, Стамбул | gulfoodistanbul.com/exhibitor-list | Собственный | ⚠️ Playwright |
| CNR Food | Февраль, Стамбул | cnrfood.com.tr/exhibitors/ | CNR Expo | ⚠️ Playwright |
| Confectionery Istanbul | Октябрь, Стамбул | confectionery.istanbul | Собственный | ⚠️ Playwright |
| TÜYAP Food | Декабрь, Стамбул | tuyap.com.tr/en/food | TÜYAP | ⚠️ Playwright |

### 🇦🇪 ОАЭ

| Выставка | Период | URL каталога | Платформа | Метод |
|---|---|---|---|---|
| Gulfood | Февраль, Дубай | gulfood.com/exhibitor-list | Informa Markets | ✅ Playwright (JS-SPA) |
| Gulfood Manufacturing | Ноябрь, Дубай | gulfoodmanufacturing.com/exhibitor-list | Informa Markets | ✅ Playwright |
| Middle East Dairy | Октябрь, Дубай | middleeastdairy.com/exhibitors/ | Собственный | ⚠️ Playwright |
| Dubai Chocolate & Confectionery | Март, Дубай | dubaichocolate.com | Собственный | ⚠️ Playwright |

---

## Часть 2: КАТАЛОГИ КОМПАНИЙ (отраслевые справочники)

### 🇷🇺 РОССИЯ

| Ресурс | URL | Что внутри | Метод |
|---|---|---|---|
| Fabricators.ru | fabricators.ru/proizvodstvo/konditerskie-fabriki | 624 кондитерских фабрики | ✅ requests |
| ProductCenter.ru | productcenter.ru/producers/catalog-konditierskiie-izdieliia-427 | Производители с фильтрами | ✅ requests |
| ProductCenter (мороженое) | productcenter.ru/producers/catalog-morozhienoie-461 | 80 фабрик мороженого | ✅ requests |
| ProductCenter (хлеб) | productcenter.ru/producers/catalog-khliebobulochnyie-izdieliia-297 | 180 хлебокомбинатов | ✅ requests |
| Wiki-Prom | wiki-prom.ru/85/konditerskie-fabriki.html | Список заводов | ✅ requests |
| МКОНД | mkond.ru/companies/ | Производители + дистрибьюторы | ✅ requests |
| O-Zavodah.ru | o-zavodah.ru/zavody-proizvoditeli-morozhenogo/ | 48 заводов мороженого | ✅ requests |
| RBC Companies | companies.rbc.ru/okved/10.71/ | Действующие компании | ✅ requests |
| T-Bank Business | tbank.ru/business/contractor/okved/10-71/ | Компании с выручкой | ✅ requests |
| SweetInfo | sweetinfo.ru/litecat | Поставщики кондитерки | ⚠️ Playwright |

### 🇰🇿 КАЗАХСТАН

| Ресурс | URL | Что внутри | Метод |
|---|---|---|---|
| Kazbrand.kz | kazbrand.kz/catalog | Производители КЗ | ✅ requests |
| MadeInKZ.kz | madeinkz.kz | Каталог производителей | ✅ requests |
| Data.egov.kz | data.egov.kz | Открытые данные | ✅ JSON API |

### 🇧🇾 БЕЛАРУСЬ

| Ресурс | URL | Что внутри | Метод |
|---|---|---|---|
| Belmarket.by | belmarket.by/producers | Производители РБ | ✅ requests |
| Products.by | products.by | Каталог производителей | ✅ requests |

### 🇹🇷 ТУРЦИЯ

| Ресурс | URL | Что внутри | Метод |
|---|---|---|---|
| TurkishExporter.net | turkishexporter.net | Экспортёры Турции | ✅ requests |
| TurkeyBusiness.com | turkeybusiness.com | Каталог компаний | ✅ requests |
| Confectionery Turkey | confectioneryturkey.com | Кондитерская отрасль | ✅ requests |

### 🇦🇪 ОАЭ

| Ресурс | URL | Что внутри | Метод |
|---|---|---|---|
| UAE Yellow Pages | yellowpages.ae | Каталог компаний | ✅ requests |
| FoodInGulf.com | foodingulf.com | F&B компании ОАЭ | ✅ requests |

### 🌍 ГЛОБАЛЬНЫЕ

| Ресурс | URL | Что внутри | Метод |
|---|---|---|---|
| Europages | europages.com | Европейские + СНГ компании | ✅ requests |
| TradeWheel | tradewheel.com | Поставщики СНГ | ✅ requests |
| OpenCorporates | opencorporates.com | Глобальный реестр юрлиц | ✅ API (200/день) |

---

## Часть 3: ИСТОЧНИКИ ДЛЯ ОБОГАЩЕНИЯ ДАННЫХ

### 📞 ПОИСК ТЕЛЕФОНОВ И АДРЕСОВ

| Сервис | API | Лимит | Страны |
|---|---|---|---|
| 2GIS | catalog.api.2gis.com/3.0/items | 5000/день бесплатно | РФ, КЗ, КГ, УЗ, ТД, АЗ, ГЕ |
| Yandex Maps | geocode-maps.yandex.ru/1.x/ | 25000/день бесплатно | РФ, РБ, КЗ |
| Google Places | maps.googleapis.com/maps/api/place/ | $200/мес бесплатно | Все страны |
| Dadata | suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party | 10000/день бесплатно | РФ |

### 🌐 ПОИСК САЙТОВ

| Сервис | API | Лимит |
|---|---|---|
| Google Custom Search | googleapis.com/customsearch/v1 | 100 запросов/день |
| Bing Web Search | api.bing.microsoft.com/v7.0/search | 1000/мес бесплатно |
| Clearbit | company.clearbit.com/v2/companies/find | 50/мес бесплатно |

### 🏢 ПОИСК ИНН И ЮРЛИЦ

| Сервис | API | Лимит | Страны |
|---|---|---|---|
| Dadata | suggestions.dadata.ru | 10000/день | РФ |
| OpenCorporates | api.opencorporates.com/v0.4/companies/search | 200/день | Все страны |

### 📧 ПОИСК EMAIL

| Сервис | API | Лимит |
|---|---|---|
| Hunter.io | api.hunter.io/v2/domain-search | 25/мес бесплатно |
| Snov.io | api.snov.io/v1/get-emails-by-domain | 50/мес бесплатно |

### 🏭 ОПРЕДЕЛЕНИЕ ОТРАСЛИ

| Сервис | API | Что даёт |
|---|---|---|
| Dadata | suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party | ОКВЭД, название, адрес |
| 2GIS | catalog.api.2gis.com/3.0/items | Рубрика (кондитерская, молочная и т.д.) |
| Clearbit | company.clearbit.com/v2/companies/find | Категория, размер, отрасль |

---

## 🎯 ПРИОРИТЕТНЫЙ ПЛАН ДЕЙСТВИЙ

### ФАЗА 1: Парсинг выставок (1-2 недели)
1. FoodExpo Kazakhstan 2025 (PDF, ~279 компаний)
2. Caspian Agro 2025 (PDF, ~178 компаний)
3. InterFood Azerbaijan 2023-2025 (Playwright, ~50 компаний/год)
4. Агропродмаш 2024-2025 (requests, ~500 компаний/год)
5. WorldFood Moscow 2024-2025 (Playwright, ~185 компаний/год)
6. Gulfood 2024-2026 (Playwright, ~7000 компаний/год) — приоритет №1 для ОАЭ

### ФАЗА 2: Парсинг каталогов (1 неделя)
1. Fabricators.ru (624 фабрики РФ)
2. ProductCenter.ru (все категории)
3. Kazbrand.kz (КЗ)
4. Belmarket.by (РБ)
5. TurkishExporter.net (Турция)

### ФАЗА 3: Обогащение данных (2-3 недели)
1. 2GIS API — поиск телефонов/адресов для всех записей без телефонов
2. Dadata API — поиск ИНН и ОКВЭД для российских компаний
3. Google Custom Search — поиск сайтов

### ФАЗА 4: Финальная категоризация (2-3 дня)

---

## 📊 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

| Источник | Компаний | С телефонами | С сайтами |
|---|---|---|---|
| Выставки СНГ | ~2000 | ~30% | ~50% |
| Выставки Турция+ОАЭ | ~8000 | ~60% | ~80% |
| Каталоги РФ | ~1500 | ~70% | ~90% |
| Каталоги СНГ | ~500 | ~50% | ~70% |
| Каталоги Турция | ~300 | ~60% | ~80% |
| ИТОГО | ~12300 | ~50-60% | ~70-80% |

После обогащения через 2GIS + Dadata + Google Search:
- С телефонами: ~85-90%
- С сайтами: ~95%
- С ИНН (РФ): ~90%
