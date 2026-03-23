#  SQL Query Terminal

This project is a high-security SQL query and reporting tool. It is designed with a dual-layer defense: a Python-based regex filter and a database-level read-only user.

## 🖼️ Visual Overview

<table width="100%">
  <tr>
    <td width="50%" align="center"><b>Main Query Terminal</b></td>
    <td width="50%" align="center"><b>System Documentation</b></td>
  </tr>
  <tr>
    <td valign="top">
      <img src="./docs/screenshots/index.jpg" width="100%">
    </td>
    <td valign="top">
      <img src="./docs/screenshots/documentation.jpg" width="100%">
    </td>
  </tr>
  <tr>
    <td valign="top">
      <p align="center"><sub><em>The primary interface for executing read-only SQL queries with real-time regex filtering.</em></sub></p>
    </td>
    <td valign="top">
      <p align="center"><sub><em>Detailed internal documentation accessible to authorized administrative users.</em></sub></p>
    </td>
  </tr>
</table>

## 🧩 How this project works

### Purpose
- SQL Query Terminal is a secure, read-only query reporting tool.
- Users submit SQL through the web UI; backend applies strict validation and executes only safe read operations.
- Built for analytics with a strong dual-layer security model.

### Architecture
- `frontend/html/index.html`: main query UI (input + results)
- `frontend/html/documentation.html`: in-app system docs
- `backend/app.py`: FastAPI backend, query endpoint(s)
- `scripts/database_init.sql` & `scripts/default_database_population.sql`: schema + seed data
- `scripts/linux_setup.sh` and `scripts/run_app.sh`: environment setup and launch flow

### Security controls
- Python regex filter in `backend/app.py` blocks disallowed SQL keywords/commands (insert, update, delete, ddl, etc.).
- DB credentials use read-only role (`READONLY_CONFIG`).
- CORS should be locked to your app/ELB domain, not `["*"]`.
- PostgreSQL host-level control through `pg_hba.conf` enforcing local and restricted access.

### Query flow
1. User types SQL and submits in frontend.
2. Frontend calls API route, e.g. `/api/query`.
3. Backend:
   - normalizes and sanitizes query text
   - regex-checks for banned commands
   - executes via read-only DB user
   - returns results or clear error
4. Frontend renders query results table or message.

### Deployment guidance
- Keep `app.mount("/", ...)` at bottom of `backend/app.py` so `/api/*` routes are evaluated first.
- Replace hardcoded DB credentials with runtime secret fetch (Secrets Manager).
- Remove `--reload` in production.
- Run as systemd (or container) with process restart.

## 🔧 Tools & tech stack
- Python 3 + FastAPI
- Uvicorn/Gunicorn
- PostgreSQL
- HTML/CSS/JavaScript frontend
- Bash scripts
- regex-based SQL filtering
- `pg_hba.conf` DB host auth policy

## 🚀 Deployment Checklist

### 1. Code Adjustments (`app.py`)
* **Route Ordering:** The `app.mount("/", ...)` command MUST remain at the absolute bottom of the file to ensure API routes (`/api/...`) are evaluated first.
* **CORS Lockdown:** Replace `allow_origins=["*"]` with the specific internal DNS name or URL of your ELB.
* **Static Files:** Ensure the path in `StaticFiles(directory="../frontend")` correctly points to your frontend folder relative to the execution directory.

### 2. Database & Security
* **Secrets Management:** Integrate with your cloud provider's Secrets Manager. Replace hardcoded dictionaries (`READONLY_CONFIG` and `ADMIN_CONFIG`) with logic that fetches the rotated password and hostname at runtime.
* **Postgres Lockdown:** Update `pg_hba.conf` to ensure the database only accepts local connections, preventing any bypass of the application logic.

### 3. Process Management
* **Disable Dev Mode:** Ensure the `--reload` flag is removed from the startup command.
* **Systemd Service:** Create a service file to ensure the app starts on boot and restarts after crashes.

---

## 🛠️ Systemd Service Template

Create the file `/etc/systemd/system/insights.service`:

```ini
[Unit]
Description=Business Insights FastAPI Server
# Wait for the network and local database to be ready
After=network.target postgresql.service

[Service]
User=linux_service_user
Group=www-data
WorkingDirectory=/opt/business-insights/backend
# Bind to 0.0.0.0 so the ELB can reach the service
ExecStart=/usr/local/bin/gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
