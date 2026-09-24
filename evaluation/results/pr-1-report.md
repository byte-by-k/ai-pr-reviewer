# Multi-Agent Code Review

**Pull request:** #1 — Demo: intentionally flawed checkout code
**Overall risk:** CRITICAL
**Recommended verdict:** Request Changes

## Executive summary

15 distinct finding(s) remained after combining 3 specialist reviews. Highest severity: critical.

| Critical | High | Medium | Low |
|---:|---:|---:|---:|
| 3 | 6 | 6 | 0 |

## Critical findings

### Hardcoded password in source code

- **Location:** `samples/intentionally_flawed_checkout.py:10`
- **Reviewer:** security
- **Confidence:** High
- **Rules:** SEC-001

The constant ADMIN_PASSWORD contains a plaintext password directly in the source code. This credential is visible to anyone with repository access and will be committed to version control history permanently. Attackers who gain read access to the repository can extract and abuse this credential.

**Evidence:** `ADMIN_PASSWORD = "demo-password-123"`

**Recommendation:** Remove the hardcoded password immediately. Store credentials in environment variables or a secrets management service (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault). Access the credential at runtime using os.environ.get('ADMIN_PASSWORD') or a secrets client library.

### SQL injection vulnerability in find_customer function

- **Location:** `samples/intentionally_flawed_checkout.py:26`
- **Reviewer:** security
- **Confidence:** High
- **Rules:** SEC-002, SEC-003

The find_customer function constructs a SQL query using f-string interpolation with the user-supplied email parameter. An attacker can inject arbitrary SQL by providing a malicious email value such as "' OR '1'='1" to bypass authentication or "'; DROP TABLE customers; --" to execute destructive commands. This allows complete database compromise.

**Evidence:** `query = f"SELECT id, email FROM customers WHERE email = '{email}'"`

**Recommendation:** Use parameterized queries with placeholders. Replace the vulnerable line with: query = "SELECT id, email FROM customers WHERE email = ?" and execute with connection.execute(query, (email,)).fetchall(). This ensures user input is treated as data, not executable SQL code.

### Command injection vulnerability in ping_shipping_host function

- **Location:** `samples/intentionally_flawed_checkout.py:34`
- **Reviewer:** security
- **Confidence:** High
- **Rules:** SEC-003

The ping_shipping_host function passes user-controlled hostname input directly into a shell command using shell=True. An attacker can inject arbitrary shell commands by providing input like "example.com; rm -rf /" or "example.com && cat /etc/passwd". This allows complete system compromise with the privileges of the running process.

**Evidence:** `result = subprocess.run(
        f"ping -c 1 {hostname}",
        shell=True,`

**Recommendation:** Never use shell=True with user input. Pass arguments as a list and validate the hostname format. Replace with: subprocess.run(['ping', '-c', '1', hostname], shell=False, capture_output=True, text=True). Additionally, validate that hostname matches expected patterns (e.g., valid domain or IP address) before executing the command.

## High findings

### Missing input validation in calculate_discounted_total function

- **Location:** `samples/intentionally_flawed_checkout.py:14`
- **Reviewer:** security
- **Confidence:** High
- **Rules:** SEC-003

The calculate_discounted_total function accepts discount_percent without validation. An attacker can supply negative values to increase prices, values over 100 to create negative totals, or extreme values to cause financial calculation errors. This can lead to revenue loss or accounting inconsistencies.

**Evidence:** `def calculate_discounted_total(price: float, discount_percent: float) -> float:
    """Return a discounted price without validating the supplied percentage."""
    return price - (price * discount_percent / 100)`

**Recommendation:** Validate that discount_percent is within acceptable bounds (0 to 100) and that price is positive. Add checks at the start of the function: if not (0 <= discount_percent <= 100): raise ValueError('Discount must be between 0 and 100'). Consider also validating that price >= 0.

### Division by zero when order_count is zero

- **Location:** `samples/intentionally_flawed_checkout.py:20`
- **Reviewer:** correctness
- **Confidence:** High
- **Rules:** No rule ID supplied

The function `average_order_value` performs division without checking if `order_count` is zero. When `order_count=0`, the operation `total_revenue / order_count` raises a ZeroDivisionError at runtime, causing the application to crash.

**Evidence:** `return total_revenue / order_count`

**Recommendation:** Add a guard clause to check if order_count is zero before division. Return 0.0 or raise a domain-specific exception with a clear message: `if order_count == 0: return 0.0` or `if order_count == 0: raise ValueError('Cannot calculate average with zero orders')`

### find_customer lacks SQL injection security tests

- **Location:** `samples/intentionally_flawed_checkout.py:24`
- **Reviewer:** testing
- **Confidence:** High
- **Rules:** TST-001

This public function has no tests, including no security tests for SQL injection. The function uses unsafe string interpolation to build SQL queries. Tests must verify that malicious email inputs (e.g., "' OR '1'='1") do not bypass authentication or extract unintended data.

