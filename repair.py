# repair.py
# ─────────────────────────────────────────────────────────────
# This file is the REPAIR LAYER of the pipeline.
# It only runs if the validator found errors.
#
# Key idea: we DON'T regenerate everything from scratch.
# We send the BROKEN schema + the SPECIFIC ERRORS back to
# Groq and ask it to fix only what's wrong.
#
# This is smarter and faster than redoing all 3 stages.
#
# Repair order:
#   1. repair_database()  — fixes database schema if broken
#   2. repair_api()       — fixes API schema if broken
#   3. repair_all()       — decides what needs fixing + runs it
# ─────────────────────────────────────────────────────────────

import json
from groq import Groq
import os
from dotenv import load_dotenv

from schemas import DatabaseSchema, APISchema

# Load environment variables
load_dotenv()

# Reuse the same Groq client + model as generator.py
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"


# ─────────────────────────────────────────────────────────────
# HELPER — call_groq_repair()
# Same pattern as generator.py's call_groq(), but named
# separately so it's clear this is a repair call.
# ─────────────────────────────────────────────────────────────

def call_groq_repair(system_prompt: str, user_prompt: str) -> dict:
    """
    Calls Groq for a repair task and returns a parsed JSON dict.

    Args:
        system_prompt: Instructions for how to repair the schema.
        user_prompt:   The broken schema + list of errors to fix.

    Returns:
        A Python dict parsed from the AI's JSON response.
    """
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
    )

    raw_text = response.choices[0].message.content
    return json.loads(raw_text)


# ─────────────────────────────────────────────────────────────
# REPAIR 1 — repair_database()
# Called when the validator found errors in the database schema.
# Sends the broken database JSON + errors to Groq and asks
# it to return a corrected version.
# ─────────────────────────────────────────────────────────────

def repair_database(database: DatabaseSchema, errors: list[str]) -> DatabaseSchema:
    """
    Repairs the database schema based on validation errors.

    Args:
        database: The broken DatabaseSchema from Stage 2.
        errors:   List of error strings from the validator.

    Returns:
        A repaired DatabaseSchema object.
    """

    system_prompt = """
You are a database repair AI.
You will be given a broken database schema (as JSON) and a list of errors.
Your job is to fix the schema so all errors are resolved.

You MUST return a corrected JSON object with EXACTLY this structure:
{
  "tables": [
    {
      "table_name": "users",
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "primary_key": true,
          "nullable": false
        }
      ]
    }
  ]
}

Rules:
- Fix ONLY what the errors describe. Do not change anything else.
- Every table MUST have an 'id' column (INTEGER, primary_key: true, nullable: false)
- Use simple SQL types only: INTEGER, TEXT, BOOLEAN, FLOAT, TIMESTAMP
- Table names must be lowercase and plural
- Return ONLY the corrected JSON object, nothing else
"""

    # Convert the broken schema to a readable JSON string
    broken_json = database.model_dump_json(indent=2)

    # Format errors as a numbered list for clarity
    error_list = "\n".join(f"{i+1}. {e}" for i, e in enumerate(errors))

    user_message = f"""
Here is the broken database schema:
{broken_json}

Here are the errors you must fix:
{error_list}

Return the fully corrected database schema JSON.
"""

    raw = call_groq_repair(system_prompt, user_message)

    # Validate repaired output with Pydantic
    return DatabaseSchema(**raw)


# ─────────────────────────────────────────────────────────────
# REPAIR 2 — repair_api()
# Called when the validator found errors in the API schema.
# Sends the broken API JSON + database table names + errors
# to Groq and asks it to return a corrected version.
# ─────────────────────────────────────────────────────────────

