import sqlite3
import os

# Path to local SQLite database
DB_PATH = os.path.join("src", "backend", "tbc_local.db")

def inspect_database():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at expected path: {DB_PATH}")
        return

    print(f"Connecting to: {os.path.abspath(DB_PATH)}\n")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enables column access by name
    cursor = conn.cursor()

    # 1. Inspect Table 12: INTAKE_REQUESTS
    print("=" * 75)
    print("🔍 VISUAL PROOF: INTAKE_REQUESTS TABLE (Most Recent First)")
    print("=" * 75)
    
    cursor.execute("""
        SELECT request_id, tbc_job_number, contractor_company_name, project_site_address, 
               requestor_name, requestor_email, triage_status, submission_timestamp 
        FROM intake_requests 
        ORDER BY rowid DESC 
        LIMIT 5
    """)
    intake_rows = cursor.fetchall()

    if not intake_rows:
        print("⚠️ No records found in intake_requests table.")
    else:
        for row in intake_rows:
            print(f"🎫 TICKET ID : {row['request_id']}")
            print(f"   Job #     : {row['tbc_job_number']}")
            print(f"   Status    : {row['triage_status']}")
            print(f"   Client    : {row['contractor_company_name']}")
            print(f"   Address   : {row['project_site_address']}")
            print(f"   Requestor : {row['requestor_name']} ({row['requestor_email']})")
            print("-" * 75)

    # 2. Inspect PROJECTS Table
    print("\n" + "=" * 75)
    print("📁 VISUAL PROOF: PROJECTS TABLE (Most Recent First)")
    print("=" * 75)

    cursor.execute("""
        SELECT tbc_job_number, project_name, contractor_name, site_address, drive_id, stage 
        FROM projects 
        ORDER BY rowid DESC 
        LIMIT 5
    """)
    project_rows = cursor.fetchall()

    if not project_rows:
        print("⚠️ No records found in projects table.")
    else:
        for row in project_rows:
            print(f"🏗️ JOB #     : {row['tbc_job_number']}")
            print(f"   Stage     : {row['stage']}")
            print(f"   Drive ID  : {row['drive_id']}")
            print(f"   Project   : {row['project_name']}")
            print(f"   Contractor: {row['contractor_name']}")
            print("-" * 75)

    conn.close()

if __name__ == "__main__":
    inspect_database()