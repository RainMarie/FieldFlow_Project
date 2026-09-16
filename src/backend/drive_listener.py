import time
import logging
import threading
from typing import List, Dict, Any
from src.backend.drive_service import get_drive_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class DriveListener:
    """Background monitoring service for Google Drive folder activity and incoming PDF files."""

    def __init__(self, interval_seconds: int = 30, drive_service=None):
        self.interval_seconds = interval_seconds
        self.drive_service = drive_service or get_drive_service()
        self.is_running = False
        self.thread = None

    def start(self):
        """Spawns the background monitoring loop in an isolated thread."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logging.info(f"🧵 Drive Listener engaged. Pulse interval: {self.interval_seconds}s.")

    def stop(self):
        """Gracefully stops background monitoring."""
        self.is_running = False
        logging.info("🛑 Drive Listener halted safely.")

    def _monitor_loop(self):
        """Continuous polling loop for active Drive directories."""
        while self.is_running:
            try:
                # Active folder monitoring logic can be invoked here
                pass
            except Exception as e:
                logging.error(f"Error inside Drive monitoring loop: {e}")
            time.sleep(self.interval_seconds)

    def check_for_new_pdfs(self, folder_id: str) -> List[Dict[str, Any]]:
        """Scans a specified Google Drive folder for newly uploaded PDF documents."""
        if not self.drive_service:
            logging.warning("Drive service unavailable for PDF check.")
            return []

        try:
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, createdTime, webViewLink)"
            ).execute()

            files = results.get('files', [])
            logging.info(f"🔍 Found {len(files)} PDF document(s) in folder {folder_id}.")
            return files
        except Exception as e:
            logging.error(f"Failed to scan folder {folder_id} for PDFs: {e}")
            return []


if __name__ == "__main__":
    print("\n--- Verification Test: Drive Listener ---")
    listener = DriveListener(interval_seconds=2)
    listener.start()
    time.sleep(3)
    listener.stop()