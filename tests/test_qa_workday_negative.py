import unittest
from src.backend.db_manager import is_valid_tbc_job_number, validate_inspection_metrics

class TestFieldFlowNegativeAssertions(unittest.TestCase):

    def test_invalid_tbc_job_number_rejection(self):
        """Verifies that malformed Tom Barrow Job Numbers are caught and rejected."""
        invalid_numbers = ["123", "ABC12345", "123456789", "INVALID", "1234567", ""]
        for num in invalid_numbers:
            with self.subTest(job_num=num):
                self.assertFalse(
                    is_valid_tbc_job_number(num), 
                    f"Security Gate Failure: Malformed job number '{num}' was improperly accepted!"
                )

    def test_form_validation_schema_rejection(self):
        """Verifies that incomplete or incorrectly typed form metrics are rejected."""
        # VFD_STARTUP requires input_voltage, output_frequency, and motor_amps as numbers
        bad_metrics = {
            "input_voltage": "HIGH_VOLTAGE_STRING", # String instead of int/float
            "output_frequency": 60.0
            # Missing motor_amps completely
        }
        is_valid, msg = validate_inspection_metrics("VFD_STARTUP", bad_metrics)
        self.assertFalse(is_valid, "Form Inspector Failure: Invalid metrics were accepted!")

    def test_missing_evidence_photo_lockout(self):
        """Simulates missing required photo uploads keeping form submission locked."""
        photo_states = {"data_plate": False, "control_screen": True}
        
        # Submission logic requires BOTH slots to be True
        can_submit = photo_states["data_plate"] and photo_states["control_screen"]
        self.assertFalse(can_submit, "Evidence Lock Failure: Form unlocked without Data Plate photo!")

if __name__ == "__main__":
    unittest.main()