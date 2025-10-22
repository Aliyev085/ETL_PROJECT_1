#!/bin/bash
set -e

PROJECT_DIR="/opt/Etl_server_project_1"
VENV_PYTHON="$PROJECT_DIR/etl/venv/bin/python"
LOG_FILE="$PROJECT_DIR/logs/cron.log"

mkdir -p "$(dirname "$LOG_FILE")"

# Run the main scraper every 30 minutes
cd "$PROJECT_DIR"
"$VENV_PYTHON" "$PROJECT_DIR/src/main.py" --initial >> "$LOG_FILE" 2>&1
