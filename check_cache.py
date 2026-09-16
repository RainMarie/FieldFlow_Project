import sqlite3
import json
import os

# Locate the database file path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "src", "backend", "tbc_local.db")

# Fallback check if the file layout is flat in the root directory
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(CURRENT_DIR, "tbc_local.db")

print(f"Connecting to Local Cache Database at: {DB_PATH}")

try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query our active test row
    cursor.execute("SELECT job_id, tbc_job_number, report_metrics FROM dispatches WHERE job_id = 'JOB-5005'")
    row = cursor.fetchone()
    
    if row:
        print("\n" + "="*50)
        print("📊 LOCAL OFFLINE STORAGE DATA RECORD DETECTED")
        print("="*50)
        print(f"Active Dispatch ID : {row['job_id']}")
        print(f"Accounting Job #   : {row['tbc_job_number']}")
        print("-"*50)
        
        # Parse and display the embedded JSON payload strings cleanly
        metrics = json.loads(row['report_metrics']) if row['report_metrics'] else {}
        print("Report Payload Matrix:")
        print(json.dumps(metrics, indent=4))
        print("="*50 + "\n")
    else:
        print("\n❌ Error: No cached row entry found matching Job ID 'JOB-5005'.")
        
    conn.close()
except Exception as e:
    print(f"Inspection utility failed to access storage: {e}")