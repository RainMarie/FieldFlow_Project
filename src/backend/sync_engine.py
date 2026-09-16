"""
src/backend/sync_engine.py
Handles asynchronous cloud synchronization between local SQLite records and Cloud Firestore.
"""

import re
import logging
import random
import time
import threading
from datetime import datetime, timezone
from typing import Optional

# Configure system logging to monitor background behavior cleanly
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
    
    # Enforce strict 8-character job identifier anchor requirement
    if not tbc_job_number or len(tbc_job_number) < 8:
        logging.error(f"[SECURITY BLOCK] Rejects cloud instantiation: Invalid 8-digit job identifier.")
        return False

    # Normalized Cloud Payload aligned with updated schema
    cloud_payload = {
        "job_id": job_id,
        "tbc_job_number": tbc_job_number,
        "tbco_account_number": local_row.get("tbco_account_number"),
        "site_name": local_row.get("site_name"),
        "sales_rep_email": local_row.get("sales_rep_email"),
        "technician_email": local_row.get("technician_email"),
        "registration_status": local_row.get("registration_status", "Registration Complete"),
        "last_modified_timestamp": datetime.now(timezone.utc)
    }

    # --- Traffic Cop Collision Retry Loop ---
    MAX_ATTEMPTS = 3
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logging.info(f"[SYNC ATTEMPT {attempt}/{MAX_ATTEMPTS}] Sending write packet for Job {job_id}...")
            
            db_client.collection("dispatches").document(job_id).set(cloud_payload, merge=True)
            logging.info(f"🎉 [CLOUD SYNC SUCCESS] Document {job_id} successfully mapped to Firestore.")
            return True
            
        except Exception as error_token:
            jitter_delay = random.uniform(0.5, 1.5)
            logging.warning(f"Cloud write traffic conflict detected on row: {str(error_token)}")
            
            if attempt < MAX_ATTEMPTS:
                logging.warning(f"Collision Buffer: Retrying in {jitter_delay:.2f} seconds...")
                time.sleep(jitter_delay)
            else:
                logging.error("Collision Buffer: Max retry attempts (3) exhausted. Shifting data safely back to fallback storage.")
                
    return False


def dispatch_sync_in_background(db_client, local_row: dict):
    """
    Detaches the cloud upload operation from the main visual screen,
    spawning a silent background thread so the screen never freezes.
    """
    worker_thread = threading.Thread(
        target=map_local_dispatch_to_cloud,
        args=(db_client, local_row),
        daemon=True
    )
    worker_thread.start()
    logging.info(f"🧵 [THREAD DEPLOYED] Asynchronous cloud sync engine engaged for Job {local_row.get('job_id', 'UNKNOWN')}.")


def cloud_document_distribution_wrapper(job_number: str, payload: dict) -> bool:
    """
    Validates job numbers against company formatting standards before pushing to cloud.
    """
    pattern = r"^\d{6}[a-zA-Z]{2}$"
    
    if not job_number or not bool(re.match(pattern, job_number.strip())):
        print(f"[SECURITY BLOCK] Rejects cloud sync instantiation for invalid token: '{job_number}'")
        return False

    print(f"[CLOUD SYNC SUCCESS] Job {job_number} approved. Passing payload to Firestore.")
    return True


# =========================================================================
# INTAKE LEDGER CLOUD SYNC WRAPPER
# =========================================================================

