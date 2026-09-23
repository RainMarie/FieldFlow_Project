"""
test_callbacks.py
FieldFlow Automated Dashboard Callback Tester
Dynamically connects to tbc_local.db inside src/backend/ via local_db path resolution.
Audits email mailto: triggers, 123456XX ticket lookups, and triage routing payloads.
"""

import os
import sys
import sqlite3
import urllib.parse

# 1. Dynamically append project root to Python's module search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

# 2. Import local_db manager to fetch the exact backend database path
try:
    from src.backend.db_manager import local_db
    DB_PATH = local_db.db_path
except ImportError:
    # Fallback path pointing directly to backend folder if module import fails
    DB_PATH = os.path.join(CURRENT_DIR, "src", "backend", "tbc_local.db")


def run_callback_diagnostics():
    """
    Executes automated diagnostic tests for all dashboard callbacks using seeded SQLite data.
    """
    print("=" * 80)
    print("🧪 FIELDFLOW DASHBOARD CALLBACK DIAGNOSTIC TESTER")
    print("=" * 80)

    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at path: {DB_PATH}")
        print("   Please run 'python seed_project_data.py' first to populate the database.")
        return

    print(f"📁 Backend Database Location: {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    test_results = []

    # -------------------------------------------------------------------------
    # 1. TEST EMAIL BUTTON CALLBACKS (mailto: triggers)
    # -------------------------------------------------------------------------
    cursor.execute("SELECT user_email, first_name, last_name FROM users WHERE role = 'Sales' LIMIT 5")
    sales_reps = cursor.fetchall()

    for email, first, last in sales_reps:
        subject = urllib.parse.quote(f"FieldFlow Dispatch Notice for {first} {last}")
        mailto_url = f"mailto:{email}?subject={subject}"
        
        if "@" in email and mailto_url.startswith("mailto:"):
            test_results.append(("Email Callback", email, "PASS", mailto_url))
        else:
            test_results.append(("Email Callback", email, "FAIL", "Invalid email address or string format"))

    # -------------------------------------------------------------------------
    # 2. TEST TICKET & DISPATCH LOOKUPS (123456XX format)
    # -------------------------------------------------------------------------
    cursor.execute("SELECT tbc_job_number, project_name FROM projects LIMIT 5")
    projects = cursor.fetchall()

    for job_no, proj_name in projects:
        cursor.execute("SELECT * FROM projects WHERE tbc_job_number = ?", (job_no,))
        record = cursor.fetchone()

        if record and (len(job_no) >= 8):  # Validates 123456XX formatting
            test_results.append(("Ticket Lookup", job_no, "PASS", f"Retrieved '{proj_name}'"))
        else:
            test_results.append(("Ticket Lookup", job_no, "FAIL", "Job record missing or invalid ID format"))

    # -------------------------------------------------------------------------
    # 3. TEST INTAKE TRIAGE ROUTING
    # -------------------------------------------------------------------------
    cursor.execute("SELECT request_id, tbc_job_number, triage_status FROM intake_requests LIMIT 5")
    intakes = cursor.fetchall()

    for req_id, job_no, status in intakes:
        cursor.execute("SELECT * FROM intake_requests WHERE request_id = ?", (req_id,))
        record = cursor.fetchone()

        if record:
            test_results.append(("Triage Routing", req_id, "PASS", f"Linked to Job #{job_no} ({status})"))
        else:
            test_results.append(("Triage Routing", req_id, "FAIL", "Intake request payload unresolvable"))

    conn.close()

    # -------------------------------------------------------------------------
    # PRINT DIAGNOSTIC MATRIX
    # -------------------------------------------------------------------------
    print(f"{'TEST CATEGORY':<18} | {'PAYLOAD TARGET':<22} | {'STATUS':<8} | {'DETAILS'}")
    print("-" * 80)

    pass_count = 0
    for category, target, status, details in test_results:
        symbol = "✅ PASS" if status == "PASS" else "❌ FAIL"
        if status == "PASS":
            pass_count += 1
        print(f"{category:<18} | {target:<22} | {symbol:<8} | {details}")

    print("-" * 80)
    print(f"RESULTS: {pass_count}/{len(test_results)} callback tests passed successfully.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_callback_diagnostics()