import smtplib
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from src.backend.db_manager import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class MidnightSalesDigest:
    """
    Batched background processor that aggregates daily finalized project 
    registrations and generates internal operational summaries.
    Protects Spark Free Tier quotas via direct server-side date bounds.
    """
    def __init__(self, corporate_domain: str = "tombarrow.com"):
        self.firestore_client = db
        self.allowed_domain = corporate_domain.lower()

    def fetch_daily_completed_jobs(self) -> List[Dict[str, Any]]:
        """Queries Cloud Firestore exclusively for dispatch items finalized within 24 hours."""
        completed_records = []
        if self.firestore_client is None:
            logging.warning("[DIGEST DATA SKIP] Firestore Client is offline. Aborting fetch loop.")
            return []
            
        try:
            now = datetime.now(timezone.utc)
            twenty_four_hours_ago = now - timedelta(hours=24)
            
            dispatches_ref = self.firestore_client.collection("dispatches")
            query = dispatches_ref.where("registration_status", "==", "Registration Complete") \
                                  .where("last_modified_timestamp", ">=", twenty_four_hours_ago) \
                                  .stream()
            
            for doc in query:
                data = doc.to_dict()
                completed_records.append({
                    "job_id": doc.id,
                    "job_number": data.get("tbc_job_number", "UNKNOWN"),
                    "technician": data.get("technician_email", "SYSTEM_ROBOT"),
                    "destination_sales_email": data.get("sales_team_email", "sales_triage@tombarrow.com")
                })
            
            logging.info(f"[QUOTAS REGISTERED] Efficiently parsed {len(completed_records)} server-filtered records.")
            return completed_records
        except Exception as e:
            logging.error(f"Critical error fetching daily transaction parameters: {str(e)}")
            return []

    def filter_internal_recipients(self, email_list: List[str]) -> List[str]:
        """Enforces Internal Broker domain rules to scrub unauthorized external emails."""
        sanitized_recipients = []
        domain_suffix = f"@{self.allowed_domain}"
        for email in email_list:
            clean_email = email.strip().lower()
            if clean_email.endswith(domain_suffix) or clean_email == "service@tbcotampaservice.com":
                sanitized_recipients.append(clean_email)
            else:
                logging.warning(f"🚫 ROUTING BLOCK: Intercepted non-corporate recipient: {clean_email}")
        return sanitized_recipients

    def compile_and_lock_internal_broker_digest(self, digest_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enforces Internal Broker security lock and constructs formatted summary payload."""
        logging.info("Internal Broker processing compilation layout filters...")
        secured_distribution_list = set()
        
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        email_body = "======================================================\n"
        email_body += f"FIELD-FLOW DAILY SUMMARY: MIDNIGHT SALES DIGEST ({date_str})\n"
        email_body += "======================================================\n\n"
        
        if not digest_records:
            email_body += "Zero assets or dispatches finalized throughout this operational window.\n"
        else:
            for index, record in enumerate(digest_records, 1):
                job_id = record.get("job_id", "UNKNOWN_ID")
                job_num = record.get("job_number", record.get("tbc_job_number", "UNKNOWN_NUM"))
                tech_email = record.get("technician", record.get("technician_email", "SYSTEM_ROBOT"))
                
                email_body += f"{index}. JOB ID: {job_id} | Accounting Job #: {job_num}\n"
                email_body += f"   Verified By Tech: {tech_email}\n"
                email_body += "   Status: [FINALIZED & SECURED IN G-DRIVE]\n\n"
                
                raw_email = record.get("destination_sales_email", record.get("sales_team_email", "service@tbcotampaservice.com"))
                target_email = raw_email.strip().lower()
                
                if target_email.endswith(f"@{self.allowed_domain}") or target_email == "service@tbcotampaservice.com":
                    secured_distribution_list.add(target_email)
                else:
                    logging.warning(f"🚫 ROUTING BLOCK: Intercepted and scrubbed email: {target_email}")
                    
        email_body += "======================================================\n"
        email_body += "Notice: This transmission is routed exclusively to internal personnel.\n"
        
        return {
            "subject": f"Midnight Sales Digest - {date_str}",
            "body": email_body,
            "verified_recipients": list(secured_distribution_list)
        }

    def run_midnight_sales_digest_sweep(self) -> List[Dict[str, Any]]:
        """Scans database for finalized records and returns manifest data."""
        return self.fetch_daily_completed_jobs()

    def compile_and_send_digest(self, raw_recipient_list: List[str]):
        """Aggregates daily records, applies domain filtering, and sends report."""
        completed_jobs = self.fetch_daily_completed_jobs()
        if not completed_jobs:
            logging.info("[DIGEST SWEEP] Zero jobs finalized today. Skipping email dispatch routine.")
            return

        safe_recipients = self.filter_internal_recipients(raw_recipient_list)
        if not safe_recipients:
            logging.error("[DIGEST ERROR] Cancelled: No authorized internal email destinations remain.")
            return

        secured_payload = self.compile_and_lock_internal_broker_digest(completed_jobs)
        
        msg = MIMEMultipart()
        msg['From'] = f"fieldflow-alerts@{self.allowed_domain}"
        msg['To'] = ", ".join(safe_recipients)
        msg['Subject'] = secured_payload["subject"]
        msg.attach(MIMEText(secured_payload["body"], 'plain'))

        try:
            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_pass = os.getenv("SMTP_PASS")

            if not smtp_user or not smtp_pass:
                logging.warning("[MAIL MOCK] Environment credentials missing. Displaying compiled payload:\n")
                print(secured_payload["body"])
                return

            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(msg['From'], safe_recipients, msg.as_string())
            server.quit()
            logging.info(f"[DIGEST DISPATCH] Sent batched sales summary to {len(safe_recipients)} recipient(s).")
        except Exception as e:
            logging.error(f"Failed to execute batch mail delivery routine: {str(e)}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING DOMAIN SHIELD INGESTION SEPARATIONS")
    print("="*60 + "\n")
    
    engine = MidnightSalesDigest()
    test_emails = ["sales_lead@tombarrow.com", "competitor_spy@yahoo.com"]
    sanitized_pool = engine.filter_internal_recipients(test_emails)
    print(f"Final Filtered Outbox Manifest: {sanitized_pool}")