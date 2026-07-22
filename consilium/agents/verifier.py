"""Verifier — финальная очистка и фильтрация"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import TARGET_COUNTRIES
from cleaners import clean_name, normalize_country, extract_country_city

async def run_verifier(clients, stats):
    """Финальная проверка"""
    print("\n=== ЭТАП 5: VERIFIER ===")
    verified = []
    
    for c in clients:
        # Очистка названия
        c.name_clean = clean_name(c.name_clean or c.legal_title or "")
        
        # Нормализация страны
        c.country = normalize_country(c.country)
        
        # Извлечение страны из адреса если нет
        if not c.country and c.legal_address:
            c.country, c.city = extract_country_city(c.legal_address)
        
        # Фильтрация по целевым странам
        if c.country not in TARGET_COUNTRIES:
            continue
        
        # Пропускаем дубли
        if c.is_duplicate:
            stats.verifier_deduped += 1
            continue
        
        # Подсчёт data_score
        c.data_score = sum([
            1 if c.inn else 0,
            1 if c.phone else 0,
            1 if c.email else 0,
            1 if c.website else 0,
            1 if c.products else 0,
        ])
        
        # confidence
        c.confidence = c.data_score
        if c.confidence < 2:
            c.needs_review = True
            stats.verifier_needs_review += 1
        
        stats.verifier_cleaned += 1
        verified.append(c)
    
    print(f"✅ Verifier завершён: {stats.verifier_cleaned} чистых, {stats.verifier_deduped} дублей, {stats.verifier_needs_review} на проверку")
    return verified