def repair_api(api: APISchema, database: DatabaseSchema, errors: list[str]) -> APISchema:
    """
    Repairs the API schema based on validation errors.

    Args:
        api:      The broken APISchema from Stage 3.
        database: The (possibly repaired) DatabaseSchema — needed
                  so the AI knows what table names are valid.
        errors:   List of error strings from the validator.

    Returns:
        A repaired APISchema object.
    """

    system_prompt = """
You are an API repair AI.
You will be given a broken API schema (as JSON) and a list of errors.
Your job is to fix the schema so all errors are resolved.

You MUST return a corrected JSON object with EXACTLY this structure:
{
  "endpoints": [
    {
      "method": "GET",
      "path": "/users",
      "description": "Get all users",
      "request_body": null,
      "response_fields": ["id", "name", "email"]
    }
  ]
}

Rules:
- Fix ONLY what the errors describe. Do not change anything else.
- method must be one of: GET, POST, PUT, DELETE
- path must start with '/' and reference a valid table name
- request_body must be null for GET and DELETE requests
- response_fields must always be a non-empty list of strings
- Return ONLY the corrected JSON object, nothing else
"""

    # Convert broken API schema to readable JSON
    broken_json = api.model_dump_json(indent=2)

    # Give the AI the valid table names so it can fix path references
    table_names = [t.table_name for t in database.tables]

    # Format errors as a numbered list
    error_list = "\n".join(f"{i+1}. {e}" for i, e in enumerate(errors))

    user_message = f"""
Here is the broken API schema:
{broken_json}

Valid table names in the database: {table_names}

Here are the errors you must fix:
{error_list}

Return the fully corrected API schema JSON.
"""

    raw = call_groq_repair(system_prompt, user_message)

    # Validate repaired output with Pydantic
    return APISchema(**raw)


# ─────────────────────────────────────────────────────────────
# MAIN — repair_all()
# The only function called from outside this file.
#
# It looks at the validation report and decides:
#   - Does the database need repair? → call repair_database()
#   - Does the API need repair?      → call repair_api()
#   - Nothing broken?                → return as-is
#
# Returns the (possibly repaired) schemas + a list of what
# repairs were made (for the final pipeline output).
# ─────────────────────────────────────────────────────────────

def repair_all(
    database: DatabaseSchema,
    api: APISchema,
    validation_report: dict
) -> tuple[DatabaseSchema, APISchema, list[str]]:
    """
    Runs repairs on whichever schemas failed validation.

    Args:
        database:          The DatabaseSchema from Stage 2.
        api:               The APISchema from Stage 3.
        validation_report: The dict returned by validate_all().

    Returns:
        A tuple of:
          - repaired DatabaseSchema  (or original if no errors)
          - repaired APISchema       (or original if no errors)
          - list of repair descriptions (what was fixed)
    """

    repairs_made = []  # We'll log what we fixed here

    # If validation already passed, nothing to do
    if validation_report["passed"]:
        return database, api, repairs_made

    # ── Figure out which checks failed ──────────────────────

    checks = validation_report["checks"]

    # Database-related check names
    db_check_names = ["primary_keys", "empty_tables"]

    # API-related check names
    api_check_names = ["table_references", "empty_endpoints", "http_methods"]

    # Collect database errors
    db_errors = []
    for check_name in db_check_names:
        db_errors.extend(checks.get(check_name, []))

    # Collect API errors
    api_errors = []
    for check_name in api_check_names:
        api_errors.extend(checks.get(check_name, []))

    # ── Repair database if needed ────────────────────────────

    if db_errors:
        print(f"  [Repair] Fixing database schema ({len(db_errors)} error(s))...")
        database = repair_database(database, db_errors)
        repairs_made.append(
            f"Repaired database schema: fixed {len(db_errors)} error(s): "
            + "; ".join(db_errors)
        )

    # ── Repair API if needed ─────────────────────────────────
    # Note: we pass the (possibly just-repaired) database here
    # so the AI has the correct table names when fixing paths.

    if api_errors:
        print(f"  [Repair] Fixing API schema ({len(api_errors)} error(s))...")
        api = repair_api(api, database, api_errors)
        repairs_made.append(
            f"Repaired API schema: fixed {len(api_errors)} error(s): "
            + "; ".join(api_errors)
        )

    return database, api, repairs_made