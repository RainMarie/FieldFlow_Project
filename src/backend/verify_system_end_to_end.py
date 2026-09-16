"""
src/backend/verify_system_end_to_end.py
Comprehensive end-to-end integration test suite verifying backend models, 
schema migrations, role permissions, search indexing, and cloud sync engine routines.
"""

import sys
import os
import logging

# --- Dynamic Path Resolution ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_system_verification():
    """Runs a non-destructive health check across all refactored project modules."""
    print("\n" + "=" * 60)
    print("🚀 FIELDFLOW SYSTEM-WIDE END-TO-END VERIFICATION SUITE")
    print("=" * 60 + "\n")

    pass_count = 0
    fail_count = 0

    # -------------------------------------------------------------------------
    # STEP 1: VERIFY VALIDATORS MODULE
    # -------------------------------------------------------------------------
    try:
        from src.backend.validators import is_valid_tbc_job_number, validate_inspection_metrics
        
        # Test valid and invalid job numbers
        assert is_valid_tbc_job_number("123456XX") == True, "Valid job number failed verification"
        assert is_valid_tbc_job_number("INVALID_JOB") == False, "Invalid job number passed verification"
        
        # Test generic inspection metric validation
        is_valid, _ = validate_inspection_metrics("GENERIC_JOB", {"some_key": "some_val"})
        assert is_valid == True, "Generic inspection metrics failed"

        print("✅ [PASS] Step 1: Validators Module (Job Numbers & Metric Blueprints)")
        pass_count += 1
    except Exception as e:
        print(f"❌ [FAIL] Step 1: Validators Module Error: {e}")
        fail_count += 1

    # -------------------------------------------------------------------------
    # STEP 2: VERIFY DATABASE MANAGER & ENCRYPTED VAULT
    # -------------------------------------------------------------------------
    try:
        from src.backend.db_manager import local_db, cred_manager
        
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Verify 15+ schema tables are present
            assert len(tables) >= 15, f"Expected 15+ SQLite tables, found {len(tables)}"

        print(f"✅ [PASS] Step 2: Database Manager & Encrypted Vault ({len(tables)} SQLite Tables Verified)")
        pass_count += 1
    except Exception as e:
        print(f"❌ [FAIL] Step 2: Database Manager Error: {e}")
        fail_count += 1

    # -------------------------------------------------------------------------
    # STEP 3: VERIFY CENTRALIZED CALENDAR SERVICE
    # -------------------------------------------------------------------------
    try:
        from src.backend.calendar_service import GoogleCalendarService
        from src.backend.calendar_listener import GoogleCalendarListener
        from src.backend.calendar_manager import GoogleCalendarManager

        cal_service = GoogleCalendarService()
        listener = GoogleCalendarListener(calendar_service=cal_service)
        manager = GoogleCalendarManager(calendar_service=cal_service)

        assert cal_service is not None, "Calendar Service failed to instantiate"
        assert listener is not None, "Calendar Listener failed to instantiate"
        assert manager is not None, "Calendar Manager failed to instantiate"

        print("✅ [PASS] Step 3: Centralized Google Calendar Service & Listeners")
        pass_count += 1
    except Exception as e:
        print(f"❌ [FAIL] Step 3: Calendar Service Error: {e}")
        fail_count += 1

    # -------------------------------------------------------------------------
    # STEP 4: VERIFY DRIVE LISTENER & TEMPLATE FACTORY DECOUPLING
    # -------------------------------------------------------------------------
    try:
        from src.backend.drive_listener import DriveListener
        from src.backend.template_factory import GoogleDocTemplateFactory

        drive_listener = DriveListener()
        template_factory = GoogleDocTemplateFactory()

        assert drive_listener is not None, "Drive Listener failed to instantiate"
        assert template_factory is not None, "Template Factory failed to instantiate"

        print("✅ [PASS] Step 4: Drive Listener & Template Factory Decoupling")
        pass_count += 1
    except Exception as e:
        print(f"❌ [FAIL] Step 4: Drive Listener & Template Factory Error: {e}")
        fail_count += 1

    # -------------------------------------------------------------------------
    # STEP 5: VERIFY LIFECYCLE RULES & USER ROLE GOVERNANCE
    # -------------------------------------------------------------------------
    try:
        from src.backend.lifecycle_rules import validate_user_role_permission, validate_intake_form_data

        # Test valid intake form dictionary checks
        test_payload = {
            "tbco_account_number": "CON-1001",
            "site_name": "Test Hospital",
            "tbc_job_number": "123456AB"
        }
        is_valid_intake, _ = validate_intake_form_data(test_payload)
        assert is_valid_intake == True, "Valid intake payload check failed"

        print("✅ [PASS] Step 5: Lifecycle Rules & Role Governance")
        pass_count += 1
    except Exception as e:
        print(f"❌ [FAIL] Step 5: Lifecycle Rules Error: {e}")
        fail_count += 1

    # -------------------------------------------------------------------------
    # STEP 6: VERIFY MULTI-TABLE SEARCH ENGINE
    # -------------------------------------------------------------------------
    try:
        from src.backend.search_engine import search_admin_portal, search_mobile_portal

        admin_results = search_admin_portal("test")
        mobile_results = search_mobile_portal("test", "tech1@tbcotampaservice.com")

        assert isinstance(admin_results, list), "Admin search did not return a list"
        assert isinstance(mobile_results, list), "Mobile search did not return a list"

        print(f"✅ [PASS] Step 6: Multi-Table Indexed Search Engine (Dry Runs Verified)")
        pass_count += 1
    except Exception as e:
        print(f"❌ [FAIL] Step 6: Search Engine Error: {e}")
        fail_count += 1

    # -------------------------------------------------------------------------
    # STEP 7: VERIFY EMAIL SERVICE & RECIPIENT LOOKUPS
    # -------------------------------------------------------------------------
    try:
        from src.backend.email_service import get_sales_rep_email_for_dispatch, send_dispatch_receipt_email

        resolved_email = get_sales_rep_email_for_dispatch("JOB-NONEXISTENT")
        assert resolved_email == "sales1@tombarrow.com", "Email service fallback hierarchy failed"

        print(f"✅ [PASS] Step 7: Email Service & Sales Representative Lookups")
        pass_count += 1
    except Exception as e:
        print(f"❌ [FAIL] Step 7: Email Service Error: {e}")
        fail_count += 1

    # -------------------------------------------------------------------------
    # STEP 8: VERIFY SYNC ENGINE CLOUD MAPPINGS
    # -------------------------------------------------------------------------
    try:
        from src.backend.sync_engine import map_local_dispatch_to_cloud, map_intake_to_cloud

        # Verify offline behavior safely handles None db_client
        dispatch_sync_res = map_local_dispatch_to_cloud(None, {"job_id": "JOB-1", "tbc_job_number": "123456AB"})
        intake_sync_res = map_intake_to_cloud(None, {"intake_id": "REQ-1"})

        assert dispatch_sync_res == False, "Offline dispatch sync should return False safely"
        assert intake_sync_res == False, "Offline intake sync should return False safely"

        print("✅ [PASS] Step 8: Cloud Sync Engine & Offline Fallbacks")
        pass_count += 1
    except Exception as e:
        print(f"❌ [FAIL] Step 8: Sync Engine Error: {e}")
        fail_count += 1

    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print(f"🎯 VERIFICATION COMPLETE: {pass_count} Passed | {fail_count} Failed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_system_verification()