"""Validated shipping-price calculation used as a clean review sample."""

from decimal import Decimal


def calculate_shipping(weight_kg: Decimal, rate_per_kg: Decimal) -> Decimal:
    """Calculate shipping cost for strictly positive inputs."""
    if weight_kg <= 0:
        raise ValueError("weight_kg must be greater than zero")
    if rate_per_kg <= 0:
        raise ValueError("rate_per_kg must be greater than zero")
    return (weight_kg * rate_per_kg).quantize(Decimal("0.01"))
