"""
Перевод ошибок валидации Pydantic на русский язык (ТЗ 13.2 «Локализация»,
13.1 п. 3 «понятные ошибки»). Чистая функция — не зависит от FastAPI.
"""

_SKIP_LOC = {"body", "query", "path", "header", "cookie"}


def _expected(ctx: dict) -> str:
    return str(ctx.get("expected", "")).replace("'", "")


def message_for(err: dict) -> str:
    kind = err.get("type", "")
    ctx = err.get("ctx") or {}
    msg = str(err.get("msg", ""))

    if kind == "missing":
        return "обязательное поле"
    if kind == "string_too_short":
        return f"слишком короткое значение (минимум {ctx.get('min_length')} симв.)"
    if kind == "string_too_long":
        return f"слишком длинное значение (максимум {ctx.get('max_length')} симв.)"
    if kind == "too_short":
        return "нужен хотя бы один элемент" if ctx.get("min_length") == 1 else "слишком мало элементов"
    if kind == "too_long":
        return f"слишком много элементов (максимум {ctx.get('max_length')})"
    if kind == "greater_than_equal":
        return f"значение должно быть не меньше {ctx.get('ge')}"
    if kind == "less_than_equal":
        return f"значение должно быть не больше {ctx.get('le')}"
    if kind == "greater_than":
        return f"значение должно быть больше {ctx.get('gt')}"
    if kind == "less_than":
        return f"значение должно быть меньше {ctx.get('lt')}"
    if kind in {"int_parsing", "int_type", "int_from_float"}:
        return "ожидается целое число"
    if kind in {"float_parsing", "float_type"}:
        return "ожидается число"
    if kind in {"bool_parsing", "bool_type"}:
        return "ожидается логическое значение"
    if kind in {"string_type", "string_pattern_mismatch"}:
        return "ожидается строка" if kind == "string_type" else "недопустимый формат"
    if kind in {"enum", "literal_error"}:
        return f"допустимые значения: {_expected(ctx)}"
    if kind == "json_invalid":
        return "некорректный JSON"
    if kind in {"model_attributes_type", "dict_type", "model_type"}:
        return "ожидается JSON-объект"
    if kind == "value_error":
        text = msg.removeprefix("Value error, ")
        if "email" in text.lower():
            return "некорректный адрес электронной почты"
        return text
    return msg or "некорректное значение"


def format_errors(raw_errors: list[dict]) -> list[dict]:
    """[{'field': 'password', 'message': 'слишком короткое значение (минимум 8 симв.)'}, ...]"""
    result = []
    for err in raw_errors:
        loc = [str(p) for p in err.get("loc", ()) if str(p) not in _SKIP_LOC]
        result.append({"field": ".".join(loc) or "запрос", "message": message_for(err)})
    return result


def summarize(errors: list[dict]) -> str:
    parts = [f"{e['field']}: {e['message']}" for e in errors[:5]]
    return "Ошибка валидации. " + "; ".join(parts)
