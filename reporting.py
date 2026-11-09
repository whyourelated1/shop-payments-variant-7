"""Format payment amounts for a human-readable receipt."""
from decimal import Decimal, ROUND_HALF_UP


def format_amount(amount, currency="RUB"):
    """Format a finite non-negative amount using two decimal places."""
    value = Decimal(str(amount))
    if not value.is_finite() or value < 0:
        raise ValueError("Amount must be finite and non-negative")
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    text = f"{rounded:,.2f}".replace(",", " ").replace(".", ",")
    return f"{text} {currency}"
