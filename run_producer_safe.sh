#!/bin/bash
set -e
cd /opt/Etl_server_project_1
source etl/venv/bin/activate
export PYTHONPATH=/opt/Etl_server_project_1/src
export $(grep -v '^#' .env | xargs)

# Mark that producer started
echo "producer_start at $(date '+%Y-%m-%d %H:%M:%S')" > /tmp/etl_heartbeat

# Run producer with a 20-minute timeout
timeout 20m python -m bina.producer && \
  echo "producer_ok at $(date '+%Y-%m-%d %H:%M:%S')" > /tmp/etl_heartbeat || \
  echo "producer_fail at $(date '+%Y-%m-%d %H:%M:%S')" > /tmp/etl_heartbeat
