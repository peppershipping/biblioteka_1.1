from decimal import Decimal

import pytest

from app.services.ratings import compute_total


@pytest.mark.parametrize(
    "plot,characters,style,expected",
    [
        (8, 9, 7, "8.0"),
        (9, 9, 8, "8.7"),   # 26/3 = 8.666… -> 8.7 (пример из ТЗ, раздел 17)
        (1, 1, 1, "1.0"),
        (10, 10, 10, "10.0"),
        (7, 7, 8, "7.3"),   # 22/3 = 7.333… -> 7.3
        (5, 6, 6, "5.7"),
    ],
)
def test_total_is_rounded_mean(plot, characters, style, expected):
    assert compute_total(plot, characters, style) == Decimal(expected)


def test_total_has_one_decimal_place():
    assert compute_total(8, 9, 7).as_tuple().exponent == -1
