import sqlite3
import json
from src.backend.db_manager import local_db

def verify_local_status():
    conn = local_db.get_connection()
    cursor = conn.cursor()
    
    # Fetch our simulated job row
    cursor.execute("SELECT job_id, report_metrics FROM dispatches WHERE job_id = 'JOB-TEST-99'")
    row = cursor.fetchone()
    conn.close()
    
    print("\n" + "="*50)
    print("VERIFYING LOCAL OFFLINE STORAGE STATE")
    print("="*50)
    
    if row:
        metrics = json.loads(row['report_metrics'])
        print(f"Job Identifier: {row['job_id']}")
        print(f"Current Cached Registration Status: {metrics.get('registration_status')}")
    else:
        print("Test record not found.")
    print("="*50 + "\n")

if __name__ == "__main__":
    verify_local_status()