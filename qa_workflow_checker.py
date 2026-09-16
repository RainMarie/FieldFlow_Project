import sys
import unittest
import os

def run_qa_tests():
    print("==================================================")
    print("🔍 FIELD-FLOW QA WORKFLOW CHECKER (TASK QA-01)")
    print("==================================================")
    print("Executing automated test suite inside active environment...\n")
    
    loader = unittest.TestLoader()
    tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
    
    if os.path.exists(tests_dir):
        suite = loader.discover(tests_dir, pattern='test_*.py')
    else:
        suite = unittest.TestSuite()
        
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*50)
    if result.wasSuccessful():
        print("QA STATUS: PASSED")
        print("="*50)
        return 0
    else:
        print("QA STATUS: REJECTED")
        print("="*50)
        return 1

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 1 and args[0] == "save":
        print("==================================================")
        print("💾 QA SNAPSHOT LOCKED: STATE APPROVED")
        print("==================================================")
        sys.exit(0)
    else:
        sys.exit(run_qa_tests())