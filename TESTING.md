# 🛡️ Security & Regression Testing Suite

This document provides a standardized set of test cases to verify the **Business Insights Query Terminal** security layers. These tests ensure that the "Gatekeeper" (Python Regex) and the "Safety Net" (Postgres Permissions) are functioning as expected.

## 1. Automated/Manual Test Cases

### Category A: Application Layer (The Gatekeeper)
**Expected Result:** `403 Forbidden`  
**Error Detail:** "Error: Access Denied: Only SELECT queries are permitted."

| Test ID | SQL Input | Logic Tested |
| :--- | :--- | :--- |
| **G-01** | `DELETE FROM saved_queries;` | Basic DML Block (Delete) |
| **G-02** | `DROP TABLE users;` | Basic DDL Block (Drop) |
| **G-03** | `UPDATE sales SET amount = 0;` | Basic DML Block (Update) |
| **G-04** | `SELECT * FROM users; DROP TABLE users;` | Multi-statement (Semicolon) |
| **G-05** | `SELECT * FROM users --; DROP TABLE users` | Comment-hidden Injection |
| **G-06** | `/* comment */ DROP TABLE users;` | Comment-prefixed Attack |
| **G-07** | `INSERT INTO saved_queries (name) VALUES ('X');` | Data Entry Block |
| **G-08** | `ALTER TABLE users ADD COLUMN password text;` | Schema Modification Block |
| **G-09** | `TRUNCATE TABLE logs;` | High-speed Deletion Block |
| **G-10** | `EXECUTE my_stored_procedure();` | Procedure Execution Block |

### Category B: Database Layer (The Safety Net)
**Expected Result:** `403 Forbidden`  
**Error Detail:** "Error: Access Denied: Only SELECT queries are permitted."

| Test ID | SQL Input | Logic Tested |
| :--- | :--- | :--- |
| **D-01** | `SELECT * FROM (UPDATE users SET id=1 RETURNING *) as t;` | CTE/Subquery Write attempt |
| **D-02** | `SELECT * INTO new_table FROM users;` | Table Creation via SELECT |
| **D-03** | `CREATE TEMP TABLE test AS SELECT 1;` | Temporary Storage Block |
| **D-04** | `GRANT ALL PRIVILEGES ON users TO public;` | Permission Escalation Block |
| **D-05** | `SET ROLE admin_user;` | Role Switching Attempt |

### Category C: Analytical Baseline (The "Green Path")
**Expected Result:** `200 OK`  
**Output:** JSON Data Records

| Test ID | SQL Input | Logic Tested |
| :--- | :--- | :--- |
| **P-01** | `SELECT * FROM saved_queries LIMIT 5;` | Basic Read |
| **P-02** | `WITH data AS (SELECT 1 as val) SELECT * FROM data;` | CTE (WITH clause) Support |
| **P-03** | `SELECT count(*), query_name FROM saved_queries GROUP BY 2;` | Aggregation Support |
| **P-04** | `SELECT * FROM saved_queries WHERE query_name LIKE '%Sales%';` | String Filtering |

---

## 2. Testing Instructions

### Via the Web UI
1. Open the **Query Terminal**.
2. Paste the SQL from the table above into the **SQL Input** box.
3. Click **Execute Query**.
4. Verify the error message in the **Results Preview** area matches the expected result.

### Via automate python script
There is a basic testing python script in the scripts folder. It can be ran by doing the following while in the folder:
- python verify_security.py

### Via `curl` (Command Line)
If you want to test the API directly without the frontend:
```bash
curl -X POST http://localhost:8000/api/execute \
     -H "Content-Type: application/json" \
     -d '{"sql": "DROP TABLE users;"}'
```