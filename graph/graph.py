from langgraph.graph import StateGraph, START, END

from graph.state import AgentState
from graph.nodes import (
    generate_sql,
    validate_sql,
    execute_sql,
    create_dataframe,
    fix_sql,
    explain_result,
    
)


def check_validation(state: AgentState):
    if state["is_valid"]:
        return "execute"

    return "fix_sql"


def check_execution(state: AgentState):
    if state["error"]:
        return check_retry(state)

    return "explain"


def check_retry(state: AgentState):
    if state["retry_count"] < 2:
        return "retry"

    return "stop"


builder = StateGraph(AgentState)

builder.add_node("generate_sql", generate_sql)
builder.add_node("validate_sql", validate_sql)
builder.add_node("execute_sql", execute_sql)
builder.add_node("create_dataframe", create_dataframe)
builder.add_node("fix_sql", fix_sql)
builder.add_node("explain_result", explain_result)

builder.add_edge(START, "generate_sql")
builder.add_edge("generate_sql", "validate_sql")


builder.add_conditional_edges(
    "validate_sql",
    check_validation,
    {
        "execute": "execute_sql",
        "fix_sql": END,
    }
)


builder.add_conditional_edges(
    "execute_sql",
    check_execution,
    {
        "retry": "fix_sql",
        "explain":"create_dataframe",
        "stop": END,
    }
)

builder.add_edge("create_dataframe","explain_result")
builder.add_edge("fix_sql", "validate_sql")

graph = builder.compile()