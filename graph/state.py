from typing import TypedDict


class AgentState(TypedDict):
    question: str

    # Database information
    schema: str
    db_path: str

    # Schema grounding
    schema_valid: bool
    schema_message: str

    # SQL
    sql: str
    is_valid: bool

    # Query result
    result: list
    columns: list
    dataframe: object

    # Visualization
    visualization: object

    # Errors and retries
    error: str
    retry_count: int

    # Final response
    explanation: str
    rejection_message: str