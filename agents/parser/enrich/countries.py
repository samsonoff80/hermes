"""Справочник стран СНГ"""
COUNTRIES_MAP = {
    "RUSSIA": "RU","RUSSIAN FEDERATION": "RU","РОССИЯ": "RU","РФ": "RU",
    "KAZAKHSTAN": "KZ","КАЗАХСТАН": "KZ",
    "UZBEKISTAN": "UZ","УЗБЕКИСТАН": "UZ",
    "AZERBAIJAN": "AZ","АЗЕРБАЙДЖАН": "AZ",
    "ARMENIA": "AM","АРМЕНИЯ": "AM",
    "KYRGYZSTAN": "KG","КЫРГЫЗСТАН": "KG","КИРГИЗИЯ": "KG",
    "TAJIKISTAN": "TJ","ТАДЖИКИСТАН": "TJ",
    "TURKMENISTAN": "TM","ТУРКМЕНИСТАН": "TM",
    "GEORGIA": "GE","ГРУЗИЯ": "GE",
}

def normalize_country(text: str) -> str:
    if not text:
        return "UNKNOWN"
    return COUNTRIES_MAP.get(text.upper().strip(), text.strip().upper())
