import os
import re
import pandas as pd
import logging

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from pydantic import BaseModel, Field
from io import BytesIO

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    # SQL is required
    sql: str = Field(
        ..., 
        min_length=1, 
        max_length=5000, 
        description="SQL query must be between 1 and 5000 characters."
    )
    
    # Name is now optional. If provided, it must follow the length rules.
    name: str = Field(
        None, 
        min_length=1, 
        max_length=200, 
        description="Optional name, must be between 1 and 200 characters if provided."
    )

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

# -- Exception Handler for Pydantic Validation Errors --

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    # This grabs the specific error from Pydantic (e.g., "String too long")
    errors = exc.errors()
    error_messages = []
    
    for error in errors:
        # Pydantic returns a list of errors. We'll format them cleanly.
        field = error.get("loc")[-1]
        msg = error.get("msg")
        error_messages.append(f"{field.upper()}: {msg}")

    # We join them together and send a 400 (Bad Request) instead of 422
    return JSONResponse(
        status_code=400,
        content={"detail": " / ".join(error_messages)},
    )

# --- ENDPOINTS ---

# This endpoint retrieves all saved queries from the database and returns them as a list of dictionaries.
@app.get("/api/queries", tags=["Saved Queries Operations"])
async def get_queries():
    try:
        logger.info("Retrieving all saved queries")

        # Wrap the hardcoded string in text()
        query = text("SELECT id, query_name as name, sql_text as sql FROM saved_queries ORDER BY query_name ASC")
        df = pd.read_sql(query, readonly_engine)
        
        logger.info(f"Retrieved {len(df)} saved queries")
        
        return df.to_dict(orient="records")
    
    except Exception as e:
        
        logger.error(f"Error retrieving queries: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# This endpoint allows users to save their SQL queries with a name. It uses parameterized queries to prevent SQL injection.
@app.post("/api/queries", tags=["Saved Queries Operations"])
async def save_query(request: QueryRequest):
    try:
        
        logger.info(f"Saving query with name: {request.name}")
        
        with admin_engine.begin() as conn:
            # Here we use text() PLUS a dictionary for maximum security
            stmt = text("INSERT INTO saved_queries (query_name, sql_text) VALUES (:name, :sql)")
            conn.execute(stmt, {"name": request.name, "sql": request.sql})
        
        logger.info(f"Query '{request.name}' saved successfully")
        return {"status": "success"}
    
    except Exception as e:
        
        logger.error(f"Error saving query '{request.name}': {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save query")

# This endpoint allows users to delete a saved query by its ID. It uses a parameterized DELETE statement to ensure safety.
@app.delete("/api/queries/{query_id}", tags=["Saved Queries Operations"])
async def delete_query(query_id: int):
    try:
        logger.info(f"Deleting query with ID: {query_id}")
        with admin_engine.begin() as conn:
            # Parameterized delete for safety
            stmt = text("DELETE FROM saved_queries WHERE id = :id")
            result = conn.execute(stmt, {"id": query_id})
        if result.rowcount > 0:
            logger.info(f"Query ID {query_id} deleted successfully")
            return {"status": "deleted"}
        else:
            logger.warning(f"Query ID {query_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Query not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting query ID {query_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete query")

# This endpoint executes a user-provided SQL query, but only if it passes the is_readonly_safe() check.
@app.post("/api/execute", tags=["Query Execution"])
async def execute_query(request: QueryRequest):
    if not is_readonly_safe(request.sql):

        logger.warning(f"Blocked unsafe query execution attempt: {request.sql[:100]}...")
        raise HTTPException(status_code=403, detail="Access Denied: Only SELECT queries are permitted.")

    try:
        logger.info(f"Executing query: {request.sql[:100]}...")
        
        # Wrap the USER'S dynamic string in text()
        # This tells SQLAlchemy: "Treat this entire blob as a SQL statement"
        query = text(request.sql)
        df = pd.read_sql(query, readonly_engine)
        
        logger.info(f"Query executed successfully, returned {len(df)} rows")
        
        return {"data": df.to_dict(orient="records")}
    
    except Exception as e:
        
        logger.error(f"Error executing query: {str(e)}")
        raise HTTPException(status_code=400, detail="Query execution failed")

# This endpoint allows users to export the results of their SQL query as an Excel file. It also uses the same safety check and query execution method as the /api/execute endpoint.   
@app.post("/api/export", tags=["Query Export"])
async def export_excel(request: QueryRequest):
    if not is_readonly_safe(request.sql):
        logger.warning(f"Blocked unsafe export attempt: {request.sql[:100]}...")
        raise HTTPException(status_code=403, detail="Access Denied: Only SELECT queries are permitted.")

    try:
        logger.info(f"Exporting query results: {request.sql[:100]}...")
        
        # Consistency check: Wrap the export query too
        query = text(request.sql)
        df = pd.read_sql(query, readonly_engine)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Query Results')
        
        output.seek(0)
        
        logger.info(f"Query exported successfully, {len(df)} rows in Excel file")
        headers = {'Content-Disposition': 'attachment; filename="query_results.xlsx"'}
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    except Exception as e:
        
        logger.error(f"Error exporting query: {str(e)}")
        raise HTTPException(status_code=400, detail="Export failed")

# Finally, we mount the static files (the frontend) at the root URL. This allows us to serve the HTML, CSS, and JS files directly from the backend.
# Mount the entire frontend folder so JS, CSS, and Favicons are all accessible
frontend_base = os.path.join(os.path.dirname(__file__), "..", "frontend")

# This handles the /js, /css, and /favicon paths
app.mount("/static", StaticFiles(directory=frontend_base), name="static")

# This specifically handles the root / and index.html
app.mount("/", StaticFiles(directory=os.path.join(frontend_base, "html"), html=True), name="html")