# Web Search Company Finding — Session Notes 21.06.2026

## Что делали
Искали пищевые компании для стран с малым покрытием (TJ, TM, KG, UZ, AZ, AM, GE) через web_search + загрузку в Supabase.

## Результат
Загружено в raw_parsed_data: 40 записей
- Таджикистан: 13 (Ширин, Амири, Almos, Водии Мевахо, Оро Исфара, Исфара Фуд, Меваи Тиллои, Меваи Зарин, Висол, Тути Помир, Али Априкот, Субхи Ватан, Худжандский консервный завод)
- Кыргызстан: 4 (АТА Лтд, Таттуу, Куликовский, Двойняшки)
- Узбекистан: 8 (Deya, Aura, Arbis, Miray, Krember, Zarqand, Hassons, Intergrain)
- Азербайджан: 2 (Shirin, Кировабадская)
- Армения: 5 (Grand Candy, Даройнк, Веллар Груп, Канач Снунд, Элен-Арт)
- Грузия: 2 (Union Group, Нарцисси)

## Проблема: все записи заблокированы dedup в clean_clients
clean_data.py делает dedup по (name_clean, country). Все найденные компании уже существуют в clean_clients от других источников (consilium_batch*, gulfood/anuga, flagma.tj и т.д.).

**Вывод**: web_search подход для расширения базы имеет ограниченную ценность — он находит компании которые уже есть.

## Рекомендации
1. **Обогащение контактов** — использовать web_search для поиска email/phone существующих компаний, а не для поиска новых
2. **Upsert вместо insert** — обновлять существующие записи новыми данными
3. **Фильтрация дублей ДО загрузки** — проверять (name_clean, country) against existing clean_clients

## Контакты найденные через web_search
- Grand Candy (AM): info@grandcandy.am, +37496211110, grandcandy.am
- Даройнк (AM): +37410447510, daroink.am
- Веллар Груп (AM): +37410539818
- Канач Снунд (AM): +37455951951
- Aura/UZ: Ташкентская область, Яккасарайский район, ул. Кушбеги, 6
- Deya/UZ: deya.uz
- Arbis/UZ: arbis.gl.uz
- Miray/UZ: miraygroup.uz
- Krember/UZ: krember.uz
- Shirin/AZ: shirin.az/ru

## Скрипты
- `scripts/load_tj_kg_companies.py` — шаблон для TJ/KG
- `scripts/load_uz_az_companies.py` — шаблон для UZ/AZ
- `scripts/load_am_ge_companies.py` — шаблон для AM/GE
