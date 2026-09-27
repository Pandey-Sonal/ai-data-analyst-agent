def validate_sql(sql: str) -> bool:
    """
    Allow only read-only SELECT queries.
    """

    sql = sql.strip().lower()

    if not sql.startswith("select"):
        return False

    forbidden_keywords = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "truncate",
        "attach",
        "detach",
    ]

    for keyword in forbidden_keywords:
        if keyword in sql:
            return False

    return True
if __name__ == "__main__":

    safe_query = """
    SELECT COUNT(*)
    FROM orders;
    """

    dangerous_query = """
    DROP TABLE orders;
    """

    print("Safe query:", validate_sql(safe_query))
    print("Dangerous query:", validate_sql(dangerous_query))