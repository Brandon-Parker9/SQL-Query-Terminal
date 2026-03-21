#!/bin/bash

# Get the root directory of the project
PROJECT_ROOT=$(dirname "$(dirname "$(readlink -f "$0")")")

# 1. Ensure Postgres is running (WSL often stops it)
sudo service postgresql start

# 2. Navigate to the backend folder
cd "$PROJECT_ROOT/backend"

# 3. Start the FastAPI server
echo "Starting Business Insights Server at http://localhost:8000"
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000