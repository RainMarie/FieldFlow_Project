import os
import json
import uuid
import logging
from datetime import datetime, timezone
from src.backend.calendar_service import GoogleCalendarService
from src.backend.db_manager import local_db, db as firestore_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def build_gcal_ticket_description(ticket_data: dict) -> str:
    """Formats structured key-value pairs for Google Calendar event descriptions."""
    job_type = ticket_data.get("request_type") or ticket_data.get("job_type") or "VFD Startup"
    project_name = ticket_data.get("project_name") or "Service Project"
    contractor = ticket_data.get("contractor_company_name") or "Valued Client"

    sc_first = ticket_data.get("project_site_contact_first_name") or ""
    sc_last = ticket_data.get("project_site_contact_last_name") or ""
    sc_name = f"{sc_first} {sc_last}".strip() or "N/A"
    sc_phone = ticket_data.get("project_site_contact_phone") or "N/A"

    rb_first = ticket_data.get("sales_rep_first_name") or ""
    rb_last = ticket_data.get("sales_rep_last_name") or ""
    rb_name = f"{rb_first} {rb_last}".strip() or ticket_data.get("sales_rep_email") or "Sales Representative"
    rb_phone = ticket_data.get("sales_rep_phone") or "N/A"

    issue_desc = ticket_data.get("issue_description") or "Service Request Dispatch"

    return (
        f"JOB TYPE: {job_type}\n"
        f"PROJECT: {project_name}\n"
        f"CONTRACTOR: {contractor}\n"
        f"SITE CONTACT: {sc_name}, {sc_phone}\n"
        f"REQUESTED BY: {rb_name}, {rb_phone}\n\n"
        f"DESCRIPTION: {issue_desc}"
    )


class GoogleCalendarManager:
    """Handles formatting and publishing appointment entries to Google Calendar safely."""

    def __init__(self, calendar_service: GoogleCalendarService = None):
        self.calendar_service = calendar_service or GoogleCalendarService()
        self.service = self.calendar_service.build_service()
        self.calendar_id = "primary"

    def publish_appointment(self, job_id: str, summary: str, location: str, description: str, start_iso: str, end_iso: str):
        """Generates loop-breaker token, updates local/cloud storage, and writes to Google Calendar."""
        if not self.service:
            logging.warning("Calendar API service offline. Skipping sync.")
            return False

        mutation_token = f"FF-MUT-{uuid.uuid4().hex[:8].upper()}"
        logging.info(f"🔄 Generated circuit breaker token {mutation_token} for Job {job_id}")

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE dispatches 
                    SET last_mutation_token = ? 
                    WHERE job_id = ?
                """, (mutation_token, job_id))
                conn.commit()
            logging.info(f"💾 Token saved to local SQLite for Job {job_id}")
        except Exception as e:
            logging.error(f"Failed to update token in local cache database: {e}")
            return False

        try:
            if firestore_db is not None:
                firestore_db.collection("dispatches").document(job_id).update({
                    "last_mutation_token": mutation_token,
                    "last_modified_timestamp": datetime.now(timezone.utc)
                })
                logging.info(f"☁️ Token synchronized to cloud Firestore for Job {job_id}")
        except Exception as e:
            logging.warning(f"Cloud database update deferred (offline/sandbox): {e}")

        event_payload = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {'dateTime': start_iso, 'timeZone': 'UTC'},
            'end': {'dateTime': end_iso, 'timeZone': 'UTC'},
            'extendedProperties': {
                'private': {
                    'Last_Mutation_Token': mutation_token
                }
            }
        }

        try:
            event = self.service.events().insert(calendarId=self.calendar_id, body=event_payload).execute()
            google_event_id = event.get('id')
            logging.info(f"🎉 [CALENDAR SUCCESS] Successfully written to Google Calendar! Event ID: {google_event_id}")

            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE dispatches 
                    SET report_metrics = json_set(report_metrics, '$.google_calendar_event_id', ?)
                    WHERE job_id = ?
                """, (google_event_id, job_id))
                conn.commit()

            return True
        except Exception as e:
            logging.error(f"Critical error communicating with Google Calendar API: {e}")
            return False


if __name__ == "__main__":
    print("\n--- Testing Step 3: Outbound Calendar Sync Payload Generation ---")
    manager = GoogleCalendarManager()
    manager.publish_appointment(
        job_id="JOB-5005",
        summary="Emergency Chiller Diagnostics",
        location="123 Main St, Tampa, FL",
        description="Technician dispatch from FieldFlow platform.",
        start_iso="2026-07-15T08:00:00Z",
        end_iso="2026-07-15T12:00:00Z"
    )