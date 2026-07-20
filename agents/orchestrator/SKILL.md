# ИНСТРУКЦИИ ОРКЕСТРАТОРА

## СИНТАКСИС DELEGATE_TASK
delegate_task(
  goal="Ты <роль>. 1. Прочитай PROGRESS.md. 2. Если DONE — верни итог. 3. Иначе продолжай с CURRENT. 4. Обнови PROGRESS.md.",
  context="---SOUL---\n<текст>\n---SKILL---\n<текст>\n---PROGRESS---\n<текст>",
  toolsets=["file","terminal"]
)

## АЛГОРИТМ ДЛЯ КАЖДОГО СЛОЯ
1. read_file("agents/<слой>/SOUL.md")
2. read_file("agents/<слой>/SKILL.md")
3. read_file("agents/<слой>/PROGRESS.md")
4. delegate_task(goal=..., context=..., toolsets=...)
5. Получить результат → если DONE → следующий слой

## ЦЕПОЧКА
product-analyst → source-scout → parsing-engineer → parser

## ПРАВИЛА
- Не используй параметр agent (его нет в Hermes)
- Не спрашивай подтверждения
- Не используй /personality для делегирования
