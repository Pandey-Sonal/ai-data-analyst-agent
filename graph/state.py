from typing import TypedDict


class AgentState(TypedDict):
    question: str
    sql: str
    is_valid: bool
    result: list
    columns:list
    dataframe:object
    error: str
    retry_count: int
    explanation: str