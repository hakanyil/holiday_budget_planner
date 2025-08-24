from decimal import Decimal, ROUND_HALF_UP, getcontext

getcontext().prec = 28
TWOP = Decimal("0.01")


def d_round(value: Decimal) -> Decimal:
    """Round a :class:`~decimal.Decimal` to two places using ``ROUND_HALF_UP``."""
    return value.quantize(TWOP, rounding=ROUND_HALF_UP)
