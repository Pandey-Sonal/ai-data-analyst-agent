import sqlite3

DB_PATH = "database/olist.db"


def execute_query(sql: str):
    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(sql)

    result = cursor.fetchall()

    connection.close()

    return result
if __name__ == "__main__":

    sql = """
    SELECT COUNT(*)
    FROM orders;
    """

    result = execute_query(sql)

    print(result)