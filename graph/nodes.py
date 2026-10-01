import os
import sqlite3

import pandas as pd
import plotly.express as px

from dotenv import load_dotenv
from groq import Groq

from graph.state import AgentState


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found")

client = Groq(api_key=api_key)


# --------------------------------------------------
# Default Olist schema
# Used when no uploaded CSV is provided
# --------------------------------------------------

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
# 1. Check user request
# --------------------------------------------------

def check_user_request(state: AgentState):

    question = state["question"].lower()

    blocked_words = [
        "delete",
        "update",
        "insert",
        "drop",
        "alter",
        "truncate",
        "create",
        "replace",
        "modify",
        "change",
    ]

    for word in blocked_words:

        if word in question:

            return {
                "is_valid": False,
                "rejection_message": (
                    "This agent supports read-only analysis only. "
                    "Data modification operations such as DELETE, UPDATE, "
                    "and INSERT are not supported."
                )
            }

    return {
        "is_valid": True,
        "rejection_message": ""
    }


# --------------------------------------------------
# 2. Check schema
# --------------------------------------------------

def check_schema(state: AgentState):

    question = state["question"].lower()
    schema = state.get("schema", "")

    # -----------------------------------------
    # Extract column names from schema
    # -----------------------------------------

    columns = []

    for line in schema.splitlines():

        line = line.strip()

        if line.startswith("- "):

            column = (
                line[2:]
                .split("(")[0]
                .strip()
            )

            columns.append(column)

    # -----------------------------------------
    # Normalize question
    # -----------------------------------------

    question_text = (
        question
        .replace("_", " ")
        .replace("?", "")
        .replace(",", "")
        .replace(".", "")
    )

    # -----------------------------------------
    # Check specific requested fields
    # -----------------------------------------

    required_field_phrases = {
        "product name": "product_name",
        "customer name": "customer_name",
        "employee salary": "employee_salary",
        "stock level": "stock_level",
        "shipping cost": "shipping_cost",
    }

    for phrase, required_column in required_field_phrases.items():

        if phrase in question_text:

            if required_column not in columns:

                message = (
                    "I can't answer this question because "
                    "the uploaded dataset does not contain "
                    f"the '{required_column}' column."
                )

                return {
                    "schema_valid": False,
                    "schema_message": message,
                    "rejection_message": message
                }

    # -----------------------------------------
    # Create question words
    # -----------------------------------------

    question_words = set(
        question_text.split()
    )

    # Add singular versions
    normalized_question_words = set()

    for word in question_words:

        normalized_question_words.add(word)

        if word.endswith("ies"):

            normalized_question_words.add(
                word[:-3] + "y"
            )

        elif word.endswith("s"):

            normalized_question_words.add(
                word[:-1]
            )

    # -----------------------------------------
    # Common business-word mappings
    # -----------------------------------------

    aliases = {

        "product": ["product_id"],
        "products": ["product_id"],

        "customer": ["customer_id"],
        "customers": ["customer_id"],

        "quantity": ["quantity_sold"],
        "sold": ["quantity_sold"],

        "revenue": [
            "net_revenue",
            "gross_revenue"
        ],

        "profit": ["profit"],

        "price": ["unit_price"],

        "discount": [
            "discount_pct",
            "discount_amount"
        ],

        "sales": ["sales_id"],
    }

    # -----------------------------------------
    # Check whether question refers
    # to something in the dataset
    # -----------------------------------------

    matched = False

    for word in normalized_question_words:

        if word in aliases:

            possible_columns = aliases[word]

            if any(
                column in columns
                for column in possible_columns
            ):

                matched = True
                break

    # -----------------------------------------
    # Direct column-name matching
    # -----------------------------------------

    if not matched:

        for column in columns:

            normalized_column = (
                column.lower()
                .replace("_", " ")
            )

            if normalized_column in question_text:

                matched = True
                break

    # -----------------------------------------
    # Valid question
    # -----------------------------------------

    if matched:

        return {
            "schema_valid": True,
            "schema_message": ""
        }

    # -----------------------------------------
    # Invalid question
    # -----------------------------------------

    available_columns = ", ".join(columns)

    message = (
        "I can't answer this question because "
        "the uploaded dataset does not contain "
        "the required data. "
    )

    return {
        "schema_valid": False,
        "schema_message": message,
        "rejection_message": message
    }

