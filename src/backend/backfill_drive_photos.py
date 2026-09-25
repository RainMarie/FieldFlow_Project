"""
src/backend/backfill_drive_photos.py
Retroactive migration script for FieldFlow.
Scans local SQLite and Cloud Firestore database records for local file path references,
uploads existing images to Google Drive, and updates database records with 
direct streamable Google Drive thumbnail URLs.
"""

import os
import sys
import logging
from typing import Dict, Any

# Dynamic path resolution to recognize project root directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.backend.db_manager import local_db, db as firestore_db
from src.backend.drive_service import ensure_project_drive_folder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_historical_photo_backfill():
    """
    Reads records from local SQLite (intake_ledger and projects), identifies local disk photo paths,
    uploads them to their respective Google Drive project folders, and updates SQLite and Firestore.
    """
    logging.info("🚀 Starting Historical Photo Backfill Migration Routine...")
    intake_count = 0
    project_count = 0

    # -------------------------------------------------------------------------
    # 1. MIGRATE INTAKE LEDGER SERVICE REQUEST PHOTOS
    # -------------------------------------------------------------------------
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT request_id, tbc_job_number, project_name, sales_rep_email, photo_url 
                FROM intake_ledger 
                WHERE photo_url IS NOT NULL AND photo_url != '' AND photo_url NOT LIKE 'http%'
            """)
            intake_rows = cursor.fetchall()
            
            logging.info(f"🔍 Found {len(intake_rows)} intake request record(s) with local photo paths.")
            
            for row in intake_rows:
                req_id = row["request_id"]
                job_num = str(row["tbc_job_number"] or "UNKNOWN").strip().upper()
                proj_name = str(row["project_name"] or "Service Project").strip()
                sales_email = str(row["sales_rep_email"] or "").strip()
                local_path = str(row["photo_url"]).strip()

                if os.path.exists(local_path) and os.path.isfile(local_path):
                    logging.info(f"📤 Uploading local photo for Intake Request '{req_id}' (Job #{job_num})...")
                    drive_info = ensure_project_drive_folder(
                        job_number=job_num,
                        project_name=proj_name,
                        requestor_name="Historical Backfill",
                        requestor_email=sales_email,
                        attached_file_paths=[local_path]
                    )
                    
                    drive_photo_url = drive_info.get("photo_url", "")
                    if drive_photo_url and drive_photo_url.startswith("http"):
                        # Update Local SQLite
                        cursor.execute("""
                            UPDATE intake_ledger 
                            SET photo_url = ? 
                            WHERE request_id = ?
                        """, (drive_photo_url, req_id))
                        
                        # Update Cloud Firestore
                        if firestore_db is not None:
                            try:
                                firestore_db.collection("intake_ledger").document(req_id).set(
                                    {"photo_url": drive_photo_url}, merge=True
                                )
                            except Exception as fs_err:
                                logging.warning(f"Firestore update error for Intake '{req_id}': {fs_err}")
                                
                        intake_count += 1
                        logging.info(f"✅ Intake Request '{req_id}' photo backfilled to Google Drive: {drive_photo_url}")
                    else:
                        logging.warning(f"⚠️ Drive upload returned empty or invalid URL for Intake '{req_id}'.")
                else:
                    logging.warning(f"⚠️ Local image file not found on disk: '{local_path}' (Intake #{req_id})")
                    
            conn.commit()
    except Exception as sql_err:
        logging.error(f"Error during intake ledger backfill query: {sql_err}")

    # -------------------------------------------------------------------------
    # 2. MIGRATE MASTER PROJECT COVER PHOTOS
    # -------------------------------------------------------------------------
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tbc_job_number, project_name, sales_rep_email, photo_url 
                FROM projects 
                WHERE photo_url IS NOT NULL AND photo_url != '' AND photo_url NOT LIKE 'http%'
            """)
            project_rows = cursor.fetchall()
            
            logging.info(f"🔍 Found {len(project_rows)} project master record(s) with local photo paths.")
            
            for row in project_rows:
                job_num = str(row["tbc_job_number"]).strip().upper()
                proj_name = str(row["project_name"] or "Service Project").strip()
                sales_email = str(row["sales_rep_email"] or "").strip()
                local_path = str(row["photo_url"]).strip()

                if os.path.exists(local_path) and os.path.isfile(local_path):
                    logging.info(f"📤 Uploading local photo for Project Job #{job_num}...")
                    drive_info = ensure_project_drive_folder(
                        job_number=job_num,
                        project_name=proj_name,
                        requestor_name="Historical Backfill",
                        requestor_email=sales_email,
                        attached_file_paths=[local_path]
                    )
                    
                    drive_photo_url = drive_info.get("photo_url", "")
                    if drive_photo_url and drive_photo_url.startswith("http"):
                        # Update Local SQLite
                        cursor.execute("""
                            UPDATE projects 
                            SET photo_url = ? 
                            WHERE tbc_job_number = ?
                        """, (drive_photo_url, job_num))
                        
                        # Update Cloud Firestore
                        if firestore_db is not None:
                            try:
                                firestore_db.collection("projects").document(job_num).set(
                                    {"photo_url": drive_photo_url}, merge=True
                                )
                            except Exception as fs_err:
                                logging.warning(f"Firestore update error for Project Job #{job_num}: {fs_err}")
                                
                        project_count += 1
                        logging.info(f"✅ Master Project Job #{job_num} photo backfilled to Google Drive: {drive_photo_url}")
                    else:
                        logging.warning(f"⚠️ Drive upload returned empty or invalid URL for Job #{job_num}.")
                else:
                    logging.warning(f"⚠️ Local image file not found on disk: '{local_path}' (Job #{job_num})")
                    
            conn.commit()
    except Exception as sql_err:
        logging.error(f"Error during projects backfill query: {sql_err}")

    logging.info("=" * 60)
    logging.info(f"🎉 BACKFILL COMPLETE: {intake_count} Service Request(s) and {project_count} Master Project(s) migrated to Google Drive!")
    logging.info("=" * 60)


if __name__ == "__main__":
    run_historical_photo_backfill()