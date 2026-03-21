from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from fastapi.responses import StreamingResponse
import re
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Postgres Connection Parameters
# For SELECTing data
READONLY_CONFIG = {
    "dbname": "insights_db",
    "user": "read_only_user",
    "password": "read_only_pass",
    "host": "localhost",
    "port": "5432",
    "sslmode": "require"
}

# For SAVING/DELETING queries (Postgres admin)
ADMIN_CONFIG = {
    "dbname": "insights_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432",
    "sslmode": "require"
}

class QueryRequest(BaseModel):
    sql: str
    name: str = None

# --- HELPER FUNCTIONS ---

def is_safe_sql(sql: str) -> bool:
    # 1. Convert to uppercase for checking
    sql_upper = sql.strip().upper()
    
    # 2. Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return False
    
    # 3. Block "Blacklisted" destructive words
    # We use \b to ensure we match the whole word (so "Droplet" isn't blocked)
    forbidden_words = [r"\bDROP\b", r"\bDELETE\b", r"\bTRUNCATE\b", r"\bUPDATE\b", r"\bINSERT\b", r"\bALTER\b"]
    
    for word in forbidden_words:
        if re.search(word, sql_upper):
            return False
            
    return True

# --- ENDPOINTS ---

@app.post("/api/execute")
async def execute_query(request: QueryRequest):
    # THE GATEKEEPER
    if not is_safe_sql(request.sql):
        raise HTTPException(status_code=403, detail="Access Denied: Only SELECT queries are permitted.")

    try:
        conn = psycopg2.connect(**READONLY_CONFIG)
        df = pd.read_sql(request.sql, conn)
        conn.close()
        return {"data": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/queries")
async def get_queries():
    try:
        conn = psycopg2.connect(**ADMIN_CONFIG)
        # Added ORDER BY created_at DESC so the newest ones are at the top
        df = pd.read_sql("SELECT id, query_name as name, sql_text as sql FROM saved_queries ORDER BY query_name ASC", conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/queries")
async def save_query(request: QueryRequest):
    try:
        conn = psycopg2.connect(**ADMIN_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO saved_queries (query_name, sql_text) VALUES (%s, %s)",
            (request.name, request.sql)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/queries/{query_id}")
async def delete_query(query_id: int):
    try:
        conn = psycopg2.connect(**ADMIN_CONFIG)
        cur = conn.cursor()
        cur.execute("DELETE FROM saved_queries WHERE id = %s", (query_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/export")
async def export_excel(request: QueryRequest):
    try:
        conn = psycopg2.connect(**READONLY_CONFIG)
        df = pd.read_sql(request.sql, conn)
        conn.close()

        # Create an in-memory buffer for the Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Query Results')
        
        output.seek(0)

        # Return the file as a stream
        headers = {
            'Content-Disposition': 'attachment; filename="query_results.xlsx"'
        }
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# THIS MUST BE AT THE BOTTOM OF THE FILE
# Mount the frontend directory to serve static files
# 'directory' points to your frontend folder relative to app.py
# 'html=True' automatically looks for index.html when you visit the root URL
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")