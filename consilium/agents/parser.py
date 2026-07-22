"""Parser — парсинг сайтов, извлечение продукции и категорий"""
import os, sys, asyncio, aiohttp, re, json
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from providers import consilium_ask
from models import ClientCategory

PROXY = "https://proton-proxy.onrender.com/proxy?url="
PAGES_TO_TRY = ["/", "/produktsiya", "/catalog", "/about", "/contacts", "/o-kompanii", "/kontakty"]

CATEGORY_KEYWORDS = {
    ClientCategory.CONFECTIONERY.value: ["кондитер", "шоколад", "конфет", "печень", "вафл", "торт", "карамел", "зефир", "мармелад", "халв", "козинак"],
    ClientCategory.DAIRY.value: ["молоч", "йогурт", "сыр", "творог", "кефир", "сметан", "масло сливоч", "сыворотк"],
    ClientCategory.HEALTHY_FOOD.value: ["здоров", "батончик", "протеин", "зож", "фитнес", "диетич", "злак"],
    ClientCategory.NUTS_DRIED.value: ["орех", "сухофрукт", "семечк", "фисташк", "миндал", "фундук", "арахис", "кураг", "чернослив", "изюм"],
    ClientCategory.FROZEN.value: ["морожен", "заморозк", "сорбет", "фруктовый лёд", "ice cream"],
    ClientCategory.BAKERY.value: ["хлеб", "пекар", "булк", "батон", "круассан", "пончик", "сдоб", "выпечк"],
    ClientCategory.INGREDIENTS.value: ["ингредиент", "добавк", "ароматизатор", "красител", "консервант", "лецитин", "какао"],
    ClientCategory.MIDDLEMAN.value: ["дистрибьют", "оптов", "перепрода", "посредник", "трейд", "снабжен", "поставк"],
}

GLAZE_BUYER_PATTERNS = {
    "high": ["закупаем глазурь", "ищем поставщик", "покупаем кондитерск", "сырьё для конфет", "ингредиенты для шоколад"],
    "medium": ["производство конфет", "глазированные сырки", "шоколадная фабрика", "кондитерская фабрика", "производство тортов"],
    "negative": ["продаём глазурь", "поставляем ингредиенты", "производим глазурь", "продажа сырья"],
}

async def fetch_page(session, url, timeout=10):
    """Запрос страницы с fallback"""
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status == 200:
                return await r.text()
    except:
        pass
    try:
        async with session.get(f"{PROXY}{url}", headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            if r.status == 200:
                return await r.text()
    except:
        pass
    return None

def extract_text(html):
    """Извлечение чистого текста из HTML"""
    try:
        import trafilatura
        text = trafilatura.extract(html)
        if text and len(text) > 100:
            return text[:3000]
    except:
        pass
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)
    return text[:3000] if text else ""

def keyword_category(text):
    """Определение категории по ключевым словам"""
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text.lower())
        if score > 0:
            scores[cat] = score
    return max(scores, key=scores.get) if scores else None

def extract_products_bs4(html):
    """Извлечение продукции через BeautifulSoup"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    products = []
    for selector in ['h2', 'h3', '.product-title', '.catalog-item-title', '.card-title', 'li']:
        for el in soup.select(selector)[:30]:
            text = el.get_text(strip=True)
            if 3 < len(text) < 120 and not any(skip in text.lower() for skip in ['главная', 'контакты', 'о нас', 'новости', 'меню']):
                products.append(text)
    return list(set(products))[:20]

def detect_glaze_buyer(text):
    """Определение покупателя глазури по тексту"""
    score = 0
    for p in GLAZE_BUYER_PATTERNS["negative"]:
        if p.lower() in text.lower():
            return False, -1
    for p in GLAZE_BUYER_PATTERNS["high"]:
        if p.lower() in text.lower():
            score += 3
    for p in GLAZE_BUYER_PATTERNS["medium"]:
        if p.lower() in text.lower():
            score += 2
    if "глазур" in text.lower():
        score += 1
    return score >= 3, score

async def parse_client_website(session, client):
    """Парсинг сайта одного клиента"""
    if not client.website:
        return client
    
    base_url = client.website if client.website.startswith("http") else f"https://{client.website}"
    all_text = ""
    
    for page in PAGES_TO_TRY[:3]:
        url = urljoin(base_url, page)
        html = await fetch_page(session, url)
        if html:
            text = extract_text(html)
            if text:
                all_text += text + "\n"
                break
    
    if not all_text:
        return client
    
    # Категория через ключевые слова
    cat = keyword_category(all_text)
    if cat:
        client.category = cat
    
    # Продукция
    html = await fetch_page(session, base_url)
    if html:
        products = extract_products_bs4(html)
        client.products = products[:30]
    
    # Если ключевые слова не сработали → AI
    if not client.category and len(all_text) > 500:
        prompt = f"""Проанализируй текст с сайта компании {client.name_clean}:
{all_text[:1500]}

Определи категорию (строго одно из): Кондитерские изделия, Молочные продукты, Здоровое питание, Орехи и сухофрукты, Заморозка, Перекупы, Хлеб/Пекарни, Ингредиенты, Не определено.
Ответь одним словом."""
        result = await consilium_ask(session, prompt)
        if result.get("best"):
            client.category = result["best"].strip()
    
    # Покупатель глазури?
    is_buyer, score = detect_glaze_buyer(all_text)
    if is_buyer and client.group_tag != "Глазури":
        client.group_tag = "Потенциальный покупатель глазури"
    
    client.data_score += 1
    return client

async def run_parser(session, clients, stats):
    """Главный метод Parser"""
    print("\n=== ЭТАП 3: PARSER ===")
    
    clients_with_site = [c for c in clients if c.website and not c.products]
    print(f"  Сайтов для парсинга: {len(clients_with_site)}")
    
    for i, c in enumerate(clients_with_site):
        if i % 50 == 0:
            print(f"  Прогресс: {i}/{len(clients_with_site)} (+{stats.parser_categorized} категорий)")
        
        await parse_client_website(session, c)
        stats.parser_processed += 1
        
        if c.category:
            stats.parser_categorized += 1
        
        await asyncio.sleep(0.2)
    
    print(f"✅ Parser завершён: {stats.parser_processed} сайтов, {stats.parser_categorized} категорий")
    return clients
