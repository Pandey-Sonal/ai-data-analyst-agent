import os
import sqlite3

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found")

client = Groq(api_key=api_key)

DB_PATH = "database/olist.db"


SCHEMA = """
Table: orders
Columns:
- order_id
- customer_id
- order_status
- order_purchase_timestamp
- order_approved_at
- order_delivered_carrier_date
- order_delivered_customer_date
- order_estimated_delivery_date

Table: order_items
Columns:
- order_id
- order_item_id
- product_id
- seller_id
- shipping_limit_date
- price
- freight_value

Table: products
Columns:
- product_id
- product_category_name
- product_name_lenght
- product_description_lenght
- product_photos_qty
- product_weight_g
- product_length_cm
- product_height_cm
- product_width_cm

Table: customers
Columns:
- customer_id
- customer_unique_id
- customer_zip_code_prefix
- customer_city
- customer_state

Table: sellers
Columns:
- seller_id
- seller_zip_code_prefix
- seller_city
- seller_state

Table: payments
Columns:
- order_id
- payment_sequential
- payment_type
- payment_installments
- payment_value

Table: reviews
Columns:
- review_id
- order_id
- review_score
- review_comment_title
- review_comment_message
- review_creation_date
- review_answer_timestamp
"""


def generate_sql(question: str) -> str:

    prompt = f"""
You are a SQL expert.

Generate a SQLite SQL query to answer the user's question.

Use ONLY the tables and columns provided below.

Schema:
{SCHEMA}

User question:
{question}

Rules:
- Return only SQL.
- Generate only SELECT queries.
- Do not modify the database.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": "You generate accurate SQLite SQL queries."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()


def validate_sql(sql: str) -> bool:

    sql_lower = sql.lower().strip()

    if not sql_lower.startswith("select"):
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
        "detach"
    ]

    for keyword in forbidden_keywords:
        if keyword in sql_lower:
            return False

    return True


def execute_query(sql: str):

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(sql)

    result = cursor.fetchall()

    connection.close()

    return result


if __name__ == "__main__":

    question = "Which product category generated the highest revenue?"

    sql = generate_sql(question)

    print("\nGenerated SQL:")
    print(sql)

    if not validate_sql(sql):
        raise ValueError("Unsafe SQL query rejected.")

    result = execute_query(sql)

    print("\nResult:")
    print(result)