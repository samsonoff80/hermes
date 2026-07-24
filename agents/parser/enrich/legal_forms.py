"""Справочник юридических форм"""
LEGAL_FORMS = {
    "ООО","АО","ЗАО","ОАО","ПАО","ТОО","ИП","ЧП","СП","ОДО","УП","ЧУП","ЖШС","МЧЖ",
    "LLC","LTD","LIMITED","INC","CORP","GMBH","SARL","SRL","BV","AG","PLC","JSC","CO"
}

def has_legal_form(text: str) -> bool:
    if not text:
        return False
    import re
    for form in LEGAL_FORMS:
        if re.search(rf"\b{re.escape(form)}\b", text, re.IGNORECASE):
            return True
    return False