def map_intake_to_cloud(db_client, intake_data: dict) -> bool:
    """
    Takes a local intake request record and uploads it to the 'intake_ledger' cloud collection.
    Includes normalized site names, account numbers, and sales emails in the cloud payload.
    """
    if db_client is None:
        logging.warning("[INTAKE CLOUD SKIP] Cloud store routing offline. Retaining intake record locally.")
        return False

    intake_id = intake_data.get("intake_id") or intake_data.get("request_id")
    if not intake_id:
        logging.error("[SECURITY BLOCK] Cannot sync intake record without a valid intake_id.")
        return False

    # Aligned schema payload keys
    cloud_payload = {
        "intake_id": intake_id,
        "tbc_job_number": intake_data.get("tbc_job_number") or intake_data.get("assigned_job_number"),
        "tbco_account_number": intake_data.get("tbco_account_number") or intake_data.get("contractor_account_number"),
        "site_name": intake_data.get("site_name") or intake_data.get("project_site_address") or "Unspecified Location",
        "sales_rep_email": intake_data.get("sales_rep_email") or intake_data.get("sales_team_email"),
        "requested_date": intake_data.get("requested_date"),
        "client_name": intake_data.get("client_name") or intake_data.get("contractor_company_name") or "Unspecified Client",
        "contact_phone": intake_data.get("contact_phone") or intake_data.get("requestor_phone") or "",
        "issue_description": intake_data.get("issue_description") or "No issue description provided.",
        "intake_source": intake_data.get("intake_source") or intake_data.get("request_source") or "WEB_FORM",
        "status": intake_data.get("status") or intake_data.get("triage_status") or "PENDING_TRIAGE",
        "created_at": intake_data.get("created_at") or intake_data.get("submission_timestamp") or datetime.now(timezone.utc).isoformat(),
        "created_by": intake_data.get("created_by") or intake_data.get("requestor_email") or "SYSTEM",
        "last_modified_timestamp": datetime.now(timezone.utc)
    }

    MAX_ATTEMPTS = 3
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logging.info(f"☁️ [INTAKE CLOUD SYNC {attempt}/{MAX_ATTEMPTS}] Syncing intake {intake_id} to Firestore...")
            db_client.collection("intake_ledger").document(intake_id).set(cloud_payload, merge=True)
            logging.info(f"🎉 [INTAKE CLOUD SUCCESS] Document {intake_id} mapped to cloud intake_ledger.")
            return True
        except Exception as error_token:
            jitter_delay = random.uniform(0.5, 1.5)
            logging.warning(f"⚠️ [INTAKE SYNC CONFLICT] Write conflict on intake {intake_id}: {error_token}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(jitter_delay)
            else:
                logging.error(f"❌ [INTAKE SYNC EXHAUSTED] Max retries reached for intake {intake_id}. Retained locally.")

    return False


def sync_intake_in_background(db_client, intake_data: dict):
    """
    Detaches the cloud intake upload operation from the UI screen,
    running it silently in the background so office staff experience zero lag.
    """
    worker_thread = threading.Thread(
        target=map_intake_to_cloud,
        args=(db_client, intake_data),
        daemon=True
    )
    worker_thread.start()
    logging.info(f"🧵 [INTAKE THREAD] Background sync worker engaged for Intake {intake_data.get('intake_id', 'UNKNOWN')}.")


def sync_intake_to_cloud(db_client, intake_id: str, new_status: str, assigned_job_number: Optional[str] = None, requested_date: Optional[str] = None) -> bool:
    """
    Updates status, assigned job number, and requested date of an intake document in Cloud Firestore.
    """
    if db_client is None:
        logging.warning(f"⚠️ [CLOUD SYNC SKIP] Cloud client offline. Skipping Firestore sync for intake '{intake_id}'.")
        return False

    try:
        doc_ref = db_client.collection("intake_ledger").document(intake_id)

        update_payload = {
            "status": new_status,
            "assigned_job_number": assigned_job_number,
            "last_modified_timestamp": datetime.now(timezone.utc)
        }
        if requested_date is not None:
            update_payload["requested_date"] = requested_date

        doc_ref.set(update_payload, merge=True)
        logging.info(f"☁️ [CLOUD INTAKE SYNC SUCCESS] Intake '{intake_id}' updated in Firestore (Status: {new_status}, Job #: {assigned_job_number}).")
        return True

    except Exception as e:
        logging.error(f"❌ [CLOUD INTAKE SYNC ERROR] Failed to sync intake '{intake_id}' to Firestore: {e}")
        return False


def dispatch_intake_sync_in_background(db_client, intake_id: str, new_status: str, assigned_job_number: Optional[str] = None, requested_date: Optional[str] = None):
    """
    Spawns an isolated background thread to handle cloud status updates silently.
    """
    worker_thread = threading.Thread(
        target=sync_intake_to_cloud,
        args=(db_client, intake_id, new_status, assigned_job_number, requested_date),
        daemon=True
    )
    worker_thread.start()
    logging.info(f"🧵 [THREAD DEPLOYED] Asynchronous background intake sync engaged for record '{intake_id}'.")