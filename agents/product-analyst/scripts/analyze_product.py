"""Анализ продукта через 5 моделей Consilium"""
import os, sys, json, asyncio, aiohttp, re
from collections import Counter

import importlib.util
_consilium = os.path.expanduser("~/.hermes/skills/consilium")
_providers = importlib.util.spec_from_file_location("providers", os.path.join(_consilium, "providers.py"))
_providers_mod = importlib.util.module_from_spec(_providers)
sys.path.insert(0, _consilium)
_providers.loader.exec_module(_providers_mod)
ask_model = _providers_mod.ask_model
from cache import get_cache

MODELS = [
    ("mistral/mistral-large-latest", "Mistral"),
    ("groq/llama-3.3-70b-versatile", "Groq"),
    ("sambanova/DeepSeek-V3.2", "SambaNova"),
    ("openrouter/google/gemini-2.5-flash-lite", "Gemini"),
    ("cloudflare/@cf/meta/llama-3.2-3b-instruct", "Cloudflare"),
]
MODEL_NAMES = [m for m, _ in MODELS]
REQUIRED_FIELDS = ["groups", "subgroups"]

async def analyze(product_name, force_refresh=False):
    prompt = f"""Analyze B2B food ingredient applications for "{product_name}" in CIS market (Russia, Kazakhstan, Uzbekistan, Armenia, Azerbaijan, Kyrgyzstan, Tajikistan, Turkmenistan, Georgia).

Target categories: confectionery, dairy, baby food, bread, oils/fats, frozen, snacks, nuts, dry fruits, distribution.
Exclude: alcohol, sugar/honey, animal feed, meat/fish, vegetables/fruits, spices, tea/coffee, beverages, cereals, pasta.

Answer STRICTLY JSON:
{{"product":"{product_name}","subgroups":["..."],"groups":["Кондитерские изделия",...],"keywords":["..."],"exclude_keywords":["..."]}}"""

    cache = get_cache()
    if not force_refresh:
        cached = cache.get(prompt, MODEL_NAMES)
        if cached is not None:
            print(f"Анализирую: {product_name}")
            print("  💾 Взято из кэша")
            print(f"\nГруппы: {cached.get('groups', [])}")
            print(f"Моделей (из кэша): {cached.get('models_responded', '?')}/{len(MODELS)}")
            out = os.path.expanduser("./data/last_analysis.json")
            with open(out, "w") as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)
            print(f"Сохранено: {out}")
            return cached

    print(f"Анализирую: {product_name}")
    async with aiohttp.ClientSession() as session:
        tasks = [ask_model(session, m, prompt, timeout=120) for m, _ in MODELS]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    all_subgroups, all_groups, all_keywords, all_exclude = [], [], [], []
    ok = 0
    for (model, name), resp in zip(MODELS, responses):
        if isinstance(resp, str) and resp.strip():
            try:
                j = json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group())
                subgroups = j.get("subgroups", [])
                groups = j.get("groups", [])
                keywords = j.get("keywords", [])
                exclude = j.get("exclude_keywords", [])
                # Flatten: some models return list of dicts instead of strings
                for item in subgroups:
                    if isinstance(item, dict):
                        all_subgroups.append(str(item))
                    elif isinstance(item, str):
                        all_subgroups.append(item)
                for item in groups:
                    if isinstance(item, dict):
                        all_groups.append(str(item))
                    elif isinstance(item, str):
                        all_groups.append(item)
                for item in keywords:
                    if isinstance(item, dict):
                        all_keywords.append(str(item))
                    elif isinstance(item, str):
                        all_keywords.append(item)
                for item in exclude:
                    if isinstance(item, dict):
                        all_exclude.append(str(item))
                    elif isinstance(item, str):
                        all_exclude.append(item)
                ok += 1
                print(f"  {name}: OK")
            except:
                print(f"  {name}: невалидный JSON")
        else:
            print(f"  {name}: нет ответа или пустые группы")

    needs_review = ok < 3
    result = {
        "product": product_name,
        "subgroups": [s for s, _ in Counter(all_subgroups).most_common(10)],
        "groups": [g for g, _ in Counter(all_groups).most_common(5)],
        "keywords": [k for k, _ in Counter(all_keywords).most_common(10)],
        "exclude_keywords": [k for k, _ in Counter(all_exclude).most_common(5)],
        "models_responded": ok,
        "needs_review": needs_review,
    }
    if not needs_review:
        cache.set(prompt, MODEL_NAMES, result)

    out = os.path.expanduser("./data/last_analysis.json")
    with open(out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nГруппы: {result['groups']}")
    print(f"Моделей: {ok}/{len(MODELS)}")
    if needs_review:
        print(f"⚠️ ТРЕБУЕТ ПРОВЕРКИ: только {ok}/{len(MODELS)} с непустыми данными")
    print(f"Сохранено: {out}")
    return result

if __name__ == "__main__":
    product = sys.argv[1] if len(sys.argv) > 1 else "Какао-порошок натуральный"
    force = "--refresh" in sys.argv
    asyncio.run(analyze(product, force_refresh=force))
