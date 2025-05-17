#!/bin/bash
CURRENT_DIR=$(dirname "$(realpath "$0")")
PROJECT_DIR=$(dirname "$CURRENT_DIR")

VENV_PATH="$PROJECT_DIR/venv/venv_main/bin/activate"
PYTHON_SCRIPT_PATH="$CURRENT_DIR/feed_mongodb_flights.py"

source "$VENV_PATH"
python3 "$PYTHON_SCRIPT_PATH"
deactivate