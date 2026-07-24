# PDF-парсинг каталогов выставок — уроки (2026-06-13)

## Ключевой инсайт
**PDF-каталоги выставок — ОСНОВНОЙ источник данных**, не веб-парсинг.
Прошлый успешный парсинг базы (3000+ записей) был именно из PDF каталогов выставок.
Проблема была в плохой очистке данных, а не в источнике.

## Известные PDF-каталоги выставок

### Prodexpo (Москва)
- 2025: `prodexpo25_catalogue.pdf` (18 MB) ✅ скачан
- 2024: `prodexpo24_catalogue.pdf` (19 MB) ✅ скачан
- 2023: не скачан (сайт защищён, 50 редиректов)
- 2026: `prod26cat.pdf` — сайт prod-expo.ru защищён от хотлинкинга

### Agroprodmash (Москва)
- 2025: `agro25_catalog.pdf` (20 MB) ✅ скачан
- 2025: `agro25guide.pdf` (12 MB) ✅ скачан
- 2024: `agro24catalog.pdf` (16 MB) ✅ скачан

### World Food Moscow
- 2025: `WF2025_catalogue_2025.09.11_01.pdf` (10 MB) ✅ скачан
- 2024: `WF2024_catalogue_2024.09.01_preview_page.pdf` (3 MB) ✅ скачан

### Другие выставки (нужно искать PDF)
- FoodExpo Kazakhstan (foodexpo.kz)
- Uz Agro Expo (uzfoodexpo.uz)
- Caspian Agro (Азербайджан)
- InterFood (Казахстан, Азербайджан, Армения)
- Югпищемаш (Краснодар)
- Сибпищемаш (Новосибирск)
- Peterfood (Санкт-Петербург)

## Как искать PDF через Serper
```python
queries = [
    'prodexpo 2026 catalogue filetype:pdf',
    'agroprodmash 2025 catalogue filetype:pdf site:agroprodmash-expo.ru',
    'world food moscow 2025 exhibitor list filetype:pdf',
    'foodexpo kazakhstan 2025 catalogue filetype:pdf',
]
```

## Как скачивать PDF
```bash
# Через curl (работает лучше чем aiohttp для редиректов)
curl -L -o file.pdf "URL" -H "User-Agent: Mozilla/5.0" --connect-timeout 30 --max-time 120

# Через прокси (если напрямую не работает)
curl -L -o file.pdf "https://proton-proxy.onrender.com/proxy?url=URL"
```

**Проблемы:**
- prod-expo.ru возвращает 50 редиректов → curl не справляется
- Некоторые сайты требуют cookies/сессию
- Решение: искать альтернативные URL через Serper

## Как парсить PDF
```python
import fitz  # pymupdf

doc = fitz.open(pdf_path)
for page in doc:
    text = page.get_text()
    # Извлекаем компании по паттернам
```

## Типичные проблемы парсинга PDF

### 1. Неправильное определение страны
PDF каталоги содержат списки регионов России → парсер определяет как "Узбекистан".
**Решение:** Страна по умолчанию = страна выставки (Россия для prodexpo/agroprodmash/worldfood).
Не определять страну по тексту PDF — он содержит регионы, а не страны.

### 2. Мусорные "компании"
Парсер захватывает регионы ("Республика Адыгея"), павильоны, госорганы.
**Решение:** Расширенный список TRASH_PATTERNS + дефолтная страна выставки.

### 3. Мало контактов (~25-30%)
PDF каталоги выставок обычно содержат только название + стенд + краткое описание.
Контакты в отдельном разделе или вообще отсутствуют.
**Решение:** Обогащение через DaData (ИНН), Serper (телефоны), парсинг сайтов.

### 4. Обрезанные названия
Названия сливаются с описанием или обрезаются.
**Решение:** Очистка через clean_name() с полным списком паттернов.

## Статистика парсинга (13.06.2026)
| PDF | Страниц | Размер | Компании | С контактами |
|-----|---------|--------|----------|--------------|
| prodexpo2025 | 548 | 18 MB | 3729 | 25% |
| agroprodmash2024 | 366 | 16 MB | 1474 | 37% |
| agroprodmash2025 | 52 | 20 MB | 183 | 3% |

## Важно: таблица clients vs clean_clients
- **clients** — основная таблица (name, phone, email, website, inn, source, country, group_tag)
- **clean_clients** — НЕТ полей phone/email, не использовать для основной базы
- supabase_loader.py должен писать в clients!
