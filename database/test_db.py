import sqlite3

connection = sqlite3.connect("database/olist.db")

cursor = connection.cursor()

cursor.execute("""
    SELECT order_status, COUNT(*)
    FROM orders
    GROUP BY order_status;
""")

results = cursor.fetchall()

for row in results:
    print(row)

connection.close()