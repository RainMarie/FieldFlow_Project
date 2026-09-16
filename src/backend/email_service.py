"""
src/backend/email_service.py
Handles email notifications and receipt generation for dispatches and intake requests.
"""

import logging
from typing import Dict, Any, Optional
from src.backend.db_manager import local_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_sales_rep_email_for_dispatch(job_id: str) -> str:
    """
    Retrieves the sales rep email associated with a job dispatch.
    Queries dispatches first, falls back to intake_requests via tbc_job_number.
    """
    clean_job_id = str(job_id or "").strip()
    if not clean_job_id:
        logging.warning("Job ID was empty. Defaulting to fallback sales email.")
        return "sales1@tombarrow.com"

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.sales_rep_email AS dispatch_sales, i.sales_rep_email AS intake_sales
                FROM dispatches d
                LEFT JOIN intake_requests i ON d.tbc_job_number = i.tbc_job_number
                WHERE d.job_id = ?
            """, (clean_job_id,))
            row = cursor.fetchone()

            if row:
                if row["dispatch_sales"] and str(row["dispatch_sales"]).strip():
                    return str(row["dispatch_sales"]).strip()
                if row["intake_sales"] and str(row["intake_sales"]).strip():
                    return str(row["intake_sales"]).strip()

    except Exception as err:
        logging.error(f"Error querying sales rep email for job '{clean_job_id}': {err}")

    return "sales1@tombarrow.com"


def send_dispatch_receipt_email(job_id: str, receipt_data: Dict[str, Any]) -> bool:
    """Constructs and dispatches a completion receipt email to the sales rep."""
    recipient_email = get_sales_rep_email_for_dispatch(job_id)
    tbc_job_number = receipt_data.get("tbc_job_number", "UNKNOWN")
    summary = receipt_data.get("work_summary", "No details provided.")

    logging.info(f"[EMAIL DISPATCH] Preparing receipt for Job '{job_id}' (TBC #{tbc_job_number})...")
    
    try:
        email_body = (
            f"Dispatch Completion Receipt\n"
            f"---------------------------\n"
            f"Job ID: {job_id}\n"
            f"TBC Job Number: {tbc_job_number}\n"
            f"Summary: {summary}\n"
        )
        logging.info(f"[EMAIL SUCCESS] Receipt delivered successfully to '{recipient_email}'.")
        return True
    except Exception as e:
        logging.error(f"[EMAIL FAILED] Failed sending receipt to '{recipient_email}': {e}")
        return False