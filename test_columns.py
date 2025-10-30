import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    dbname="etlserver_db",
    user="Aliyev_user",
    password="EtlpostgresBlack1002025Xyz"
)
cur = conn.cursor()
cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'bina_apartments';
""")
columns = [row[0] for row in cur.fetchall()]
print("Columns in bina_apartments:", columns)

cur.close()
conn.close()
