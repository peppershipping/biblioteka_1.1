from app.validation_messages import format_errors, summarize


def test_missing_field_is_translated():
    errors = format_errors([{"type": "missing", "loc": ("body", "username"), "msg": "Field required"}])
    assert errors == [{"field": "username", "message": "обязательное поле"}]


def test_length_and_range_messages():
    errors = format_errors(
        [
            {"type": "string_too_short", "loc": ("body", "password"), "msg": "x", "ctx": {"min_length": 8}},
            {"type": "less_than_equal", "loc": ("body", "plot"), "msg": "x", "ctx": {"le": 10}},
            {"type": "greater_than_equal", "loc": ("query", "offset"), "msg": "x", "ctx": {"ge": 0}},
        ]
    )
    assert errors[0]["message"] == "слишком короткое значение (минимум 8 симв.)"
    assert errors[1]["message"] == "значение должно быть не больше 10"
    assert errors[2] == {"field": "offset", "message": "значение должно быть не меньше 0"}


def test_email_value_error_is_localised():
    errors = format_errors(
        [{"type": "value_error", "loc": ("body", "email"), "msg": "value is not a valid email address: bad"}]
    )
    assert errors[0]["message"] == "некорректный адрес электронной почты"


def test_custom_value_error_keeps_text_without_prefix():
    errors = format_errors([{"type": "value_error", "loc": ("body",), "msg": "Value error, нужен хотя бы один критерий"}])
    assert errors == [{"field": "запрос", "message": "нужен хотя бы один критерий"}]


def test_summary_is_human_readable_and_has_no_internals():
    text = summarize([{"field": "plot", "message": "значение должно быть не больше 10"}])
    assert text.startswith("Ошибка валидации.")
    assert "plot" in text and "Traceback" not in text
