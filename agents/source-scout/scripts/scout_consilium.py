"""Consilium Scout — поиск дополнительных источников через 5 моделей"""
import os, sys, json, asyncio, aiohttp, re
from collections import Counter

sys.path.insert(0, os.path.expanduser("~/.hermes/skills/consilium"))
import importlib.util, os as _os
_consilium = _os.path.expanduser("~/.hermes/skills/consilium")
_providers_spec = importlib.util.spec_from_file_location("providers", _os.path.join(_consilium, "providers.py"))
_providers = importlib.util.module_from_spec(_providers_spec)
_providers_spec.loader.exec_module(_providers)
ask_model = _providers.ask_model

MODELS = [
    ("openrouter/nvidia/nemotron-3-super-120b-a12b:free", "NVIDIA"),
    ("openrouter/google/gemma-4-31b-it:free", "Gemma"),
    ("mistral/mistral-large-latest", "Mistral"),
    ("cloudflare/@cf/meta/llama-3.2-3b-instruct", "Cloudflare"),
    ("groq/llama-3.3-70b-versatile", "Groq"),
]

TARGET_COUNTRIES = ["Таджикистан", "Туркменистан", "Азербайджан", "Кыргызстан"]

async def find_sources(session, country):
    prompt = f"""Найди 5-10 реальных источников (сайтов) для поиска списков производителей пищевого сырья в стране {country}.

Источники могут быть:
- Выставки (пищевые, кондитерские, масложировые)
- B2B каталоги производителей
- Реестры предприятий (egrul, nalog, stat)
- Ассоциации пищевой промышленности
- Тендерные площадки
- Жёлтые страницы / справочники бизнеса

Для каждого источника дай:
1. Название (на русском или английском)
2. URL (реальный существующий сайт)
3. Тип (exhibition / catalog / register / association / tender / directory)
4. Качество (A/B/C) — A=можно парсить напрямую, B=нужен прокси/playwright, C=сложно
5. Пищевая релевантность (1-10)

Ответь СТРОГО JSON массив:
[
  {{"name": "...", "url": "https://...", "type": "...", "quality": "...", "food_relevance": N}},
  ...
]

НЕ выдумывай URL. Только реальные известные сайты."""

    results = []
    tasks = [ask_model(session, m, prompt, timeout=120) for m, _ in MODELS]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    for (model, name), resp in zip(MODELS, responses):
        if isinstance(resp, str) and resp.strip():
            try:
                text = resp.strip()
                if "```" in text:
                    text = re.sub(r'```(?:json)?', '', text).strip()
                start = text.find("[")
                end = text.rfind("]")
                if start >= 0 and end > start:
                    arr = json.loads(text[start:end+1])
                    if isinstance(arr, list):
                        results.extend(arr)
                        print(f"  {name}: {len(arr)} источников")
                    else:
                        print(f"  {name}: не массив")
                else:
                    print(f"  {name}: нет JSON массива")
            except Exception as e:
                print(f"  {name}: ошибка парсинга — {e}")
        else:
            print(f"  {name}: нет ответа")
    
    return results

async def main():
    all_results = {}
    async with aiohttp.ClientSession() as session:
        for country in TARGET_COUNTRIES:
            print(f"\n{'='*50}")
            print(f"🔍 {country}")
            print('='*50)
            sources = await find_sources(session, country)
            
            # Deduplicate by URL
            seen = set()
            unique = []
            for src in sources:
                url = src.get("url", "").rstrip("/").replace("www.", "")
                if url and url not in seen:
                    seen.add(url)
                    unique.append(src)
            
            all_results[country] = unique
            print(f"  → {len(unique)} уникальных источников")
    
    # Save
    output_path = os.path.expanduser("~/.hermes/skills/layer2-scout/data/sources_consilium_extra.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "_date": "2026-06-19",
            "_method": "consilium_5_models",
            "target_countries": TARGET_COUNTRIES,
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n{'='*50}")
    print(f"ИТОГО:")
    total = 0
    for country, sources in all_results.items():
        print(f"  {country}: {len(sources)} уникальных")
        total += len(sources)
    print(f"  ВСЕГО: {total}")
    print(f"\nСохранено: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
