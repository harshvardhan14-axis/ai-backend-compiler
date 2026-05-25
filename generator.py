# generator.py
# ─────────────────────────────────────────────────────────────
# AI GENERATION LAYER
# ─────────────────────────────────────────────────────────────

import os
import json

from groq import Groq
from dotenv import load_dotenv

from schemas import IntentSchema, DatabaseSchema, APISchema


# ─────────────────────────────────────────────────────────────
# LOAD ENV VARIABLES
# ─────────────────────────────────────────────────────────────

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Stable lightweight Groq model
MODEL = "llama-3.1-8b-instant"


# ─────────────────────────────────────────────────────────────
# HELPER — call_groq()
# ─────────────────────────────────────────────────────────────

def call_groq(system_prompt: str, user_prompt: str) -> dict:

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    raw_text = response.choices[0].message.content

    return json.loads(raw_text)


# ─────────────────────────────────────────────────────────────
# STAGE 1 — extract_intent()
# ─────────────────────────────────────────────────────────────

def extract_intent(user_prompt: str) -> IntentSchema:

    system_prompt = """
You are a software architect AI.

Analyze the user's app idea and extract structured intent.

Return ONLY valid JSON.

Required structure:
{
  "app_name": "string",
  "app_type": "string",
  "description": "string",
  "entities": ["string"],
  "features": ["string"]
}
"""

    user_message = f"App idea: {user_prompt}"

    raw = call_groq(system_prompt, user_message)

    # Safety cleanup
    raw.setdefault("app_name", "GeneratedApp")
    raw.setdefault("app_type", "CRUD app")
    raw.setdefault("description", "Generated application")
    raw.setdefault("entities", [])
    raw.setdefault("features", [])

    return IntentSchema(**raw)


# ─────────────────────────────────────────────────────────────
# STAGE 2 — generate_database()
# ─────────────────────────────────────────────────────────────

def generate_database(intent: IntentSchema) -> DatabaseSchema:

    system_prompt = """
You are a database design AI.

Generate a relational database schema.

Return ONLY valid JSON.

Required structure:
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
"""

    user_message = f"""
App name: {intent.app_name}

Entities:
{intent.entities}

Features:
{intent.features}
"""

    raw = call_groq(system_prompt, user_message)

    # Safety cleanup
    raw.setdefault("tables", [])

    for table in raw["tables"]:

        table.setdefault("table_name", "unknown")

        table.setdefault("columns", [])

        has_id = any(col.get("name") == "id" for col in table["columns"])

        # Automatically inject missing id column
        if not has_id:
            table["columns"].insert(0, {
                "name": "id",
                "type": "INTEGER",
                "primary_key": True,
                "nullable": False
            })

    return DatabaseSchema(**raw)


# ─────────────────────────────────────────────────────────────
# STAGE 3 — generate_api()
# ─────────────────────────────────────────────────────────────

def generate_api(intent: IntentSchema, database: DatabaseSchema) -> APISchema:

    system_prompt = """
You are a REST API design AI.

Generate CRUD API endpoints.

Return ONLY valid JSON.

Required structure:
{
  "endpoints": [
    {
      "method": "GET",
      "path": "/users",
      "description": "Get users",
      "request_body": null,
      "response_fields": ["id"]
    }
  ]
}
"""

    table_summary = []

    for table in database.tables:
        cols = [col.name for col in table.columns]
        table_summary.append(
            f"{table.table_name}: {', '.join(cols)}"
        )

    tables_text = "\n".join(table_summary)

    user_message = f"""
App name: {intent.app_name}

Database tables:
{tables_text}
"""

    raw = call_groq(system_prompt, user_message)

    # ─────────────────────────────────────────────────────────
    # SAFETY CLEANUP
    # ─────────────────────────────────────────────────────────

    raw.setdefault("endpoints", [])

    cleaned_endpoints = []

    for endpoint in raw["endpoints"]:

        method = endpoint.get("method", "GET")
        path = endpoint.get("path", "/unknown")
        description = endpoint.get("description", "Generated endpoint")

        request_body = endpoint.get("request_body", None)
        response_fields = endpoint.get("response_fields", [])

        # ── Fix request_body ────────────────────────────────

        # If request_body is a dict, convert keys -> list
        if isinstance(request_body, dict):
            request_body = list(request_body.keys())

        # If invalid type, reset
        if request_body is not None and not isinstance(request_body, list):
            request_body = []

        # GET and DELETE should not have request bodies
        if method.upper() in ["GET", "DELETE"]:
            request_body = None

        # ── Fix response_fields ─────────────────────────────

        # If response_fields is None
        if response_fields is None:
            response_fields = []

        # If response_fields is dict
        if isinstance(response_fields, dict):
            response_fields = list(response_fields.keys())

        # If invalid type
        if not isinstance(response_fields, list):
            response_fields = []

        cleaned_endpoints.append({
            "method": method,
            "path": path,
            "description": description,
            "request_body": request_body,
            "response_fields": response_fields,
        })

    raw["endpoints"] = cleaned_endpoints

    return APISchema(**raw)