def generate_sql(state: AgentState):

    question = state["question"]
    schema = state.get("schema", SCHEMA)

    prompt = f"""
You are a SQL expert.

Database schema:
{schema}

User question:
{question}

Generate exactly ONE SQLite SELECT query.

IMPORTANT:
- Use the exact column from the schema that matches the user's question.
- Do NOT substitute a different or related column.
- If the user says "stock level" and the schema contains "stock_level",
  you MUST use stock_level.
- If the user says "quantity sold", use quantity_sold.
- Column names must come directly from the provided schema.
- Never invent columns.
- Never use SELECT NULL.
- Never return NULL as a replacement for a required column.

Aggregation rules:
- average → AVG(column)
- total/sum → SUM(column)
- how many/count → COUNT(*) or COUNT(column)
- maximum/highest → MAX(column)
- minimum/lowest → MIN(column)
- grouped comparison → GROUP BY

For uploaded CSV data, use the table:
uploaded_data

Example:
Question: What is the average stock level?
If the schema contains stock_level, generate:
SELECT AVG(stock_level) AS average_stock_level FROM uploaded_data;

Return ONLY SQL.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    sql = response.choices[0].message.content.strip()

    if sql.startswith("```"):
        sql = sql.replace("```sql", "")
        sql = sql.replace("```", "")
        sql = sql.strip()

    return {
        "sql": sql
    }


# --------------------------------------------------
# 4. Validate SQL
# --------------------------------------------------


def validate_sql(state: AgentState):

    sql = state["sql"].strip()

    # Only SELECT queries are allowed
    if not sql.lower().startswith("select"):
        return {
            "is_valid": False,
            "rejection_message": "Only SELECT queries are allowed."
        }

    # Remove final semicolon
    sql = sql.rstrip(";").strip()

    # Prevent multiple SQL statements
    if ";" in sql:
        return {
            "is_valid": False,
            "rejection_message": "Multiple SQL statements are not allowed."
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
        "detach"
    ]

    sql_lower = sql.lower()

    for keyword in forbidden_keywords:
        if keyword in sql_lower:
            return {
                "is_valid": False,
                "rejection_message": f"Forbidden SQL operation: {keyword}"
            }

    return {
        "is_valid": True,
        "sql": sql
    }
# --------------------------------------------------
# 4. Execute SQL
# --------------------------------------------------

def execute_sql(state: AgentState):

    sql = state["sql"]

    # Use uploaded database if available.
    # Otherwise use Olist database.
    db_path = state.get(
        "db_path",
        "database/olist.db"
    )

    connection = sqlite3.connect(db_path)

    try:

        cursor = connection.cursor()

        cursor.execute(sql)

        result = cursor.fetchall()

        columns = [
            description[0]
            for description in cursor.description
        ]

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


# --------------------------------------------------
# 5. Create DataFrame
# --------------------------------------------------

def create_dataframe(state: AgentState):

    result = state["result"]

    columns = state["columns"]

    df = pd.DataFrame(
        result,
        columns=columns
    )

    return {
        "dataframe": df
    }


# --------------------------------------------------
# 6. Create Visualization
# --------------------------------------------------

def create_visualization(state: AgentState):
    import pandas as pd
    import plotly.express as px

    df = state.get("dataframe")

    if df is None or df.empty:
        return {"visualization": None}

    question = state["question"].lower()

    # --------------------------------------------------
    # Single value → KPI, no chart
    # --------------------------------------------------

    if df.shape == (1, 1):
        return {"visualization": None}

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()


    # --------------------------------------------------
    # Helper:
    # Identify ID/category columns
    # --------------------------------------------------

    def is_id_column(column):
        column_lower = column.lower()

        return (
            column_lower == "id"
            or column_lower.endswith("_id")
            or column_lower.endswith("id")
        )


    # --------------------------------------------------
    # 1. Questions asking "by", "each", "per"
    # → category comparison → BAR CHART
    # --------------------------------------------------

    comparison_words = [
        "by",
        "each",
        "per",
        "for each"
    ]

    if any(word in question for word in comparison_words):

        if len(df.columns) >= 2 and numeric_columns:

            # ------------------------------------------
            # Find category column
            # ------------------------------------------

            id_columns = [
                col
                for col in df.columns
                if is_id_column(col)
            ]

            if id_columns:

                category_column = id_columns[0]

            else:

                non_numeric_columns = [
                    col
                    for col in df.columns
                    if col not in numeric_columns
                ]

                if non_numeric_columns:

                    category_column = non_numeric_columns[0]

                else:

                    # Fallback
                    category_column = df.columns[0]


            # ------------------------------------------
            # Find measurement column
            # ------------------------------------------

            measurement_columns = [
                col
                for col in numeric_columns
                if col != category_column
            ]

            if not measurement_columns:
                return {"visualization": None}

            value_column = measurement_columns[-1]


            # ------------------------------------------
            # Prepare chart data
            # ------------------------------------------

            chart_df = df.copy()

            if len(chart_df) > 10:

                chart_df = chart_df.nlargest(
                    10,
                    value_column
                )


            # ------------------------------------------
            # Create bar chart
            # ------------------------------------------

            fig = px.bar(
                chart_df,
                x=category_column,
                y=value_column,
                title=(
                    f"{value_column.replace('_', ' ').title()} "
                    f"by "
                    f"{category_column.replace('_', ' ').title()}"
                )
            )

            return {
                "visualization": fig
            }


    # --------------------------------------------------
    # 2. Explicit date/time result → LINE CHART
    # --------------------------------------------------

    date_columns = [
        col
        for col in df.columns
        if any(
            word in col.lower()
            for word in [
                "date",
                "time",
                "datetime"
            ]
        )
    ]

    if date_columns and numeric_columns:

        date_column = date_columns[0]

        measurement_columns = [
            col
            for col in numeric_columns
            if col != date_column
        ]

        if not measurement_columns:
            return {"visualization": None}

        value_column = measurement_columns[-1]

        chart_df = df.copy()

        chart_df[date_column] = pd.to_datetime(
            chart_df[date_column],
            errors="coerce"
        )

        chart_df = chart_df.dropna(
            subset=[date_column]
        ).sort_values(
            date_column
        )

        if not chart_df.empty:

            fig = px.line(
                chart_df,
                x=date_column,
                y=value_column,
                title=(
                    f"{value_column.replace('_', ' ').title()} "
                    f"Over Time"
                )
            )

            return {
                "visualization": fig
            }


    # --------------------------------------------------
    # 3. Top / highest / lowest → BAR CHART
    # --------------------------------------------------

    if any(
        word in question
        for word in [
            "top",
            "highest",
            "lowest"
        ]
    ):

        if len(df.columns) >= 2 and numeric_columns:

            id_columns = [
                col
                for col in df.columns
                if is_id_column(col)
            ]

            if id_columns:

                category_column = id_columns[0]

            else:

                non_numeric_columns = [
                    col
                    for col in df.columns
                    if col not in numeric_columns
                ]

                if non_numeric_columns:

                    category_column = non_numeric_columns[0]

                else:

                    category_column = df.columns[0]


            measurement_columns = [
                col
                for col in numeric_columns
                if col != category_column
            ]

            if not measurement_columns:
                return {"visualization": None}

            value_column = measurement_columns[-1]

            chart_df = df.copy()

            # Top/highest → highest first
            if "lowest" not in question:

                chart_df = chart_df.sort_values(
                    value_column,
                    ascending=False
                )

            else:

                chart_df = chart_df.sort_values(
                    value_column,
                    ascending=True
                )

            if len(chart_df) > 10:

                chart_df = chart_df.head(10)

            fig = px.bar(
                chart_df,
                x=category_column,
                y=value_column,
                title=(
                    f"{value_column.replace('_', ' ').title()} "
                    f"by "
                    f"{category_column.replace('_', ' ').title()}"
                )
            )

            return {
                "visualization": fig
            }


    # --------------------------------------------------
    # 4. Two numeric measurements → SCATTER
    # --------------------------------------------------

    if len(numeric_columns) >= 2:

        # Remove ID columns from relationship charts
        # when possible.

        measurement_columns = [
            col
            for col in numeric_columns
            if not is_id_column(col)
        ]

        if len(measurement_columns) >= 2:

            x_column = measurement_columns[0]
            y_column = measurement_columns[1]

            fig = px.scatter(
                df,
                x=x_column,
                y=y_column,
                title=(
                    f"{y_column.replace('_', ' ').title()} "
                    f"vs "
                    f"{x_column.replace('_', ' ').title()}"
                )
            )

            return {
                "visualization": fig
            }

        # Fallback if both numeric columns are IDs
        # or only one actual measurement exists.

        fig = px.scatter(
            df,
            x=numeric_columns[0],
            y=numeric_columns[1],
            title=(
                f"{numeric_columns[1].replace('_', ' ').title()} "
                f"vs "
                f"{numeric_columns[0].replace('_', ' ').title()}"
            )
        )

        return {
            "visualization": fig
        }


    # --------------------------------------------------
    # 5. Nothing appropriate → no chart
    # --------------------------------------------------

    return {
        "visualization": None
    }

# --------------------------------------------------
# 7. Fix SQL after execution error
# --------------------------------------------------

def fix_sql(state: AgentState):

    question = state["question"]

    sql = state["sql"]

    error = state["error"]

    # Use current dataset schema
    schema = state.get(
        "schema",
        SCHEMA
    )

    prompt = f"""
