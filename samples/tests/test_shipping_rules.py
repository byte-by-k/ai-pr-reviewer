from decimal import Decimal

import pytest

from samples.shipping_rules import calculate_shipping


def test_calculate_shipping_rounds_to_cents():
    assert calculate_shipping(Decimal("2.5"), Decimal("3.333")) == Decimal("8.33")


@pytest.mark.parametrize(
    ("weight", "rate"),
    [
        (Decimal("0"), Decimal("2")),
        (Decimal("-1"), Decimal("2")),
        (Decimal("2"), Decimal("0")),
        (Decimal("2"), Decimal("-1")),
    ],
)
def test_calculate_shipping_rejects_non_positive_inputs(weight, rate):
    with pytest.raises(ValueError):
        calculate_shipping(weight, rate)
