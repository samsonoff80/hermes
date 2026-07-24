from collections import defaultdict
import json

def merge_results(*data_sources):
    """
    Объединяет результаты анализа из нескольких источников.
    
    Args:
        *data_sources: Список словарей с данными (например, основной анализ + ЗОЖ).
    
    Returns:
        dict: Объединённые данные.
    """
    merged = defaultdict(dict)
    for data in data_sources:
        for product, groups in data.items():
            for group, subgroups in groups.items():
                if group not in merged[product]:
                    merged[product][group] = {}
                for subgroup, items in subgroups.items():
                    if subgroup not in merged[product][group]:
                        merged[product][group][subgroup] = []
                    merged[product][group][subgroup].extend(items)
    
    # Удаление дубликатов и сортировка
    for product, groups in merged.items():
        for group, subgroups in groups.items():
            for subgroup, items in subgroups.items():
                merged[product][group][subgroup] = sorted(list(set(items)))
    
    return dict(merged)

# Пример использования
if __name__ == "__main__":
    main_data = {
        "Какао-порошок": {
            "Кондитерские фабрики": {
                "Крупные производители": ["фабрика1", "фабрика2"],
                "Малые производители": ["фабрика3"]
            }
        }
    }
    
    health_data = {
        "Какао-порошок": {
            "Производители здорового питания": {
                "Протеиновые батончики": ["бренд1", "бренд2"],
                "Веганские десерты": ["бренд3"]
            }
        }
    }
    
    result = merge_results(main_data, health_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))