You are a SQL debugging expert.

The following SQL query failed when executed.

User question:
{question}

Failed SQL:
{sql}

Database error:
{error}

Database schema:
{schema}

Generate a corrected SQLite SQL query.

Rules:
- Use only tables and columns from the provided schema.
- Do not invent tables.
- Do not invent columns.
- Return only SQL.
- Generate only one SELECT query.
- Do not modify the database.
- Use SQLite syntax.
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

    # Remove markdown SQL fences if present
    if corrected_sql.startswith("```sql"):
        corrected_sql = corrected_sql[6:]

    if corrected_sql.endswith("```"):
        corrected_sql = corrected_sql[:-3]

    corrected_sql = corrected_sql.strip()

    return {
        "sql": corrected_sql,
        "retry_count": state["retry_count"] + 1,
        "error": ""
    }


# --------------------------------------------------
# 8. Explain SQL result
# --------------------------------------------------

def explain_result(state: AgentState):

    question = state["question"]

    result = state["result"]

    columns = state["columns"]

    df = pd.DataFrame(
        result,
        columns=columns
    )

    # -----------------------------------------
    # Limit data sent to the LLM
    # -----------------------------------------

    total_rows = len(df)

    if total_rows > 10:

        sample_df = df.head(10)

        result_text = sample_df.to_string(
            index=False
        )

        result_text += (
            f"\n\nShowing first 10 rows "
            f"out of {total_rows} total rows."
        )

    else:

        result_text = df.to_string(
            index=False
        )

    # -----------------------------------------
    # Short explanation prompt
    # -----------------------------------------

    prompt = f"""
You are an AI Data Analyst.

User question:
{question}

Query result:
{result_text}

Give one short answer based ONLY on the query result.

Rules:
- Do not invent facts.
- Do not invent values.
- Do not invent currency symbols.
- Keep the answer concise.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You explain SQL results clearly "
                    "and accurately."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    explanation = (
        response.choices[0]
        .message.content
    )

    return {
        "explanation": explanation
    }