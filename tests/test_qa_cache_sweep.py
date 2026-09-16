import unittest
import json
from src.backend.db_manager import local_db, execute_7_day_local_cache_sweep

class TestFieldFlowCacheSweepIntegrity(unittest.TestCase):

    def setUp(self):
        """Seeds one completed job (target for deletion) and one active job (must be preserved)."""
        self.completed_job_id = "JOB-QA-SWEEP-DONE"
        self.active_job_id = "JOB-QA-SWEEP-ACTIVE"
        self.test_job_num = "998877FL"
        self.test_tech_email = "tech1@tombarrow.com"

        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            # Clean leftover test entries
            cursor.execute("DELETE FROM dispatches WHERE job_id IN (?, ?)", (self.completed_job_id, self.active_job_id))
            cursor.execute("DELETE FROM projects WHERE tbc_job_number = ?", (self.test_job_num,))

            cursor.execute("""
                INSERT OR IGNORE INTO users (user_email, user_name, role)
                VALUES (?, 'Tech One', 'Technician')
            """, (self.test_tech_email,))

            cursor.execute("""
                INSERT INTO projects (tbc_job_number, project_name, site_address, contractor_name, stage)
                VALUES (?, 'Cache Sweep Test Building', '500 Memory Lane', 'Clean Corp', 'Active')
            """, (self.test_job_num,))

            # 1. Completed job with 'Registration Complete' status
            completed_metrics = json.dumps({"registration_status": "Registration Complete"})
            cursor.execute("""
                INSERT INTO dispatches (job_id, tbc_job_number, technician_email, tech_email, completion_status, report_metrics)
                VALUES (?, ?, ?, ?, 'Ready for Review', ?)
            """, (self.completed_job_id, self.test_job_num, self.test_tech_email, self.test_tech_email, completed_metrics))

            # 2. Active job currently 'In Progress'
            active_metrics = json.dumps({"registration_status": "In Progress"})
            cursor.execute("""
                INSERT INTO dispatches (job_id, tbc_job_number, technician_email, tech_email, completion_status, report_metrics)
                VALUES (?, ?, ?, ?, 'In Progress', ?)
            """, (self.active_job_id, self.test_job_num, self.test_tech_email, self.test_tech_email, active_metrics))

            conn.commit()

    def test_cache_sweep_selectivity(self):
        """Verifies that the cache sweep cleans finalized items while preserving active jobs."""
        purged_count = execute_7_day_local_cache_sweep()
        self.assertGreaterEqual(purged_count, 1, "Cache Sweep Failure: Completed job was not purged!")

        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verify completed job was removed from local memory
            cursor.execute("SELECT * FROM dispatches WHERE job_id = ?", (self.completed_job_id,))
            self.assertIsNone(cursor.fetchone(), "Data Corruption Risk: Completed job remained in local storage!")

            # Verify active job was left completely intact
            cursor.execute("SELECT * FROM dispatches WHERE job_id = ?", (self.active_job_id,))
            active_row = cursor.fetchone()
            self.assertIsNotNone(active_row, "CRITICAL ERROR: Active job was accidentally deleted during cache sweep!")

    def tearDown(self):
        """Cleans up the sandbox database."""
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dispatches WHERE job_id IN (?, ?)", (self.completed_job_id, self.active_job_id))
            cursor.execute("DELETE FROM projects WHERE tbc_job_number = ?", (self.test_job_num,))
            conn.commit()

if __name__ == "__main__":
    unittest.main()