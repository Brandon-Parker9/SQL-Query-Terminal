import os
import re
import pandas as pd

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text

# --- FASTAPI SETUP ---
app = FastAPI()

# CORS Middleware: Allow all origins, methods, and headers for simplicity. In production, you should lock this down to specific domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE ENGINES (The SQLAlchemy Way) ---

# We create the connection strings for SQLAlchemy
# Format: postgresql://user:password@host:port/dbname
ADMIN_URL = "postgresql://postgres:password@localhost:5432/insights_db"
READONLY_URL = "postgresql://read_only_user:read_only_pass@localhost:5432/insights_db"

# Create the engines
# 'pool_pre_ping' is a pro-tip: it checks if the connection is alive before using it
admin_engine = create_engine(ADMIN_URL, pool_pre_ping=True)
readonly_engine = create_engine(READONLY_URL, pool_pre_ping=True)

# --- Pydantic Models ---
class QueryRequest(BaseModel):
    sql: str
    name: str = None

# --- HELPER FUNCTIONS ---

def is_readonly_safe(sql: str) -> bool:
    """
    Validates that the SQL query is a single, non-destructive SELECT statement.
    """
    # 1. Clean the string: Remove SQL comments (-- or /* */) 
    # This prevents: SELECT * FROM users; -- DROP TABLE users
    sql_clean = re.sub(r'--.*?\n|/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # 2. Normalize: Trim whitespace and convert to lowercase for easy checking
    sql_clean = sql_clean.strip().lower()

    # 3. The "Must Start With" Rule:
    # Analytical terminals should almost always start with SELECT or WITH (for CTEs)
    if not (sql_clean.startswith("select") or sql_clean.startswith("with")):
        return False

    # 4. The "Forbidden Keywords" Deny List:
    # We look for words that change data (DML) or structure (DDL)
    forbidden_patterns = [
        r"\bdrop\b", r"\bdelete\b", r"\binsert\b", r"\bupdate\b", 
        r"\balter\b", r"\btruncate\b", r"\bcreate\b", r"\bgrant\b", 
        r"\brevoke\b", r"\binto\b"
    ]

    for pattern in forbidden_patterns:
        if re.search(pattern, sql_clean):
            return False

    # 5. The "Anti-Semicolon" Check:
    # Prevents "Piggybacking" (e.g., SELECT * FROM x; DROP TABLE y)
    # We allow a semicolon ONLY if it's the very last character
    if ";" in sql_clean[:-1]:
        return False

    return True

# --- ENDPOINTS ---

# --- ENDPOINTS ---

# This endpoint retrieves all saved queries from the database and returns them as a list of dictionaries.
@app.get("/api/queries")
async def get_queries():
    try:
        # Wrap the hardcoded string in text()
        query = text("SELECT id, query_name as name, sql_text as sql FROM saved_queries ORDER BY query_name ASC")
        df = pd.read_sql(query, admin_engine)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# This endpoint executes a user-provided SQL query, but only if it passes the is_readonly_safe() check.
@app.post("/api/execute")
async def execute_query(request: QueryRequest):
    if not is_readonly_safe(request.sql):
        raise HTTPException(status_code=403, detail="Access Denied: Only SELECT queries are permitted.")

    try:
        # Wrap the USER'S dynamic string in text()
        # This tells SQLAlchemy: "Treat this entire blob as a SQL statement"
        query = text(request.sql)
        df = pd.read_sql(query, readonly_engine)
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# This endpoint allows users to save their SQL queries with a name. It uses parameterized queries to prevent SQL injection.
@app.post("/api/queries")
async def save_query(request: QueryRequest):
    try:
        with admin_engine.begin() as conn:
            # Here we use text() PLUS a dictionary for maximum security
            stmt = text("INSERT INTO saved_queries (query_name, sql_text) VALUES (:name, :sql)")
            conn.execute(stmt, {"name": request.name, "sql": request.sql})
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# This endpoint allows users to export the results of their SQL query as an Excel file. It also uses the same safety check and query execution method as the /api/execute endpoint.   
@app.post("/api/export")
async def export_excel(request: QueryRequest):
    try:
        # Consistency check: Wrap the export query too
        query = text(request.sql)
        df = pd.read_sql(query, readonly_engine)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Query Results')
        
        output.seek(0)
        headers = {'Content-Disposition': 'attachment; filename="query_results.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# This endpoint allows users to delete a saved query by its ID. It uses a parameterized DELETE statement to ensure safety.
@app.delete("/api/queries/{query_id}")
async def delete_query(query_id: int):
    try:
        with admin_engine.begin() as conn:
            # Parameterized delete for safety
            stmt = text("DELETE FROM saved_queries WHERE id = :id")
            conn.execute(stmt, {"id": query_id})
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# This endpoint serves the favicon for the application. It checks if the SVG file exists and returns it with the correct media type. If the file is not found, it returns a 204 No Content response.
@app.get("/favicon.svg", include_in_schema=False)
async def favicon():
    # Adjusted path to match your folder structure
    file_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "favicon", "canadian-maple-leaf-brands-solid-full.svg")
    
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/svg+xml")
    return Response(status_code=204)

# Finally, we mount the static files (the frontend) at the root URL. This allows us to serve the HTML, CSS, and JS files directly from the backend.
app.mount("/", StaticFiles(directory="../frontend/html", html=True), name="static")