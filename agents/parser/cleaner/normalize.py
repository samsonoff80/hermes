"""Нормализация названий компаний"""
import re
import unicodedata

LEGAL_FORMS_CYR = r"ООО|АО|ЗАО|ОАО|ПАО|ТОО|ИП|ЧП|СП|ОДО|УП|ЧУП|ЖШС|МЧЖ"
LEGAL_FORMS_LAT = r"LLC|LTD|LIMITED|INC|CORP|GMBH|SARL|SRL|BV|AG|PLC|JSC|CO"
RE_LEGAL = re.compile(r"\b(?:" + LEGAL_FORMS_CYR + "|" + LEGAL_FORMS_LAT + r")\b\.?", re.IGNORECASE)

COUNTRIES = [
    "RUSSIA","RUSSIAN FEDERATION","KAZAKHSTAN","UZBEKISTAN","AZERBAIJAN",
    "ARMENIA","KYRGYZSTAN","TAJIKISTAN","TURKMENISTAN","GEORGIA",
    "РОССИЯ","РФ","КАЗАХСТАН","УЗБЕКИСТАН","АЗЕРБАЙДЖАН",
    "АРМЕНИЯ","КЫРГЫЗСТАН","ТАДЖИКИСТАН","ТУРКМЕНИСТАН","ГРУЗИЯ"
]
RE_COUNTRY_SUFFIX = re.compile(
    r"[\s,.\s\(\)\[\]]*\b(?:" + "|".join(re.escape(c) for c in COUNTRIES) + r")\b[\s,.\s\(\)\[\]]*$",
    re.IGNORECASE
)

def normalize(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", str(text))
    t = t.replace("‑", " ").replace("—", " ").replace("–", " ").replace("−", " ")
    t = re.sub(r'[\'"«»‘’„“”()\[\]{}]', ' ', t)
    t = t.upper()
    t = re.sub(r'\b([A-ZА-ЯЁ]{2,4})\.', r'\1', t)
    # Удаляем юрформы только с краёв
    t = re.sub(r"^(" + "|".join(LEGAL_FORMS_CYR.split("|")) + r")\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+(" + "|".join(LEGAL_FORMS_CYR.split("|")) + r")$", "", t, flags=re.IGNORECASE)
    t = RE_COUNTRY_SUFFIX.sub("", t)
    t = re.sub(r'[^A-ZА-ЯЁ0-9\s]', ' ', t)
    return " ".join(t.split()).strip()
