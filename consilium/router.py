#!/usr/bin/env python3
"""Consilium Router — классификация задач и фильтрация системного промпта.

Раньше модуль существовал, но нигде не импортировался, а его логика была
продублирована инлайном в consilium_server.py. Теперь сервер использует именно
эти функции — дубля больше нет.
"""
import re
import logging
from typing import List, Dict

logger = logging.getLogger('consilium.router')

TASK_KEYWORDS = {
    "search": ["найди", "поиск", "источник", "сайт", "спарси", "scout",
               "url", "http", "парсинг сайт", "парс сайт"],
    "code": ["код", "code", "функци", "function", "скрипт", "script",
             "python", "ошибк", "error", "bug", "парс", "parse"],
    "analysis": ["анализ", "analysis", "сравни", "compare", "статус",
                 "status", "почем", "why", "как работает"],
}


def classify_task(messages: List[Dict]) -> str:
    """Тип задачи по последнему пользовательскому сообщению."""
    user_text = ""
    for m in reversed(messages or []):
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                user_text = c.lower()
            elif isinstance(c, list):
                # v0.19 умеет слать content частями: [{"type":"text","text":...}]
                user_text = " ".join(
                    part.get("text", "") for part in c if isinstance(part, dict)
                ).lower()
            break
    if not user_text:
        return "chat"
    for task in ("search", "code", "analysis"):
        if any(kw in user_text for kw in TASK_KEYWORDS[task]):
            return task
    return "chat"


# Служебные блоки Hermes, которые не несут смысла для модели.
# ВАЖНО: у каждого паттерна есть якорь конца — иначе вырезается весь
# остаток промпта, включая роль агента и протокол вызова слоёв.
# Прежние регулярки были жадными до конца строки: из 631 символов реального
# промпта оставалось 119, а инструкции оркестратора исчезали целиком.
_HERMES_BLOCKS = [
    # Блок «You run on Hermes Agent …»
    re.compile(r"You run on Hermes Agent\b[\s\S]*?(?=\n\s*\n|\n#|\Z)"),
    # Секции Hermes. Граница — пустая строка ИЛИ следующий заголовок любого
    # уровня. Раньше lookahead был '^#\s', который не срабатывает на '## СЛОИ'
    # (там после # идёт #, а не пробел), поэтому блок съедал весь остаток
    # промпта вместе с ролью оркестратора.
    re.compile(r"^#\s*Finishing the job\b[\s\S]*?(?=\n\s*\n|\n#|\Z)", re.MULTILINE),
    re.compile(r"^#\s*Parallel tool calls\b[\s\S]*?(?=\n\s*\n|\n#|\Z)", re.MULTILINE),
    # Блок про persistent memory
    re.compile(r"You have persistent memory across sessions\.[\s\S]*?(?=\n\s*\n|\n#|\Z)"),
]

# Если после фильтрации осталось меньше — считаем, что фильтр съел лишнее,
# и возвращаем исходный промпт. Лучше лишние токены, чем агент без роли.
MIN_KEPT_CHARS = 40


def filter_system_prompt(content: str, request_id: str = "") -> str:
    """Вырезает только служебные блоки Hermes через _HERMES_BLOCKS."""
    if not content or not isinstance(content, str):
        return content
    filtered = content
    for pattern in _HERMES_BLOCKS:
        filtered = pattern.sub("", filtered)
    filtered = re.sub(r"\n{3,}", "\n\n", filtered).strip()
    if len(filtered) < MIN_KEPT_CHARS and len(content) > MIN_KEPT_CHARS:
        return content
    if len(filtered) != len(content):
        logger.info(f"[{request_id}] ✂️ Фильтр: {len(content)}→{len(filtered)} символов")
    return filtered
