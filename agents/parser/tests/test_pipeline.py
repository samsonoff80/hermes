"""Тесты для Pipeline V5.5"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cleaner.normalize import normalize
from cleaner.scorer import score
from dedup.fuzzy import FuzzyDedup
from dedup.exact import ExactDedup

def test_normalize():
    assert normalize("ООО Шоколадная Фабрика") == "ШОКОЛАДНАЯ ФАБРИКА"
    assert normalize("STAND 12A") == "12A"
    assert normalize("FOOD EXPO 2024") == "FOOD EXPO 2024"
    assert normalize("ООО Ромашка, Россия") == "РОМАШКА"
    assert normalize("ООО «Ромашка»") == "РОМАШКА"
    assert normalize("NANTONG FOODWE FOODS CO LTD") == "NANTONG FOODWE FOODS"
    print("✅ normalize tests passed")

def test_scorer():
    assert score("ООО Шоколадная Фабрика", normalize("ООО Шоколадная Фабрика")) >= 50
    assert score("STAND 12A", normalize("STAND 12A")) <= 10
    assert score("FOOD EXPO 2024", normalize("FOOD EXPO 2024")) <= 25
    assert score("LLC Chocolate Factory", normalize("LLC Chocolate Factory")) >= 50
    print("✅ scorer tests passed")

def test_fuzzy_dedup():
    fd = FuzzyDedup()
    assert not fd.is_duplicate("ООО МОЛОЧНЫЙ ЗАВОД")
    assert fd.is_duplicate("МОЛОЧНЫЙ ЗАВОД")
    assert not fd.is_duplicate("ООО ШОКОЛАДНАЯ ФАБРИКА")
    assert not fd.is_duplicate("ШОКОЛАДНАЯ ФАБРИКА ЗАО")
    print("✅ fuzzy dedup tests passed")

def test_exact_dedup():
    ed = ExactDedup(":memory:")
    assert not ed.is_duplicate({"email": "test@mail.ru"})
    assert ed.is_duplicate({"email": "test@mail.ru"})
    assert not ed.is_duplicate({"email": "other@mail.ru"})
    ed.close()
    print("✅ exact dedup tests passed")

if __name__ == "__main__":
    test_normalize()
    test_scorer()
    test_fuzzy_dedup()
    test_exact_dedup()
    print("\n🎉 All tests passed!")
