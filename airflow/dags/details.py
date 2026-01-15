from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from airflow import DAG

# Number of DAGs you want
SCRAPER_COUNT = 2

for i in range(1, SCRAPER_COUNT + 1):
    dag_id = f"detail_scraper_singleton_{i}"

    default_args = {
        "owner": "airflow",
        "depends_on_past": False,
        "retries": 0,
    }

    dag = DAG(
        dag_id=dag_id,
        default_args=default_args,
        start_date=datetime(2025, 1, 1),
        schedule_interval="* * * * *",  # every minute
        catchup=False,
        max_active_runs=1,
    )

    with dag:
        BashOperator(
            task_id=f"run_detail_scraper_{i}",
            bash_command=f"python /opt/Etl_server_project_1/src/bina/detail_scraper.py",
            execution_timeout=timedelta(hours=1),
            task_concurrency=1,
        )

    globals()[dag_id] = dag
