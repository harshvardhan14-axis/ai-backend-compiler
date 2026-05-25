# validator.py
# ─────────────────────────────────────────────────────────────
# This file is the VALIDATION LAYER of the pipeline.
# After the AI generates the database + API schemas,
# we need to check if they are consistent with each other.
#
# Think of it like a proofreader — it doesn't generate anything,
# it just checks what was already generated and reports problems.
#
# Checks performed:
#   1. every_table_has_primary_key()  — every table must have an id
#   2. api_references_valid_tables()  — API paths must match table names
#   3. no_empty_tables()             — tables must have at least 1 column
#   4. no_empty_endpoints()          — endpoints must have response fields
#   5. validate_all()                — runs ALL checks, returns a report
# ─────────────────────────────────────────────────────────────

from schemas import DatabaseSchema, APISchema


# ─────────────────────────────────────────────────────────────
# HELPER — extract_table_names()
# Returns a simple list of table names from the database schema.
# Used by other checks below.
# ─────────────────────────────────────────────────────────────

def extract_table_names(database: DatabaseSchema) -> list[str]:
    """Returns a list of all table names, e.g. ['users', 'tasks']"""
    return [table.table_name for table in database.tables]


# ─────────────────────────────────────────────────────────────
# CHECK 1 — every_table_has_primary_key()
# Every table MUST have a column where primary_key = True.
# If not, we can't reliably identify individual rows.
# ─────────────────────────────────────────────────────────────

def every_table_has_primary_key(database: DatabaseSchema) -> list[str]:
    """
    Checks that every table has at least one primary key column.

    Returns:
        A list of error messages. Empty list = no errors.
    """
    errors = []

    for table in database.tables:
        # Look for any column with primary_key = True
        has_pk = any(col.primary_key for col in table.columns)

        if not has_pk:
            errors.append(
                f"Table '{table.table_name}' has no primary key column. "
                f"Add a column with primary_key=true (e.g. 'id')."
            )

    return errors


# ─────────────────────────────────────────────────────────────
# CHECK 2 — api_references_valid_tables()
# Every API endpoint path should reference a table that exists.
# E.g. if there's a GET /users endpoint, a 'users' table must exist.
#
# How we check: extract the first segment of the path.
# /users       → "users"
# /users/{id}  → "users"
# /tasks/{id}  → "tasks"
# ─────────────────────────────────────────────────────────────

def api_references_valid_tables(database: DatabaseSchema, api: APISchema) -> list[str]:
    """
    Checks that every API endpoint path matches a known table name.

    Returns:
        A list of error messages. Empty list = no errors.
    """
    errors = []
    table_names = extract_table_names(database)

    for endpoint in api.endpoints:
        # Split the path by '/' and grab the first real segment
        # e.g. "/users/{id}" → ["", "users", "{id}"] → "users"
        parts = endpoint.path.strip("/").split("/")
        resource = parts[0] if parts else ""

        # Skip empty or root paths
        if not resource:
            continue

        # Check if this resource matches any known table
        if resource not in table_names:
            errors.append(
                f"Endpoint '{endpoint.method} {endpoint.path}' references "
                f"resource '{resource}', but no table named '{resource}' exists. "
                f"Known tables: {table_names}"
            )

    return errors


# ─────────────────────────────────────────────────────────────
# CHECK 3 — no_empty_tables()
# Every table must have at least one column.
# An empty table is useless and likely a generation error.
# ─────────────────────────────────────────────────────────────

def no_empty_tables(database: DatabaseSchema) -> list[str]:
    """
    Checks that no table has zero columns.

    Returns:
        A list of error messages. Empty list = no errors.
    """
    errors = []

    for table in database.tables:
        if len(table.columns) == 0:
            errors.append(
                f"Table '{table.table_name}' has no columns. "
                f"Every table needs at least an 'id' column."
            )

    return errors


# ─────────────────────────────────────────────────────────────
# CHECK 4 — no_empty_endpoints()
# Every endpoint must have at least one response field.
# An endpoint that returns nothing is a generation error.
# ─────────────────────────────────────────────────────────────

def no_empty_endpoints(api: APISchema) -> list[str]:
    """
    Checks that no endpoint has an empty response_fields list.

    Returns:
        A list of error messages. Empty list = no errors.
    """
    errors = []

    for endpoint in api.endpoints:
        if len(endpoint.response_fields) == 0:
            errors.append(
                f"Endpoint '{endpoint.method} {endpoint.path}' has no response fields. "
                f"Every endpoint must return at least one field."
            )

    return errors


# ─────────────────────────────────────────────────────────────
# CHECK 5 — valid_http_methods()
# Every endpoint method must be GET, POST, PUT, or DELETE.
# ─────────────────────────────────────────────────────────────

def valid_http_methods(api: APISchema) -> list[str]:
    """
    Checks that all endpoint methods are valid HTTP verbs.

    Returns:
        A list of error messages. Empty list = no errors.
    """
    allowed_methods = {"GET", "POST", "PUT", "DELETE"}
    errors = []

    for endpoint in api.endpoints:
        if endpoint.method.upper() not in allowed_methods:
            errors.append(
                f"Endpoint '{endpoint.path}' has invalid method '{endpoint.method}'. "
                f"Must be one of: {allowed_methods}"
            )

    return errors


# ─────────────────────────────────────────────────────────────
# MAIN — validate_all()
# Runs ALL checks above and returns a single validation report.
# This is the only function called from outside this file.
# ─────────────────────────────────────────────────────────────

def validate_all(database: DatabaseSchema, api: APISchema) -> dict:
    """
    Runs all validation checks and returns a report.

    Args:
        database: The DatabaseSchema from Stage 2.
        api:      The APISchema from Stage 3.

    Returns:
        A dict with:
          - "passed"  (bool):       True if zero errors found
          - "errors"  (list[str]):  All error messages found
          - "checks"  (dict):       Per-check breakdown of errors
    """

    # Run every check and collect results
    checks = {
        "primary_keys":    every_table_has_primary_key(database),
        "table_references": api_references_valid_tables(database, api),
        "empty_tables":    no_empty_tables(database),
        "empty_endpoints": no_empty_endpoints(api),
        "http_methods":    valid_http_methods(api),
    }

    # Flatten all errors into one list
    all_errors = []
    for check_name, errors in checks.items():
        all_errors.extend(errors)

    # Build the final report
    report = {
        "passed": len(all_errors) == 0,   # True only if no errors at all
        "errors": all_errors,             # Full list of every error found
        "checks": checks,                 # Breakdown by check name
    }

    return report