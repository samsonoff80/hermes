"""Скоринг компаний (0-100)"""
import re

RE_URL = re.compile(r'https?://|www\.', re.IGNORECASE)
RE_ADDRESS = re.compile(r'\b(?:ул|г|д|стр|пом|оф|пер|пр-т|просп|наб|пл)\.?\s*[A-ZА-ЯЁ0-9\s,.-]+', re.IGNORECASE)

from cleaner.normalize import RE_LEGAL

BAD_KEYWORDS = {"STAND","HALL","EXHIBITION","CATALOG","VISITOR","BOOTH","ВЫСТАВКА","СТЕНД","ПАВИЛЬОН","СКАЧИВАЙТЕ","ПРИЛОЖЕНИЕ","СПИСОК ПРОДУКТОВ","СПИСОК ФИРМ","СПИСОК УЧАСТНИКОВ"}
GOOD_WORDS_EXACT = {"FOOD","FACTORY","PLANT","DAIRY","EXPORT","IMPORT","ФАБРИКА","ЗАВОД","КОМБИНАТ","МОЛОКО","СЫР","ШОКОЛАД","КАКАО","ГЛАЗУРЬ","ЙОГУРТ","МОРОЖЕНОЕ"}
GOOD_WORDS_PREFIX = {"МОЛОЧ","КОНДИТЕР","ХЛЕБ","МАСЛО","САХАР","ГРЕНК","ГРЕНКИ","СУХАР","СУХАРИ","СУХАРИКИ","СНЭК","СНЭКИ"}
NON_FOOD_KEYWORDS = {"EDUCATION","SCHOOL","UNIVERSITY","MEDICAL","BANK","INSURANCE","CONSTRUCTION","OIL","GAS","NEFT","GAZ","СТРОЙ","НЕФТЬ","БАНК","ШКОЛА","УНИВЕР","МЕДИЦ","СТРАХОВ"}
JOURNAL_KEYWORDS = {"ЖУРНАЛ","MAGAZINE","ИЗДАНИЕ","ИЗДАТЕЛЬСТВО","ПРЕССА","ГАЗЕТА"}

RE_TRASH = re.compile(r"^[\d\s\W]+$")
RE_NON_FOOD = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in NON_FOOD_KEYWORDS) + r")\b", re.IGNORECASE)
RE_BAD = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in BAD_KEYWORDS) + r")\b", re.IGNORECASE)
RE_GOOD_EXACT = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in GOOD_WORDS_EXACT) + r")\b", re.IGNORECASE)
RE_GOOD_PREFIX = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in GOOD_WORDS_PREFIX) + r")", re.IGNORECASE)
RE_JOURNAL = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in JOURNAL_KEYWORDS) + r")\b", re.IGNORECASE)

def score(raw_text: str, normalized_text: str) -> int:
    if not normalized_text or RE_TRASH.match(normalized_text):
        return 0
    if len(normalized_text) < 4:
        return 0
    
    t = normalized_text.upper()
    s = 30
    
    if RE_JOURNAL.search(t):
        s -= 30
    if RE_NON_FOOD.search(t):
        s -= 25
    
    bad_hits = len(RE_BAD.findall(t))
    if bad_hits >= 2:
        s -= 50
    elif bad_hits == 1:
        s -= 20
    
    if RE_URL.search(raw_text) or '@' in raw_text:
        s -= 30
    if RE_ADDRESS.search(raw_text):
        s -= 25
    
    if RE_GOOD_EXACT.search(t) or RE_GOOD_PREFIX.search(t):
        s += 25
    if RE_LEGAL.search(raw_text):
        s += 20
    
    words = [w for w in t.split() if len(w) > 1]
    if len(words) >= 3:
        s += 10
    elif len(words) >= 2:
        s += 5
    if len(normalized_text) >= 15:
        s += 5
    
    return min(100, max(0, s))
