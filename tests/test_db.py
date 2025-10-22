import os
from dotenv import load_dotenv
import psycopg

# Load variables from .env in the same folder
load_dotenv()

# Connect using your updated credentials
conn = psycopg.connect(
    host="127.0.0.1",   # since we're outside Docker but still on the same server
    port=os.getenv("POSTGRES_PORT", "5432"),
    dbname=os.getenv("POSTGRES_DB", "etlserver_db"),
    user=os.getenv("POSTGRES_USER", "Aliyev_user"),
    password=os.getenv("POSTGRES_PASSWORD", "EtlpostgresBlack1002025Xyz")
)

with conn:
    with conn.cursor() as cur:
        # Create a table if it doesn’t exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                price NUMERIC(10,2),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Insert sample row
        cur.execute("INSERT INTO listings (title, price) VALUES (%s, %s)", ("hello world", 9.99))
        # Fetch last 3 rows
        cur.execute("SELECT id, title, price, created_at FROM listings ORDER BY id DESC LIMIT 3")
        rows = cur.fetchall()
        print("Recent rows:", rows)

print("Success!")
