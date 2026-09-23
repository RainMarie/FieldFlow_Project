"""
src/backend/sync_engine.py
Handles asynchronous cloud synchronization between local SQLite records and Cloud Firestore.
Synchronizes intake records to the standardized 'intake_ledger' cloud collection.
"""

import re
import logging
import random
import time
import threading
from datetime import datetime, timezone
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def map_local_dispatch_to_cloud(db_client, local_row: dict) -> bool:
    """
    Takes a local SQLite dispatch row, maps it into a normalized cloud payload,
    and runs it through a retry loop with randomized delays to prevent cloud write conflicts.
    """
    if db_client is None:
        logging.warning("[SYNC MAP SKIP] Cloud routing offline. Retaining data safely inside local sandbox cache.")
        return False
        
    job_id = local_row.get("job_id")
    tbc_job_number = local_row.get("tbc_job_number")
    
    if not tbc_job_number or len(tbc_job_number) < 8:
        logging.error(f"[SECURITY BLOCK] Rejects cloud instantiation: Invalid 8-digit job identifier.")
        return False

    cloud_payload = {
        "job_id": job_id,
        "tbc_job_number": tbc_job_number,
        "tbco_account_number": local_row.get("tbco_account_number"),
        "site_name": local_row.get("site_name"),
        "sales_rep_email": local_row.get("sales_rep_email"),
        "technician_email": local_row.get("technician_email"),
        "status": local_row.get("status", "Scheduled"),
        "last_modified_timestamp": datetime.now(timezone.utc)
    }

    MAX_ATTEMPTS = 3
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logging.info(f"[SYNC ATTEMPT {attempt}/{MAX_ATTEMPTS}] Sending write packet for Job {job_id}...")
            db_client.collection("dispatches").document(job_id).set(cloud_payload, merge=True)
            logging.info(f"[CLOUD SYNC SUCCESS] Document {job_id} successfully mapped to Firestore.")
            return True
            
        except Exception as error_token:
            jitter_delay = random.uniform(0.5, 1.5)
            logging.warning(f"Cloud write traffic conflict detected on row: {str(error_token)}")
            
            if attempt < MAX_ATTEMPTS:
                time.sleep(jitter_delay)
            else:
                logging.error("Collision Buffer: Max retry attempts (3) exhausted.")
                
    return False


def dispatch_sync_in_background(db_client, local_row: dict):
    """Spawns an isolated background thread for dispatch cloud synchronization."""
    worker_thread = threading.Thread(
        target=map_local_dispatch_to_cloud,
        args=(db_client, local_row),
        daemon=True
    )
    worker_thread.start()


def map_intake_to_cloud(db_client, intake_data: dict) -> bool:
    """
    Takes a local intake request record and uploads it to the standardized 'intake_ledger' cloud collection.
    """
    if db_client is None:
        logging.warning("[INTAKE CLOUD SKIP] Cloud store routing offline. Retaining intake record locally.")
        return False

    request_id = intake_data.get("request_id")
    if not request_id:
        logging.error("[SECURITY BLOCK] Cannot sync intake record without a valid request_id.")
        return False

    cloud_payload = {
        "request_id": request_id,
        "tbc_job_number": intake_data.get("tbc_job_number"),
        "team_code": intake_data.get("team_code"),
        "site_name": intake_data.get("site_name"),
        "project_name": intake_data.get("project_name"),
        "contractor_company_name": intake_data.get("contractor_company_name"),
        "street_address_1": intake_data.get("street_address_1"),
        "street_address_2": intake_data.get("street_address_2"),
        "city": intake_data.get("city"),
        "state": intake_data.get("state"),
        "postal_code": intake_data.get("postal_code"),
        "country": intake_data.get("country", "US"),
        "sales_rep_email": intake_data.get("sales_rep_email"),
        "sales_rep_phone": intake_data.get("sales_rep_phone"),
        "project_site_contact_first_name": intake_data.get("project_site_contact_first_name"),
        "project_site_contact_last_name": intake_data.get("project_site_contact_last_name"),
        "project_site_contact_email": intake_data.get("project_site_contact_email"),
        "project_site_contact_phone": intake_data.get("project_site_contact_phone"),
        "issue_description": intake_data.get("issue_description"),
        "triage_status": intake_data.get("triage_status", "Unassigned"),
        "request_type": intake_data.get("request_type", "VFD Startup"),
        "submission_timestamp": intake_data.get("submission_timestamp", datetime.now(timezone.utc).isoformat()),
        "last_modified_timestamp": datetime.now(timezone.utc)
    }

    MAX_ATTEMPTS = 3
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logging.info(f"[INTAKE CLOUD SYNC {attempt}/{MAX_ATTEMPTS}] Syncing intake {request_id} to Firestore...")
            db_client.collection("intake_ledger").document(request_id).set(cloud_payload, merge=True)
            logging.info(f"[INTAKE CLOUD SUCCESS] Document {request_id} mapped to collection intake_ledger.")
            return True
        except Exception as error_token:
            jitter_delay = random.uniform(0.5, 1.5)
            logging.warning(f"[INTAKE SYNC CONFLICT] Write conflict on intake {request_id}: {error_token}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(jitter_delay)

    return False


def sync_intake_in_background(db_client, intake_data: dict):
    """Detaches cloud intake upload operation into an isolated background thread."""
    worker_thread = threading.Thread(
        target=map_intake_to_cloud,
        args=(db_client, intake_data),
        daemon=True
    )
    worker_thread.start()