**Evidence:** `def find_customer(database_path: str, email: str) -> list[tuple]:
    """Look up a customer using unsafe SQL string interpolation."""
    connection = sqlite3.connect(database_path)
    query = f"SELECT id, email FROM customers WHERE email = '{email}'"
    rows = connection.execute(query).fetchall()`

**Recommendation:** Add security tests that attempt SQL injection payloads: (1) email="' OR '1'='1" should not return all customers, (2) email="'; DROP TABLE customers; --" should not execute destructive commands. Also add happy-path tests with valid emails and failure-path tests with non-existent emails. Verify the connection is closed in all cases.

**Suggested test:** test_find_customer_valid_email(), test_find_customer_not_found(), test_find_customer_sql_injection_or_clause(), test_find_customer_sql_injection_drop_table(), test_find_customer_closes_connection()

### Database connection never closed in find_customer

- **Location:** `samples/intentionally_flawed_checkout.py:25`
- **Reviewer:** correctness
- **Confidence:** High
- **Rules:** No rule ID supplied

The function `find_customer` opens a SQLite connection on line 25 but never closes it. This causes a resource leak where database connections accumulate over repeated calls, eventually exhausting available connections and causing application failures.

**Evidence:** `connection = sqlite3.connect(database_path)
    query = f"SELECT id, email FROM customers WHERE email = '{email}'"
    rows = connection.execute(query).fetchall()
    return rows`

**Recommendation:** Use a context manager to ensure the connection is properly closed: `with sqlite3.connect(database_path) as connection:` or explicitly call `connection.close()` in a try-finally block.

### ping_shipping_host lacks command injection security tests

- **Location:** `samples/intentionally_flawed_checkout.py:32`
- **Reviewer:** testing
- **Confidence:** High
- **Rules:** TST-001

This public function has no tests, including no security tests for command injection. The function uses shell=True with unsanitized user input. Tests must verify that malicious hostname inputs (e.g., "example.com; rm -rf /") do not execute arbitrary commands.

**Evidence:** `def ping_shipping_host(hostname: str) -> str:
    """Run a diagnostic command with unchecked user-controlled input."""
    result = subprocess.run(
        f"ping -c 1 {hostname}",
        shell=True,
        capture_output=True,
        text=True,
    )`

**Recommendation:** Add security tests that attempt command injection payloads: (1) hostname="example.com; cat /etc/passwd" should not execute the second command, (2) hostname="example.com && echo hacked" should not execute the echo. Also add happy-path tests with valid hostnames and failure-path tests with invalid hostnames or network errors.

**Suggested test:** test_ping_shipping_host_valid_hostname(), test_ping_shipping_host_invalid_hostname(), test_ping_shipping_host_command_injection_semicolon(), test_ping_shipping_host_command_injection_ampersand(), test_ping_shipping_host_command_injection_pipe()

### Mutable default argument causes shared state bug

- **Location:** `samples/intentionally_flawed_checkout.py:43`
- **Reviewer:** correctness
- **Confidence:** High
- **Rules:** No rule ID supplied

The function `add_audit_event` uses a mutable list `[]` as a default argument. In Python, default arguments are evaluated once at function definition time, not at call time. This means all calls to `add_audit_event` without providing an `events` argument will share the same list object, causing unintended state accumulation across invocations.

**Evidence:** `def add_audit_event(event: str, events: list[str] = []) -> list[str]:
    """Append to a shared mutable default list."""
    events.append(event)
    return events`

**Recommendation:** Use `None` as the default and create a new list inside the function: `def add_audit_event(event: str, events: list[str] = None) -> list[str]:
    if events is None:
        events = []
    events.append(event)
    return events`

## Medium findings

### calculate_discounted_total lacks unit tests for validation and boundary cases

- **Location:** `samples/intentionally_flawed_checkout.py:14`
- **Reviewer:** testing
- **Confidence:** High
- **Rules:** TST-001

This public function has no tests. It accepts unchecked discount_percent values that could be negative, exceed 100, or cause incorrect pricing. Tests should verify happy-path discounts, boundary values (0%, 100%), invalid inputs (negative, >100%), and edge cases (very large prices).

**Evidence:** `def calculate_discounted_total(price: float, discount_percent: float) -> float:
    """Return a discounted price without validating the supplied percentage."""
    return price - (price * discount_percent / 100)`

**Recommendation:** Add unit tests covering: (1) valid discount (e.g., 10% off $100 = $90), (2) 0% discount, (3) 100% discount, (4) negative discount_percent, (5) discount_percent > 100, (6) negative price, (7) zero price.

**Suggested test:** test_calculate_discounted_total_valid_discount(), test_calculate_discounted_total_zero_discount(), test_calculate_discounted_total_full_discount(), test_calculate_discounted_total_negative_discount(), test_calculate_discounted_total_excessive_discount()

### Missing validation allows negative or excessive discount percentages

- **Location:** `samples/intentionally_flawed_checkout.py:15`
- **Reviewer:** correctness
- **Confidence:** High
- **Rules:** No rule ID supplied

