import unittest
import json
from src.backend.db_manager import local_db
from src.backend.sync_engine import map_local_dispatch_to_cloud

class TestFieldFlowOfflineResilience(unittest.TestCase):

    def setUp(self):
        """Prepares test records for testing zero-signal / offline behavior."""
        self.test_job_id = "JOB-QA-OFFLINE-01"
        self.test_job_num = "776655FL"
        
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            cursor.execute("DELETE FROM projects WHERE tbc_job_number = ?", (self.test_job_num,))
            
            cursor.execute("""
                INSERT INTO projects (tbc_job_number, project_name, site_address, contractor_name, stage)
                VALUES (?, 'Offline Underground Vault Test', 'B1 Basement, Tampa', 'Shield Corp', 'Active')
            """, (self.test_job_num,))

            initial_metrics = json.dumps({"registration_status": "Ready for Review", "serial_number": "SN-OFFLINE-100"})
            cursor.execute("""
                INSERT INTO dispatches (job_id, tbc_job_number, completion_status, report_metrics, technician_email)
                VALUES (?, ?, 'Ready for Review', ?, 'tech1@tombarrow.com')
            """, (self.test_job_id, self.test_job_num, initial_metrics))
            conn.commit()

    def test_zero_signal_fallback_and_local_retention(self):
        """Verifies that when cloud connection is None (zero signal), sync gracefully defers and data remains safe in local SQLite."""
        mock_offline_client = None
        
        local_row = {
            "job_id": self.test_job_id,
            "tbc_job_number": self.test_job_num,
            "technician_email": "tech1@tombarrow.com",
            "registration_status": "Ready for Review"
        }

        # Attempt cloud sync while offline
        sync_result = map_local_dispatch_to_cloud(mock_offline_client, local_row)
        
        # Must return False (deferred) without throwing unhandled crashes
        self.assertFalse(sync_result, "Sync Engine Error: Sync reported success despite zero network connection!")

        # Verify data is still 100% intact in local SQLite database
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Data Loss Failure: Local record was wiped when cloud sync failed!")
            metrics = json.loads(row["report_metrics"])
            self.assertEqual(metrics["serial_number"], "SN-OFFLINE-100")

    def tearDown(self):
        """Cleans up isolated test data."""
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dispatches WHERE job_id = ?", (self.test_job_id,))
            cursor.execute("DELETE FROM projects WHERE tbc_job_number = ?", (self.test_job_num,))
            conn.commit()

if __name__ == "__main__":
    unittest.main()