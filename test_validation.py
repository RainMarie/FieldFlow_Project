import sys
import os

# ELI5: This helps Python locate our 'src' folder code smoothly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from backend.db_manager import is_valid_tbc_job_number
from backend.sync_engine import cloud_document_distribution_wrapper

def run_system_stress_test():
    print("==================================================")
    print("🧪 STARTING FIELDFLOW INGESTION VALIDATION TESTS  ")
    print("==================================================\n")

    # List of test cases: (Job Number, What we expect to happen)
    test_cases = [
        ("123456XX", "SHOULD PASS (Valid 6 numbers + 2 letters)"),
        ("12345678", "SHOULD BLOCK (Old purely numeric format)"),
        ("123456XX9", "SHOULD BLOCK (Too long / overflow string)"),
        ("TEMP-PRJ-99", "SHOULD BLOCK (Temporary layout placeholder)"),
        ("", "SHOULD BLOCK (Empty token string)")
    ]

    for job_num, expectation in test_cases:
        print(f"Testing Input: '{job_num}' | Expectation: {expectation}")
        
        # Test the Local Ingestion Gate check
        local_pass = is_valid_tbc_job_number(job_num)
        
        if local_pass:
            print("  ↳ [LOCAL INGESTION]: APPROVED ✅")
            # If it passes local, try sending it to the cloud sync wrapper
            cloud_document_distribution_wrapper(job_num, payload={})
        else:
            print("  ↳ [LOCAL INGESTION]: BLOCKED ❌ -> Rejects Instantiation.")
        print("-" * 50)

if __name__ == "__main__":
    run_system_stress_test()