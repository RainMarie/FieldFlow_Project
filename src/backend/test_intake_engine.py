import os
import sys

# Dynamic path resolution to connect with backend database engines cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.backend.db_manager import (
    add_intake_record,
    get_pending_intakes,
    convert_intake_to_dispatched
)

def run_intake_test():
    print("\n" + "="*60)
    print("🧪 RUNNING INTAKE LEDGER ENGINE TEST")
    print("="*60 + "\n")

    # 1. Create a dummy customer request
    print("1️⃣ Creating test incoming customer order...")
    sample_request = {
        "client_name": "Tampa General Hospital",
        "service_address": "1 Hospital Segment Way, Tampa, FL",
        "contact_phone": "813-555-0199",
        "issue_description": "Chiller unit reporting emergency error code E-04.",
        "intake_source": "PHONE_IN",
        "created_by": "office_admin@tombarrow.com"
    }
    
    intake_id = add_intake_record(sample_request)
    print(f"   ✅ Saved new order slip with tracking tag: {intake_id}\n")

    # 2. Fetch pending requests (Admin Inbox view)
    print("2️⃣ Fetching pending unassigned requests for Admin Inbox...")
    pending_list = get_pending_intakes()
    print(f"   📋 Found {len(pending_list)} pending order(s) waiting for review.")
    
    found = any(item.get("intake_id") == intake_id for item in pending_list)
    if found:
        print("   ✅ Verified: Created order slip appears in the review queue!\n")
    else:
        print("   ❌ Error: Created order slip missing from review queue!\n")
        return

    # 3. Dispatch the order
    print("3️⃣ Assigning technician & converting request to active job...")
    test_job_number = "123456XX"
    test_tech_email = "tech1@tbcotampaservice.com"
    
    success = convert_intake_to_dispatched(intake_id, test_job_number, test_tech_email)
    if success:
        print(f"   ✅ Order {intake_id} converted to Job #{test_job_number} assigned to {test_tech_email}!\n")

    # 4. Re-check pending requests to verify it was cleared
    print("4️⃣ Re-checking pending inbox to verify slip was cleared...")
    updated_pending = get_pending_intakes()
    still_pending = any(item.get("intake_id") == intake_id for item in updated_pending)
    
    if not still_pending:
        print("   🎉 SUCCESS: Order slip moved out of holding tray and into active work orders!\n")
    else:
        print("   ❌ Error: Order slip still showing as pending after dispatch!\n")

    print("="*60)
    print("✅ INTAKE ENGINE TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_intake_test()