#!/bin/bash
export PYTHONPATH=/opt/Etl_server_project_1/src
export DB_HOST=127.0.0.1
export DB_NAME=etlserver_db
export DB_USER=Aliyev_user
export DB_PASSWORD=Aliyev_password

cd /opt/Etl_server_project_1/src
exec /opt/Etl_server_project_1/etl/venv/bin/python -u -m bina.scraper_each_item
