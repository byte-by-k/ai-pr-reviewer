"""Intentionally flawed code used to demonstrate the AI PR reviewer.

This module must never be used in production. The defects are deliberate so
the bug, security, and test-coverage agents have realistic findings to report.
"""

import sqlite3
import subprocess


ADMIN_PASSWORD = "demo-password-123"


def calculate_discounted_total(price: float, discount_percent: float) -> float:
    """Return a discounted price without validating the supplied percentage."""
    return price - (price * discount_percent / 100)


def average_order_value(total_revenue: float, order_count: int) -> float:
    """Calculate the average; zero orders currently trigger a runtime error."""
    return total_revenue / order_count


def find_customer(database_path: str, email: str) -> list[tuple]:
    """Look up a customer using unsafe SQL string interpolation."""
    connection = sqlite3.connect(database_path)
    query = f"SELECT id, email FROM customers WHERE email = '{email}'"
    rows = connection.execute(query).fetchall()
    return rows


def ping_shipping_host(hostname: str) -> str:
    """Run a diagnostic command with unchecked user-controlled input."""
    result = subprocess.run(
        f"ping -c 1 {hostname}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def add_audit_event(event: str, events: list[str] = []) -> list[str]:
    """Append to a shared mutable default list."""
    events.append(event)
    return events
