import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found")

client = Groq(api_key=api_key)


schema = """
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
"""


question = "Which product category generated the highest revenue?"


prompt = f"""
You are a SQL expert.

Generate a SQLite SQL query to answer the user's question.

Use only the tables and columns provided in the schema.

Schema:
{schema}

User question:
{question}

Return only the SQL query.
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


sql = response.choices[0].message.content

print("Generated SQL:")
print(sql)