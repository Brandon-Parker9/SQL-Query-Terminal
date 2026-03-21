#!/bin/bash

# --- 1. SYSTEM INSTALLS ---
sudo apt update
sudo apt install postgresql postgresql-contrib python3 python3-pip -y
sudo service postgresql start

# --- 2. PYTHON PACKAGES ---
pip install fastapi uvicorn pandas psycopg2-binary openpyxl --break-system-packages

# --- 3. DATABASE CREATION (Shell Level) ---
# Set admin password
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'password';"

# Create DB if it doesn't exist
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='insights_db'")
if [ "$DB_EXISTS" != "1" ]; then
    sudo -u postgres psql -c "CREATE DATABASE insights_db;"
fi

# --- 4. RUN SQL DEFINITIONS ---
# Get the directory where this script is located
SCRIPT_DIR=$(dirname "$(readlink -f "$0")") # More robust path detection

echo "Initializing database structure..."
sudo -u postgres psql -d insights_db -f "$SCRIPT_DIR/database_init.sql"

echo "Populating default data..."
sudo -u postgres psql -d insights_db -f "$SCRIPT_DIR/default_database_population.sql"

echo "------------------------------------------------"
echo "✅ Environment & Database Re-initialized!"
echo "------------------------------------------------"