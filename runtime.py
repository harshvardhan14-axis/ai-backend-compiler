# runtime.py
# ─────────────────────────────────────────────────────────────
# This file is the RUNTIME SIMULATION LAYER of the pipeline.
# It does NOT actually run a server or execute SQL.
# Instead, it SIMULATES what would happen if the app ran:
#
#   • Can we "create" all the tables? (simulate DB setup)
#   • Can we "call" each API endpoint? (simulate HTTP requests)
#   • Do the responses match what the schema promises?
#
# Think of it like a dry-run or rehearsal before the real show.
# It catches logical problems that validation couldn't catch.
#
# This is pure Python — no AI calls, no network, no database.
# Everything is simulated in memory using fake data.
#
# Steps:
#   1. simulate_database_setup()  — "creates" tables in memory
#   2. simulate_api_execution()   — "calls" each endpoint
#   3. run_simulation()           — runs both + returns a report
# ─────────────────────────────────────────────────────────────

from schemas import DatabaseSchema, APISchema, IntentSchema


# ─────────────────────────────────────────────────────────────
# HELPER — generate_fake_value()
# Given a column type, returns a realistic fake value.
# Used to simulate what a database row would look like.
# ─────────────────────────────────────────────────────────────

def generate_fake_value(col_type: str, col_name: str):
    """
    Returns a fake value for a given SQL column type.

    Args:
        col_type: SQL type string e.g. 'INTEGER', 'TEXT'
        col_name: Column name e.g. 'email', 'id'

    Returns:
        A fake Python value matching the type.
    """
    col_type = col_type.upper()
    col_name = col_name.lower()

    # Use column name hints for more realistic fake data
    if col_name == "id":
        return 1
    if "email" in col_name:
        return "user@example.com"
    if "name" in col_name:
        return "John Doe"
    if "password" in col_name:
        return "hashed_password_123"
    if "phone" in col_name:
        return "+1234567890"
    if "date" in col_name or "created" in col_name or "updated" in col_name:
        return "2024-01-01T00:00:00"

    # Fall back to type-based defaults
    if col_type == "INTEGER":
        return 1
    elif col_type == "TEXT":
        return "sample_text"
    elif col_type == "BOOLEAN":
        return True
    elif col_type == "FLOAT":
        return 1.0
    elif col_type == "TIMESTAMP":
        return "2024-01-01T00:00:00"
    else:
        return "unknown"


# ─────────────────────────────────────────────────────────────
# STEP 1 — simulate_database_setup()
# Walks through every table and "creates" it in memory.
# Returns a fake in-memory database as a dict of table -> rows.
# Also checks for any setup problems.
# ─────────────────────────────────────────────────────────────

def simulate_database_setup(database: DatabaseSchema) -> dict:
    """
    Simulates creating all database tables in memory.

    Args:
        database: The DatabaseSchema to simulate.

    Returns:
        A dict with:
          - "success"        (bool):       Did all tables set up OK?
          - "tables_created" (list[str]):  Names of tables created
          - "fake_db"        (dict):       In-memory fake database
          - "errors"         (list[str]):  Any problems found
    """

    fake_db = {}       # Simulated database: { table_name: [row_dict] }
    tables_created = []
    errors = []

    for table in database.tables:
        # Build a fake row using the column definitions
        fake_row = {}
        for col in table.columns:
            fake_row[col.name] = generate_fake_value(col.type, col.name)

        # Check: nullable=False columns must have a value
        for col in table.columns:
            if not col.nullable and fake_row.get(col.name) is None:
                errors.append(
                    f"Table '{table.table_name}': column '{col.name}' "
                    f"is NOT NULL but would receive a null value."
                )

        # "Insert" one fake row into the simulated table
        fake_db[table.table_name] = [fake_row]
        tables_created.append(table.table_name)

        print(f"  [Runtime] Table '{table.table_name}' created with "
              f"{len(table.columns)} column(s). Sample row: {fake_row}")

    return {
        "success": len(errors) == 0,
        "tables_created": tables_created,
        "fake_db": fake_db,
        "errors": errors,
    }


# ─────────────────────────────────────────────────────────────
# STEP 2 — simulate_api_execution()
# Walks through every endpoint and "calls" it in memory.
# Uses the fake_db from Step 1 to simulate real responses.
# Checks that the response actually contains the promised fields.
# ─────────────────────────────────────────────────────────────

