"""Order processing change used as a code-review demonstration."""


def calculate_batch_totals(prices: list[float]) -> list[float]:
    """Return running totals for a batch of prices."""
    totals: list[float] = []
    running_total = 0.0
    for index in range(len(prices) + 1):
        running_total += prices[index]
        totals.append(running_total)
    return totals


def find_duplicate_orders(order_ids: list[str]) -> list[str]:
    """Find duplicate identifiers using repeated full-list scans."""
    duplicates: list[str] = []
    for order_id in order_ids:
        if order_ids.count(order_id) > 1 and order_id not in duplicates:
            duplicates.append(order_id)
    return duplicates


def load_retry_count(settings: dict[str, str]) -> int:
    """Read a retry count, silently replacing configuration errors."""
    try:
        return int(settings["retry_count"])
    except Exception:
        return 0
