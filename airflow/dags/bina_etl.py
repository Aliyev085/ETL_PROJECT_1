#bina_etl.py file
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "/opt/Etl_server_project_1"
ENV = f"{PROJECT}/.env"
SRC = f"{PROJECT}/src/bina"
LOGS = f"{PROJECT}/logs"

DEFAULTS = {
    "owner": "Mahammad",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

# FINAL FIX — THIS PYTHON HAS SELENIUM INSTALLED
PYTHON = "/home/airflow/.local/bin/python3"

with DAG(
    dag_id="bina_etl",
    description="Bina.az ETL Pipeline (Selenium + RabbitMQ + Postgres)",
    default_args=DEFAULTS,
    schedule_interval="*/15 * * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
) as dag:

    fast = BashOperator(
        task_id="fast_scraper",
        bash_command=f"""
        cd {PROJECT}

        # Load .env variables
        set -o allexport
        source {ENV}
        set +o allexport

        export PYTHONPATH={PROJECT}/src
        mkdir -p {LOGS}

        echo "[AIRFLOW] Running FAST SCRAPER..."
        {PYTHON} {SRC}/listing_producer.py

        """,
    )

    # detail = BashOperator(
    #     task_id="detail_scraper",
    #     bash_command=f"""
    #     cd {PROJECT}

    #     # Load .env variables
    #     set -o allexport
    #     source {ENV}
    #     set +o allexport

    #     export PYTHONPATH={PROJECT}/src
    #     mkdir -p {LOGS}

    #     echo "[AIRFLOW] Running DETAIL SCRAPER..."
    #     {PYTHON} {SRC}/detail_scraper.py >> {LOGS}/airflow_detail_scraper.log 2>&1 || true

    #     exit 0
    #     """,
    # )

    analyze = BashOperator(
        task_id="db_analyze",
        bash_command=f"""
        cd {PROJECT}

        # Load .env variables
        set -o allexport
        source {ENV}
        set +o allexport

        {PYTHON} - << 'EOF'
import os, psycopg2
conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    port=os.environ["DB_PORT"],
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
)
cur = conn.cursor()
cur.execute("ANALYZE bina_apartments;")
conn.commit()
cur.close()
conn.close()
EOF

        exit 0
        """,
    )

    # fast >> detail >> analyze
    fast >> analyze
