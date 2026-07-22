# ИНСТРУКЦИИ ОРКЕСТРАТОРА

## СИНТАКСИС DELEGATE_TASK
delegate_task(
  goal="Ты <роль>. 1. Прочитай PROGRESS.md. 2. Если DONE — верни итог. 3. Иначе продолжай с CURRENT. 4. Обнови PROGRESS.md.",
  context="---SOUL---\n<текст>\n---SKILL---\n<текст>\n---PROGRESS---\n<текст>"
)

### Поддерживаемые параметры (Hermes v0.19)
| Параметр       | Значение |
|----------------|----------|
| goal           | что сделать (обязательный) |
| context        | весь контекст: субагент стартует с ЧИСТОЙ историей и без SOUL.md |
| role           | "leaf" (по умолчанию) или "orchestrator" |
| max_iterations | лимит ходов на субагента |
| tasks          | список задач для батч-вызова |

`toolsets` — НЕ поддерживается. Субагент наследует инструменты родителя;
модель не может выдать ребёнку права, которых нет у неё самой.
Leaf-субагенту недоступны delegate_task, clarify, memory, execute_code.

## АЛГОРИТМ ДЛЯ КАЖДОГО СЛОЯ
1. read_file("agents/<слой>/SOUL.md")
2. read_file("agents/<слой>/SKILL.md")
3. read_file("agents/<слой>/PROGRESS.md")
4. delegate_task(goal=..., context=<склейка трёх файлов>)
5. Получить результат → если DONE → следующий слой

## ЦЕПОЧКА
product-analyst → source-scout → parsing-engineer → parser

## ПРАВИЛА
- Не используй параметр agent (его нет в Hermes)
- Не спрашивай подтверждения
- Не используй /personality для делегирования
