import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Update if your port is different
EXECUTE_URL = f"{BASE_URL}/api/execute"

# Define our Test Suite
test_suite = [
    # --- Category A: Gatekeeper (Regex) ---
    {"id": "G-01", "name": "Direct Delete", "sql": "DELETE FROM saved_queries;", "expected": 403},
    {"id": "G-02", "name": "Table Drop", "sql": "DROP TABLE users;", "expected": 403},
    {"id": "G-04", "name": "Piggybacking", "sql": "SELECT * FROM users; DROP TABLE users;", "expected": 403},
    {"id": "G-05", "name": "Comment Injection", "sql": "SELECT * FROM users; -- DROP TABLE users", "expected": 403},
    
    # --- Category B: Safety Net (DB Permissions) ---
    # Note: These might return 400 or 403 depending on if Regex catches them first
    {"id": "D-01", "name": "Nested Update", "sql": "SELECT * FROM (UPDATE users SET id=1 RETURNING *) as t;", "expected": [400, 403]},
    {"id": "D-02", "name": "Select Into", "sql": "SELECT * INTO new_table FROM users;", "expected": [400, 403]},
    
    # --- Category C: Green Path (Successful Queries) ---
    {"id": "P-01", "name": "Basic Read", "sql": "SELECT * FROM saved_queries LIMIT 1;", "expected": 200},
    {"id": "P-02", "name": "CTE Support", "sql": "WITH data AS (SELECT 1 as val) SELECT * FROM data;", "expected": 200},
]

def run_tests():
    print(f"{'ID':<6} | {'Test Name':<20} | {'Status':<10} | {'Result'}")
    print("-" * 60)
    
    passed = 0
    failed = 0

    for test in test_suite:
        try:
            response = requests.post(EXECUTE_URL, json={"sql": test["sql"]}, timeout=5)
            actual_status = response.status_code
            
            # Check if actual status matches expected (handling lists of allowed codes)
            expected = test["expected"]
            is_success = actual_status == expected if isinstance(expected, int) else actual_status in expected
            
            if is_success:
                status_text = "✅ PASS"
                passed += 1
            else:
                status_text = "❌ FAIL"
                failed += 1
            
            print(f"{test['id']:<6} | {test['name']:<20} | {status_text:<10} | Received {actual_status}")
            
        except requests.exceptions.ConnectionError:
            print("\n❌ Error: Could not connect to the server. Is FastAPI running?")
            return

    print("-" * 60)
    print(f"Total Tests: {len(test_suite)} | Passed: {passed} | Failed: {failed}")

if __name__ == "__main__":
    run_tests()