# Коды телефонов — определение страны

## Целевые страны (9 штук)

| Страна | Код | Формат | Пример |
|--------|-----|--------|--------|
| Россия | +7 | +7 9XX XXX XX XX | +7 912 345 67 89 |
| Казахстан | +7 | +7 7XX XXX XX XX | +7 701 234 56 78 |
| Узбекистан | +998 | +998 XX XXX XX XX | +998 90 123 45 67 |
| Кыргызстан | +996 | +996 XXX XXX XXX | +996 555 123 456 |
| Таджикистан | +992 | +992 XXX XX XXXX | +992 93 123 4567 |
| Армения | +374 | +374 XX XXX XXX | +374 91 234 567 |
| Азербайджан | +994 | +994 XX XXX XX XX | +994 50 123 45 67 |
| Туркменистан | +993 | +993 X XX XX XX | +993 6 12 34 56 |
| Грузия | +995 | +995 XXX XXX XXX | +995 555 123 456 |

## Не-СНГ (удалять)

| Страна | Код |
|--------|-----|
| Беларусь | +375 |
| Украина | +380 |
| Китай | +86 |
| Корея | +82 |
| Турция | +90 |
| Сербия | +381 |
| Франция | +33 |
| Германия | +49 |
| Италия | +39 |

## Алгоритм определения

```python
import re

PHONE_TO_COUNTRY = {
    '+7': 'Россия',      # нужно уточнять по следующей цифре
    '+375': 'Беларусь',
    '+380': 'Украина',
    '+998': 'Узбекистан',
    '+996': 'Кыргызстан',
    '+992': 'Таджикистан',
    '+374': 'Армения',
    '+994': 'Азербайджан',
    '+993': 'Туркменистан',
    '+995': 'Грузия',
}

CIS_CODES = {'+7', '+998', '+996', '+992', '+374', '+994', '+993', '+995'}

def detect_country_by_phone(phone):
    if not phone:
        return None
    p = re.sub(r'[\s\-\(\)]', '', str(phone).strip())
    
    # Check specific codes first (longer codes first)
    for code in ['+998', '+996', '+992', '+374', '+994', '+993', '+995', '+375', '+380']:
        if p.startswith(code):
            return PHONE_TO_COUNTRY.get(code)
    
    # Russian/Kazakhstan +7
    if p.startswith('+7') and len(p) >= 11:
        # +7 7XX = Kazakhstan, +7 9XX = Russia
        second_digit = p[2] if len(p) > 2 else ''
        if second_digit == '7':
            return 'Казахстан'
        else:
            return 'Россия'
    
    # 8XXXXXXXXXX format
    if p.startswith('8') and len(p) == 11:
        second_digit = p[1] if len(p) > 1 else ''
        if second_digit == '7':
            return 'Казахстан'
        else:
            return 'Россия'
    
    return None  # Unknown
```
