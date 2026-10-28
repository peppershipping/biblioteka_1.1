"""Бизнес-логика оценок: итоговая оценка (ТЗ 4.2, правило 30)."""

from decimal import ROUND_HALF_UP, Decimal


def compute_total(plot: int, characters: int, style: int) -> Decimal:
    """
    Итоговая оценка = (Сюжет + Персонажи + Стиль) / 3, округление до одного знака.
    Округление «half up» совпадает с ROUND() для NUMERIC в PostgreSQL, которым
    пользуется триггер recalc_rating_total.
    """
    return (Decimal(plot + characters + style) / Decimal(3)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
