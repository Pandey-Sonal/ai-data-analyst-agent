import sqlite3
from pathlib import Path

import pandas as pd


# Project folders
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_DIR = BASE_DIR / "database"

DB_PATH = DATABASE_DIR / "olist.db"


connection = sqlite3.connect(DB_PATH)


files = {
    "olist_customers_dataset.csv": "customers",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "olist_order_payments_dataset.csv": "payments",
    "olist_order_reviews_dataset.csv": "reviews",
}


# Load each CSV into SQLite
for filename, table_name in files.items():

    file_path = DATA_DIR / filename

    df = pd.read_csv(file_path)

    df.to_sql(
        table_name,
        connection,
        if_exists="replace",
        index=False
    )

    print(f"Loaded {table_name}: {len(df)} rows")


connection.close()

print(f"\nDatabase created: {DB_PATH}")