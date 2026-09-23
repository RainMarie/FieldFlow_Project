import time
import logging
import sqlite3
from src.backend.drive_listener import FolderGateListener

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class AutomationTestHarness(FolderGateListener):
    """
    An isolated test harness that inherits from our real Drive Listener 
    but overrides the network scanner to simulate an instant file drop event.
    """
    def __init__(self):
        # Initialize our real engine variables cleanly
        super().__init__(interval_seconds=2)
        logging.info("[TEST HARNESS] Simulation environment initialized.")

    def check_for_new_pdfs(self, folder_id: str):
        """
        Overrides the real Google Drive API internet lookup. 
        Simulates finding a real file instantly when it scans our mock folder path.
        """
        if folder_id == "MOCK_DRIVE_FOLDER_ID_XYZ":
            logging.info(f"[SIMULATED DROP] Guard spotted 'factory_cert_JOB-TEST-99.pdf' inside folder: {folder_id}")
            return [{"id": "mock_file_123", "name": "factory_cert_JOB-TEST-99.pdf"}]
        return []

def execute_live_drop_test():
    print("\n" + "="*60)
    print("STARTING STEP 5.TEST.2: LIVE SIMULATED FILE-DROP EVENT")
    print("="*60 + "\n")
    
    # 1. Start our simulated background engine worker thread
    harness = AutomationTestHarness()
    harness.start()
    
    # 2. Allow the background daemon thread to run for 3 seconds 
    # This gives it enough time to execute its database checks and spot the mock file
    time.sleep(3)
    
    # 3. Spin down the engine safely
    harness.stop()
    print("\n" + "="*60)
    print("SIMULATION CYCLES COMPLETE. PROCEED TO VERIFICATION")
    print("="*60 + "\n")

if __name__ == "__main__":
    execute_live_drop_test()