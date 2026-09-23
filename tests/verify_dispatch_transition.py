import logging
from src.backend.db_manager import create_intake_request, dispatch_intake_request, local_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def run_dispatch_transition_test():
    print("\n" + "="*60)
    print("🧪 RUNNING TASK BE-09.3 DISPATCH TRANSITION VERIFICATION TEST")
    print("="*60 + "\n")

    # 1. Seed a test intake ticket into our local filing cabinet
    test_ticket_id = "TEMP-CR-2026-0001"
    sample_payload = {
        "request_id": test_ticket_id,
        "contractor_company_name": "Acme Mechanical Solutions",
        "project_site_address": "1 Hospital Segment Way, Tampa, FL",
        "issue_description": "VFD tripping on overvoltage fault during startup.",
        "triage_status": "PENDING_TRIAGE"
    }
    
    create_intake_request(sample_payload)
    print(f"📥 [TEST SEED] Seeded test intake ticket '{test_ticket_id}' with status 'PENDING_TRIAGE'.")

    # 2. Test Invalid Job Number Guard (Should fail safely)
    print("\n--- Test 1: Testing Malformed Job Number Security Block ---")
    bad_result = dispatch_intake_request(test_ticket_id, "INVALID_JOB")
    assert bad_result == False, "❌ Error: System allowed an invalid job number!"
    print("✅ Blocked invalid job number format successfully.")

    # 3. Test Valid Dispatch Transition (Should succeed)
    print("\n--- Test 2: Executing Valid Dispatch Transition ---")
    valid_job_number = "123456XX"
    good_result = dispatch_intake_request(test_ticket_id, valid_job_number)
    assert good_result == True, "❌ Error: Dispatch transition failed for valid ticket!"

    # 4. Verify Local Database Record Update
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT triage_status, tbc_job_number FROM intake_requests WHERE request_id = ?", (test_ticket_id,))
        row = cursor.fetchone()

    print(f"\n🔍 [LOCAL DB VERIFICATION]")
    print(f"   - Ticket ID: {test_ticket_id}")
    print(f"   - New Triage Status: {row['triage_status']}")
    print(f"   - Assigned Job #: {row['tbc_job_number']}")

    assert row['triage_status'] == "DISPATCHED", "❌ Error: Database status was not updated to DISPATCHED!"
    assert row['tbc_job_number'] == valid_job_number, "❌ Error: Job number mismatch in database!"

    print("\n" + "="*60)
    print("🎉 TASK BE-09.3 VERIFICATION COMPLETE: ALL CHECKS PASSED!")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_dispatch_transition_test()