The function `calculate_discounted_total` accepts any float value for `discount_percent` without validation. Negative values would increase the price instead of discounting it, and values over 100 would result in negative prices. Both scenarios represent incorrect business logic that could cause financial errors.

**Evidence:** `def calculate_discounted_total(price: float, discount_percent: float) -> float:
    """Return a discounted price without validating the supplied percentage."""
    return price - (price * discount_percent / 100)`

**Recommendation:** Add input validation to ensure discount_percent is within valid bounds: `if not 0 <= discount_percent <= 100: raise ValueError(f'Discount percent must be between 0 and 100, got {discount_percent}')`. Also validate that price is non-negative.

### average_order_value lacks unit tests for division-by-zero failure path

- **Location:** `samples/intentionally_flawed_checkout.py:19`
- **Reviewer:** testing
- **Confidence:** High
- **Rules:** TST-001

This public function has no tests. The code will raise ZeroDivisionError when order_count is zero. Tests must verify the happy path (positive order_count) and the failure path (zero order_count), plus boundary cases (negative values, very large numbers).

**Evidence:** `def average_order_value(total_revenue: float, order_count: int) -> float:
    """Calculate the average; zero orders currently trigger a runtime error."""
    return total_revenue / order_count`

**Recommendation:** Add unit tests covering: (1) valid calculation (e.g., $1000 / 10 orders = $100), (2) zero order_count raises ZeroDivisionError or returns a sentinel value, (3) negative order_count, (4) zero revenue with positive orders.

**Suggested test:** test_average_order_value_valid_orders(), test_average_order_value_zero_orders_raises_error(), test_average_order_value_negative_orders(), test_average_order_value_zero_revenue()

### Database connection not properly closed in find_customer function

- **Location:** `samples/intentionally_flawed_checkout.py:25`
- **Reviewer:** security
- **Confidence:** High
- **Rules:** No rule ID supplied

The find_customer function opens a database connection but never closes it. If this function is called repeatedly, it will leak database connections, eventually exhausting the connection pool. While primarily a reliability issue, connection exhaustion can be exploited for denial-of-service attacks.

**Evidence:** `connection = sqlite3.connect(database_path)
    query = f"SELECT id, email FROM customers WHERE email = '{email}'"
    rows = connection.execute(query).fetchall()
    return rows`

**Recommendation:** Use a context manager to ensure the connection is properly closed. Wrap the connection logic with: with sqlite3.connect(database_path) as connection: ... This guarantees cleanup even if an exception occurs.

### No exception handling for subprocess execution failures

- **Location:** `samples/intentionally_flawed_checkout.py:34`
- **Reviewer:** correctness
- **Confidence:** Medium
- **Rules:** RES-001

The function `ping_shipping_host` executes a subprocess command without any exception handling. If the subprocess fails to start, times out, or encounters other runtime errors, the function will propagate an unhandled exception. This makes the calling code fragile and difficult to handle errors gracefully.

**Evidence:** `result = subprocess.run(
        f"ping -c 1 {hostname}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout`

**Recommendation:** Wrap the subprocess.run call in a try-except block to catch subprocess.SubprocessError, subprocess.TimeoutExpired, and OSError. Log the exception and either return a meaningful error indicator or raise a domain-specific exception. Consider adding a timeout parameter to prevent indefinite hangs.

### add_audit_event lacks tests for mutable default argument bug

- **Location:** `samples/intentionally_flawed_checkout.py:43`
- **Reviewer:** testing
- **Confidence:** High
- **Rules:** TST-001

This public function has no tests. The mutable default argument (events: list[str] = []) causes state to persist across calls, a classic Python bug. Tests must verify that multiple calls without an explicit events argument do not share the same list, and that providing an explicit list works correctly.

**Evidence:** `def add_audit_event(event: str, events: list[str] = []) -> list[str]:
    """Append to a shared mutable default list."""
    events.append(event)
    return events`

**Recommendation:** Add unit tests covering: (1) first call with default argument returns single-item list, (2) second call with default argument incorrectly returns two-item list (demonstrating the bug), (3) explicit empty list argument works correctly, (4) explicit non-empty list argument appends correctly.

**Suggested test:** test_add_audit_event_first_call_default(), test_add_audit_event_second_call_default_shares_state(), test_add_audit_event_explicit_empty_list(), test_add_audit_event_explicit_nonempty_list()

## Agent summaries

- **Correctness:** Found 5 correctness defects: division by zero, unclosed database connection, mutable default argument, missing input validation, and empty catch pattern risk.
- **Security:** Critical security vulnerabilities detected: hardcoded credential, SQL injection, and command injection. All three issues pose immediate exploitation risks and must be remediated before any production use.
- **Testing:** Five public functions lack any unit tests. Missing coverage includes happy-path validation, boundary conditions (zero division, SQL injection, command injection), error handling, and the mutable default argument bug.

## Limitations

- This is static, diff-only AI review; unchanged repository context may be missing.
- Findings require human verification and do not replace security scanners or tests.
- Only project rules retrieved for each changed hunk are considered.
