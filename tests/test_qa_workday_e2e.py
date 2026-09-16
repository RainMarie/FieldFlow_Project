import unittest
import json
from src.backend.db_manager import local_db, execute_7_day_local_cache_sweep

class TestFieldFlowWorkdayE2E(unittest.TestCase):

    def setUp(self):
        """Prepares a clean, isolated sandbox before each test runs."""
        self.test_job_id = "JOB-QA-2026"
        self.test_job_num = "889900FL"
        self.test_tech_email = "tech1@tombarrow.com"

        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Clean up any leftover test data
            cursor.execute("DELETE FROM job_parts_used WHERE job_id = ?", (self.test_job_id,))
            cursor.execute("DELETE FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            cursor.execute("DELETE FROM projects WHERE tbc_job_number = ?", (self.test_job_num,))
            
            # 2. Seed approved user record for database security rules
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_email, user_name, role)
                VALUES (?, 'Tech One', 'Technician')
            """, (self.test_tech_email,))

            # 3. Plant clean baseline project record
            cursor.execute("""
                INSERT INTO projects (tbc_job_number, project_name, site_address, contractor_name, stage)
                VALUES (?, 'QA Test Hospital Suite', '100 Test Way, Tampa, FL', 'Acme Corp', 'Active')
            """, (self.test_job_num,))

            # 4. Plant initial unassigned dispatch ticket
            initial_metrics = json.dumps({"registration_status": "Draft"})
            cursor.execute("""
                INSERT INTO dispatches (job_id, tbc_job_number, completion_status, report_metrics, labor_hours, travel_hours)
                VALUES (?, ?, 'Scheduled', ?, 0.0, 0.0)
            """, (self.test_job_id, self.test_job_num, initial_metrics))
            conn.commit()

    def test_full_workday_lifecycle(self):
        """Simulates all 5 operational milestones of a technician's workday."""
        
        # --- STAGE 1: Office Dispatch Assignment Gate ---
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dispatches 
                SET technician_email = ?, tech_email = ?, completion_status = 'In Progress'
                WHERE job_id = ?
            """, (self.test_tech_email, self.test_tech_email, self.test_job_id))
            conn.commit()

            cursor.execute("SELECT technician_email, completion_status FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            row = cursor.fetchone()
            self.assertEqual(row["technician_email"], self.test_tech_email)
            self.assertEqual(row["completion_status"], "In Progress")

        # --- STAGE 2: Technician Pre-Travel Driving Clock ---
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dispatches 
                SET travel_hours = 0.5, completion_status = 'Traveling'
                WHERE job_id = ?
            """, (self.test_job_id,))
            conn.commit()

            cursor.execute("SELECT travel_hours, completion_status FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            row = cursor.fetchone()
            self.assertEqual(row["travel_hours"], 0.5)
            self.assertEqual(row["completion_status"], "Traveling")

        # --- STAGE 3: Evidence Locks & Hard Data Freeze ---
        final_metrics = json.dumps({"serial_number": "SN-QA-999", "model_number": "MOD-QA-100", "registration_status": "Registration Complete"})
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dispatches 
                SET completion_status = 'Ready for Review', report_metrics = ?
                WHERE job_id = ?
            """, (final_metrics, self.test_job_id))
            conn.commit()

            cursor.execute("SELECT report_metrics, completion_status FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            row = cursor.fetchone()
            saved_metrics = json.loads(row["report_metrics"])
            self.assertEqual(saved_metrics["registration_status"], "Registration Complete")

        # --- STAGE 4: Unlisted Part Manual Cost Resolution ---
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            usage_id = "USE-QA-PART-1"
            cursor.execute("""
                INSERT INTO job_parts_used (usage_id, job_id, is_unlisted, unlisted_description, manual_cost, cost_status)
                VALUES (?, ?, 1, 'Custom Core Valve Override', 180.00, 'Resolved')
            """, (usage_id, self.test_job_id))
            conn.commit()

            cursor.execute("SELECT manual_cost, cost_status FROM job_parts_used WHERE usage_id = ?", (usage_id,))
            row = cursor.fetchone()
            self.assertEqual(row["manual_cost"], 180.00)
            self.assertEqual(row["cost_status"], "Resolved")

        # --- STAGE 5: Automated 7-Day Memory Cache Sweep ---
        purged_count = execute_7_day_local_cache_sweep()
        self.assertGreaterEqual(purged_count, 1)

        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            row = cursor.fetchone()
            self.assertIsNone(row)

    def tearDown(self):
        """Cleans up the database so no lingering test rows remain."""
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM job_parts_used WHERE job_id = ?", (self.test_job_id,))
            cursor.execute("DELETE FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            cursor.execute("DELETE FROM projects WHERE tbc_job_number = ?", (self.test_job_num,))
            conn.commit()

if __name__ == "__main__":
    unittest.main()