import psycopg2

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        dbname="etlserver_db",
        user="Aliyev_user",
        password="EtlpostgresBlack1002025Xyz"
    )

    cur = conn.cursor()
    cur.execute("SELECT * FROM bina_apartments LIMIT 1;")
    result = cur.fetchall()
    print("Connection successful! Sample row:", result)

except Exception as e:
    print("Connection failed:", e)

finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()
