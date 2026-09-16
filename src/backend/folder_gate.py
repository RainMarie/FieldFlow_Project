import json
import logging
from google.oauth2 import service_account

try:
    from src.backend.db_manager import cred_manager
    from src.backend.sales_digest import MidnightSalesDigest
except ImportError:
    from db_manager import cred_manager
    from sales_digest import MidnightSalesDigest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def initialize_drive_auth():
    """Retrieves robot credentials and authorizes Google Drive access scopes."""
    firebase_config_raw = cred_manager.get_credential("Firebase", "master_service_account")
    if not firebase_config_raw:
        logging.error("Authentication critical failure: Master configuration missing.")
        return None
        
    config_dict = json.loads(firebase_config_raw)
    DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
    
    try:
        credentials = service_account.Credentials.from_service_account_info(config_dict, scopes=DRIVE_SCOPES)
        return credentials
    except Exception as e:
        logging.error(f"Failed to process service account mapping: {str(e)}")
        return None


def run_midnight_sales_digest_sweep() -> list:
    """Delegate wrapper routing directly to sales_digest.py module."""
    return MidnightSalesDigest().run_midnight_sales_digest_sweep()


def compile_and_lock_internal_broker_digest(digest_records: list) -> dict:
    """Delegate wrapper routing directly to sales_digest.py module."""
    return MidnightSalesDigest().compile_and_lock_internal_broker_digest(digest_records)


if __name__ == "__main__":
    print("--- Running Step 5.5.2 Local Verification Pipeline ---")
    
    MOCK_DAILY_RECORDS = [
        {
            "job_id": "JOB-5005",
            "tbc_job_number": "123456XX",
            "technician_email": "tech1@tombarrow.com",
            "sales_team_email": "sales_rep@tombarrow.com"
        },
        {
            "job_id": "JOB-5006",
            "tbc_job_number": "789101XX",
            "technician_email": "tech2@tombarrow.com",
            "sales_team_email": "external_customer@gmail.com"
        }
    ]
    
    secured_payload = compile_and_lock_internal_broker_digest(MOCK_DAILY_RECORDS)
    
    print("\n--- SECURED TELEMETRY PACKET OUTBOX ---")
    print(f"Subject: {secured_payload['subject']}")
    print(f"Verified Safe Recipient Outbox List: {secured_payload['verified_recipients']}")
    print("\nMessage Content Preview:")
    print(secured_payload['body'])