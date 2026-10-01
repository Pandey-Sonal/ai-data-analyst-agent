from langgraph.graph import StateGraph, START, END

from graph.state import AgentState

from graph.nodes import (
    check_user_request,
    check_schema,
    generate_sql,
    validate_sql,
    execute_sql,
    create_dataframe,
    create_visualization,
    fix_sql,
    explain_result,
)


def check_user_request_route(state: AgentState):
    if state["is_valid"]:
        return "check_schema"

    return "reject"


def check_schema_route(state: AgentState):
    if state["schema_valid"]:
        return "generate_sql"

    return "reject"


def check_validation(state: AgentState):
    if state["is_valid"]:
        return "execute"

    return "stop"


def check_execution(state: AgentState):
    if state["error"]:
        return check_retry(state)

    return "success"


def check_retry(state: AgentState):
    if state["retry_count"] < 2:
        return "retry"

    return "stop"


# Create graph
builder = StateGraph(AgentState)


# Add nodes
builder.add_node("check_user_request", check_user_request)
builder.add_node("check_schema", check_schema)
builder.add_node("generate_sql", generate_sql)
builder.add_node("validate_sql", validate_sql)
builder.add_node("execute_sql", execute_sql)
builder.add_node("create_dataframe", create_dataframe)
builder.add_node("create_visualization", create_visualization)
builder.add_node("fix_sql", fix_sql)
builder.add_node("explain_result", explain_result)


# START → User request check
builder.add_edge(
    START,
    "check_user_request"
)


# User request check → Schema check OR reject
builder.add_conditional_edges(
    "check_user_request",
    check_user_request_route,
    {
        "check_schema": "check_schema",
        "reject": END,
    }
)


# Schema check → Generate SQL OR reject
builder.add_conditional_edges(
    "check_schema",
    check_schema_route,
    {
        "generate_sql": "generate_sql",
        "reject": END,
    }
)


# Generate SQL → Validate SQL
builder.add_edge(
    "generate_sql",
    "validate_sql"
)


# Validate SQL → Execute OR Stop
builder.add_conditional_edges(
    "validate_sql",
    check_validation,
    {
        "execute": "execute_sql",
        "stop": END,
    }
)


# Execute SQL → Retry OR DataFrame OR Stop
builder.add_conditional_edges(
    "execute_sql",
    check_execution,
    {
        "retry": "fix_sql",
        "success": "create_dataframe",
        "stop": END,
    }
)


# Fix SQL → Validate again
builder.add_edge(
    "fix_sql",
    "validate_sql"
)


# DataFrame → Visualization
builder.add_edge(
    "create_dataframe",
    "create_visualization"
)


# Visualization → Explanation
builder.add_edge(
    "create_visualization",
    "explain_result"
)


# Explanation → END
builder.add_edge(
    "explain_result",
    END
)


# Compile graph
graph = builder.compile()