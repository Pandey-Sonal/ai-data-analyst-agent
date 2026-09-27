import os
import sqlite3
import pandas as pd

from dotenv import load_dotenv
from groq import Groq

from graph.state import AgentState


# Load environment variables
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found")

client = Groq(api_key=api_key)


# Database schema given to the LLM
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


# --------------------------------------------------
# 1. Generate SQL
# --------------------------------------------------

def generate_sql(state: AgentState):
    question = state["question"]

    prompt = f"""
You are a SQL expert and data analyst.

Generate a SQLite SQL query to answer the user's question.

Use ONLY the tables and columns provided below.

Schema:
{SCHEMA}

Important business meanings:
- "delivered orders" means orders where order_status = 'delivered'.
- "customer state" means customers.customer_state.
- "seller state" means sellers.seller_state.
- "product price" means order_items.price.
- "freight" or "shipping cost" means order_items.freight_value.
- order_items.price and payments.payment_value are different metrics.
- Do not invent columns or tables.
- If the question asks for revenue and does not define it, use SUM(order_items.price) as the default revenue metric.
- Use JOINs when information is stored in different tables.

User question:
{question}

Rules:
- Return only SQL.
- Generate only SELECT queries.
- Do not modify the database.
- Use SQLite syntax.
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

    sql = response.choices[0].message.content.strip()

    print("\nGenerated SQL:")
    print(sql)

    return {
        "sql": sql
    }


# --------------------------------------------------
# 2. Validate SQL
# --------------------------------------------------

def validate_sql(state: AgentState):
    sql = state["sql"].strip().lower()

    # Query must start with SELECT
    if not sql.startswith("select"):
        return {
            "is_valid": False
        }

    # Remove one final semicolon
    sql = sql.rstrip(";").strip()

    # Reject multiple SQL statements
    if ";" in sql:
        return {
            "is_valid": False
        }

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
            return {
                "is_valid": False
            }

    return {
        "is_valid": True
    }


# --------------------------------------------------
# 3. Execute SQL
# --------------------------------------------------
def execute_sql(state: AgentState):
    sql = state["sql"]

    connection = sqlite3.connect("database/olist.db")

    try:
        cursor = connection.cursor()

        cursor.execute(sql)

        result = cursor.fetchall()

        columns = [description[0] for description in cursor.description]

        return {
            "result": result,
            "columns": columns,
            "error": ""
        }

    except Exception as e:
        return {
            "result": [],
            "columns": [],
            "error": str(e)
        }

    finally:
        connection.close()

def create_dataframe(state: AgentState):
    result = state["result"]
    columns = state["columns"]

    df = pd.DataFrame(result, columns=columns)

    print("\nDataFrame:")
    print(df)

    return {
        "dataframe": df
    }
# --------------------------------------------------
# 4. Fix SQL after execution error
# --------------------------------------------------

def fix_sql(state: AgentState):
    question = state["question"]
    sql = state["sql"]
    error = state["error"]

    prompt = f"""
You are a SQL debugging expert.

The following SQL query failed when executed.

User question:
{question}

Failed SQL:
{sql}

Database error:
{error}

Schema:
{SCHEMA}

Generate a corrected SQLite SQL query.

Rules:
- Use only the provided schema.
- Return only SQL.
- Generate only SELECT queries.
- Do not modify the database.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": "You fix SQL queries based on database errors."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    corrected_sql = response.choices[0].message.content.strip()

    print("\nCorrected SQL:")
    print(corrected_sql)

    return {
        "sql": corrected_sql,
        "retry_count": state["retry_count"] + 1,
        "error": ""
    }


# --------------------------------------------------
# 5. Explain SQL result
# --------------------------------------------------

def explain_result(state: AgentState):
    question = state["question"]
    sql = state["sql"]
    result = state["result"]

    prompt = f"""
You are a data analyst.

Answer the user's question using the SQL result.

User question:
{question}

SQL query:
{sql}

SQL result:
{result}

Rules:
- Give a clear, concise business answer.
- Use only the information in the SQL result.
- Do not invent facts.
- Do not include SQL unless necessary.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": "You explain database results clearly."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    explanation = response.choices[0].message.content.strip()

    return {
        "explanation": explanation
    }