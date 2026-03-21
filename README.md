# Business Insights | Database Viewer

A full-stack internal tool for executing and saving read-only SQL queries against a PostgreSQL production environment.

## 📂 Project Structure
- **backend/**: FastAPI server (`app.py`) handling SQL execution and Excel exports.
- **frontend/**: UI components (`index.html`) and documentation (`documentation.html`).
- **scripts/**: Automation scripts for environment setup and database initialization.

## 🚀 Quick Start (WSL/Linux)

### 1. Initial Setup
Run the setup script to install dependencies, create the database, and seed initial data.
```bash
chmod +x scripts/linux_setup.sh
./scripts/linux_setup.sh