def simulate_api_execution(api: APISchema, fake_db: dict) -> dict:
    """
    Simulates calling every API endpoint against the fake database.

    Args:
        api:     The APISchema to simulate.
        fake_db: The in-memory fake database from simulate_database_setup().

    Returns:
        A dict with:
          - "success"            (bool):       Did all endpoints run OK?
          - "endpoints_tested"   (int):        How many endpoints were tested
          - "results"            (list[dict]): Per-endpoint simulation results
          - "errors"             (list[str]):  Any problems found
    """

    results = []
    errors = []

    for endpoint in api.endpoints:
        method = endpoint.method.upper()
        path   = endpoint.path

        # Figure out which table this endpoint is for
        # e.g. "/users/{id}" -> "users"
        resource = path.strip("/").split("/")[0]

        # Build a simulated response based on the method
        simulated_response = {}
        endpoint_errors = []

        if method == "GET":
            # Simulate fetching from the fake database
            if resource in fake_db and fake_db[resource]:
                row = fake_db[resource][0]
                simulated_response = {
                    field: row.get(field, f"<missing:{field}>")
                    for field in endpoint.response_fields
                }
            else:
                simulated_response = []

        elif method == "POST":
            # Simulate creating a new record
            if resource in fake_db and fake_db[resource]:
                row = fake_db[resource][0]
                simulated_response = {
                    field: row.get(field, f"<missing:{field}>")
                    for field in endpoint.response_fields
                }
            else:
                simulated_response = {"id": 1, "status": "created"}

        elif method == "PUT":
            # Simulate updating a record
            simulated_response = {"status": "updated", "id": 1}

        elif method == "DELETE":
            # Simulate deleting a record
            simulated_response = {"status": "deleted", "id": 1}

        # Check: response fields exist in the fake row
        if method in ("GET", "POST") and isinstance(simulated_response, dict):
            for field in endpoint.response_fields:
                value = simulated_response.get(field, "")
                if isinstance(value, str) and value.startswith("<missing:"):
                    endpoint_errors.append(
                        f"{method} {path}: response field '{field}' "
                        f"not found in table '{resource}'"
                    )

        errors.extend(endpoint_errors)

        result = {
            "method":   method,
            "path":     path,
            "status":   "OK" if not endpoint_errors else "FAILED",
            "response": simulated_response,
            "errors":   endpoint_errors,
        }
        results.append(result)

        status_label = "OK" if not endpoint_errors else "FAILED"
        print(f"  [Runtime] {method:6} {path:30} -> {status_label}")

    return {
        "success":          len(errors) == 0,
        "endpoints_tested": len(api.endpoints),
        "results":          results,
        "errors":           errors,
    }


# ─────────────────────────────────────────────────────────────
# STEP 3 — compute_evaluation_metrics()
# Calculates summary metrics for the pipeline run.
# These are the "evaluation metrics" required by the assignment.
# ─────────────────────────────────────────────────────────────

def compute_evaluation_metrics(
    intent: IntentSchema,
    database: DatabaseSchema,
    api: APISchema,
    db_result: dict,
    api_result: dict,
    repairs_made: list,
) -> dict:
    """
    Computes evaluation metrics for the full pipeline run.

    Returns:
        A dict of named metrics with scores and descriptions.
    """

    total_endpoints = len(api.endpoints)
    passed_endpoints = sum(
        1 for r in api_result["results"] if r["status"] == "OK"
    )

    total_tables = len(database.tables)
    total_columns = sum(len(t.columns) for t in database.tables)

    # Endpoint pass rate (0.0 to 1.0)
    endpoint_pass_rate = (
        round(passed_endpoints / total_endpoints, 2)
        if total_endpoints > 0 else 0.0
    )

    # Schema coverage: did we generate tables for all entities?
    table_names = [t.table_name for t in database.tables]
    entities_covered = sum(
        1 for entity in intent.entities
        if entity.lower() in table_names or entity.lower() + "s" in table_names
    )
    schema_coverage = (
        round(entities_covered / len(intent.entities), 2)
        if intent.entities else 0.0
    )

    # Feature coverage: enough endpoints for the features?
    feature_coverage = round(
        min(total_endpoints / max(len(intent.features), 1), 1.0), 2
    )

    return {
        "total_tables":       total_tables,
        "total_columns":      total_columns,
        "total_endpoints":    total_endpoints,
        "endpoints_passed":   passed_endpoints,
        "endpoint_pass_rate": endpoint_pass_rate,
        "schema_coverage":    schema_coverage,
        "feature_coverage":   feature_coverage,
        "repairs_made":       len(repairs_made),
        "overall_success":    db_result["success"] and api_result["success"],
    }


# ─────────────────────────────────────────────────────────────
# MAIN — run_simulation()
# The only function called from outside this file.
# Runs the full simulation and returns a complete report.
# ─────────────────────────────────────────────────────────────

def run_simulation(
    intent: IntentSchema,
    database: DatabaseSchema,
    api: APISchema,
    repairs_made: list,
) -> dict:
    """
    Runs the full runtime simulation and returns a report.

    Args:
        intent:       The IntentSchema from Stage 1.
        database:     The (repaired) DatabaseSchema.
        api:          The (repaired) APISchema.
        repairs_made: List of repair descriptions from repair.py.

    Returns:
        A dict with:
          - "summary"    (str):  Human-readable result summary
          - "success"    (bool): Did the simulation fully pass?
          - "db_result"  (dict): Database simulation details
          - "api_result" (dict): API simulation details
          - "evaluation" (dict): Evaluation metrics
    """

    print("\n[Runtime] Starting database simulation...")
    db_result = simulate_database_setup(database)

    print("\n[Runtime] Starting API simulation...")
    api_result = simulate_api_execution(api, db_result["fake_db"])

    print("\n[Runtime] Computing evaluation metrics...")
    evaluation = compute_evaluation_metrics(
        intent, database, api, db_result, api_result, repairs_made
    )

    overall = db_result["success"] and api_result["success"]

    summary_lines = [
        f"App: {intent.app_name} ({intent.app_type})",
        f"Tables created: {len(db_result['tables_created'])}",
        f"Endpoints tested: {api_result['endpoints_tested']}",
        f"Endpoints passed: {evaluation['endpoints_passed']} / {evaluation['total_endpoints']}",
        f"Repairs made: {len(repairs_made)}",
        f"Overall result: {'PASSED' if overall else 'FAILED'}",
    ]
    summary = " | ".join(summary_lines)

    return {
        "summary":    summary,
        "success":    overall,
        "db_result":  db_result,
        "api_result": api_result,
        "evaluation": evaluation,
    }