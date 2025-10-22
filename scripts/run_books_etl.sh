#!/usr/bin/env bash
set -euo pipefail
cd /opt/Etl_server_project_1
source .venv/bin/activate
python etl/books_selenium_etl.py >> /opt/Etl_server_project_1/logs/books_etl.log 2>&1
