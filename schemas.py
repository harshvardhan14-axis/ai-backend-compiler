from pydantic import BaseModel, Field
from typing import List, Optional


class IntentSchema(BaseModel):
    app_name: str = Field(..., description="Short name for the app, e.g. 'TodoApp'")
    app_type: str = Field(..., description="Type of app, e.g. 'REST API', 'CRUD app'")
    description: str = Field(..., description="One-sentence summary of what the app does")
    entities: List[str] = Field(..., description="Core data objects, e.g. ['User', 'Task']")
    features: List[str] = Field(..., description="Key features, e.g. ['Create task', 'Delete task']")


class ColumnSchema(BaseModel):
    # A single column inside a database table
    name: str = Field(..., description="Column name, e.g. 'id'")
    type: str = Field(..., description="Data type, e.g. 'INTEGER', 'TEXT', 'BOOLEAN'")
    primary_key: bool = Field(default=False, description="Is this the primary key?")
    nullable: bool = Field(default=True, description="Can this column be empty/null?")


class TableSchema(BaseModel):
    # A single database table with its columns
    table_name: str = Field(..., description="Table name, e.g. 'users'")
    columns: List[ColumnSchema] = Field(..., description="List of columns in this table")


class DatabaseSchema(BaseModel):
    # The full database — a list of tables
    tables: List[TableSchema] = Field(..., description="All tables in the database")


class EndpointSchema(BaseModel):
    # A single API endpoint
    method: str = Field(..., description="HTTP method: GET, POST, PUT, DELETE")
    path: str = Field(..., description="URL path, e.g. '/users/{id}'")
    description: str = Field(..., description="What this endpoint does")
    request_body: Optional[List[str]] = Field(
        default=None,
        description="Fields expected in the request body, e.g. ['name', 'email']"
    )
    response_fields: List[str] = Field(
        ...,
        description="Fields returned in the response, e.g. ['id', 'name']"
    )


class APISchema(BaseModel):
    endpoints: List[EndpointSchema] = Field(..., description="All API endpoints")



class PipelineOutput(BaseModel):
    intent: IntentSchema
    database: DatabaseSchema
    api: APISchema
    validation_passed: bool = Field(..., description="Did the validation layer pass?")
    repairs_made: List[str] = Field(
        default_factory=list,
        description="List of repairs made, e.g. ['Fixed missing primary key in users table']"
    )
    simulation_result: str = Field(
        default="",
        description="Summary from the runtime simulation step"
    )
    evaluation: dict = Field(
        default_factory=dict,
        description="Evaluation metrics from the pipeline run"
    )


class UserRequest(BaseModel):
    prompt: str = Field(..., description="The user's natural language app request")