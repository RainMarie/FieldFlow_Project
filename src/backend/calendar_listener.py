import os
import re
import json
import time
import logging
import threading
from datetime import datetime, timezone
from src.backend.calendar_service import GoogleCalendarService
from src.backend.db_manager import local_db, db as firestore_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def parse_gcal_description(description_text: str) -> dict:
    """Parses structured key-value pairs from a Google Calendar event description."""
    parsed = {
        "job_type": None,
        "issue_description": None,
        "site_contact_name": None,
        "site_contact_phone": None,
        "requested_by_name": None,
        "requested_by_phone": None
    }
    if not description_text:
        return parsed

    # Extract Job Type
    jt_match = re.search(r"JOB TYPE:\s*(.+)", description_text, re.IGNORECASE)
    if jt_match:
        parsed["job_type"] = jt_match.group(1).strip()

    # Extract Problem Description
    desc_match = re.search(r"DESCRIPTION:\s*(.+?)(?=\n\s*\n|\n[A-Z\s]+:|$)", description_text, re.DOTALL | re.IGNORECASE)
    if desc_match:
        parsed["issue_description"] = desc_match.group(1).strip()

    # Extract Site Contact Name and Phone
    sc_match = re.search(r"SITE CONTACT:\s*([^,\n]+)(?:,\s*([^\n]+))?", description_text, re.IGNORECASE)
    if sc_match:
        parsed["site_contact_name"] = sc_match.group(1).strip() if sc_match.group(1) else None
        parsed["site_contact_phone"] = sc_match.group(2).strip() if sc_match.group(2) else None

    # Extract Requested By Name and Phone
    rb_match = re.search(r"REQUESTED BY:\s*([^,\n]+)(?:,\s*([^\n]+))?", description_text, re.IGNORECASE)
    if rb_match:
        parsed["requested_by_name"] = rb_match.group(1).strip() if rb_match.group(1) else None
        parsed["requested_by_phone"] = rb_match.group(2).strip() if rb_match.group(2) else None

    return parsed


class GoogleCalendarListener:
    """Background worker polling Google Calendar and syncing updates to SQLite and Cloud Firestore."""

    def __init__(self, interval_seconds: int = 10, calendar_service: GoogleCalendarService = None):
        self.calendar_service = calendar_service or GoogleCalendarService()
        scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar'
        ]
        self.service = self.calendar_service.build_service(scopes=scopes)
        self.calendar_id = "primary"
        self.interval_seconds = interval_seconds
        self.is_running = False

    def start_monitoring(self):
        """Spawns the loop runner thread cleanly inside a background channel."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logging.info(f"Background Calendar Listener engaged. Pulse loop interval: {self.interval_seconds}s.")

    def stop_monitoring(self):
        """Gracefully spins down background execution loops."""
        self.is_running = False
        logging.info("Background Calendar Listener halted safely.")

    def _monitor_loop(self):
        """Continuous execution loop scanning active calendar matrices."""
        while self.is_running:
            try:
                self.check_for_calendar_updates()
            except Exception as e:
                logging.error(f"Error inside monitoring channel iteration: {e}")
            time.sleep(self.interval_seconds)

    def check_for_calendar_updates(self):
        """Scans recent Google Calendar events and updates local and cloud databases."""
        if not self.service:
            return

        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            maxResults=10,
            singleEvents=True,
            orderBy='updated'
        ).execute()

        events = events_result.get('items', [])

        for event in events:
            google_event_id = event.get('id')

            extended_props = event.get('extendedProperties', {})
            private_props = extended_props.get('private', {})
            google_token = private_props.get('Last_Mutation_Token')

            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT job_id, tbc_job_number, last_mutation_token 
                    FROM dispatches 
                    WHERE json_extract(report_metrics, '$.google_calendar_event_id') = ?
                """, (google_event_id,))
                local_record = cursor.fetchone()

            if not local_record:
                continue

            job_id = local_record['job_id']
            tbc_job_num = local_record['tbc_job_number']
            local_token = local_record['last_mutation_token']

            # Circuit breaker token comparison
            if google_token and google_token == local_token:
                continue

            logging.warning(f"[CIRCUIT BREAKER TRIGGERED] External manual modification spotted for Job {job_id}!")

            # Extract fields from event payload
            description_notes = event.get('description', '')
            location_val = event.get('location', '')
            start_payload = event.get('start', {})
            new_sched_time = start_payload.get('dateTime') or start_payload.get('date', '')
            if new_sched_time:
                new_sched_time = new_sched_time[:10]

            # Parse description fields
            parsed_fields = parse_gcal_description(description_notes)

            # Determine dispatch status keyword
            target_status = "Scheduled"
            if "Traveling" in description_notes:
                target_status = "Traveling"
            elif "In Progress" in description_notes:
                target_status = "In Progress"
            elif "Ready for Review" in description_notes:
                target_status = "Ready for Review"

            # 1. Update SQLite Dispatches
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE dispatches 
                        SET status = ?,
                            scheduled_time = ?,
                            job_type = COALESCE(?, job_type),
                            report_metrics = json_set(
                                report_metrics, 
                                '$.site_contact_name', ?,
                                '$.site_contact_phone', ?,
                                '$.requested_by_name', ?
                            ),
                            last_mutation_token = ?
                        WHERE job_id = ?
                    """, (
                        target_status,
                        new_sched_time,
                        parsed_fields['job_type'],
                        parsed_fields['site_contact_name'],
                        parsed_fields['site_contact_phone'],
                        parsed_fields['requested_by_name'],
                        google_token,
                        job_id
                    ))

                    # 2. Update SQLite Intake Requests
                    if parsed_fields['issue_description']:
                        cursor.execute("""
                            UPDATE intake_requests
                            SET issue_description = ?
                            WHERE tbc_job_number = ?
                        """, (parsed_fields['issue_description'], tbc_job_num))

                    # 3. Update SQLite Locations
                    if location_val and parsed_fields['site_contact_name']:
                        cursor.execute("""
                            UPDATE locations
                            SET primary_contact = ?,
                                contact_phone = ?
                            WHERE site_name = ?
                        """, (parsed_fields['site_contact_name'], parsed_fields['site_contact_phone'], location_val))

                    conn.commit()
                logging.info(f"SQLite updated smoothly for Job {job_id}.")
            except Exception as e:
                logging.error(f"Failed to update local cache during inbound sync: {e}")

            # 4. Update Cloud Firestore
            try:
                if firestore_db is not None:
                    firestore_db.collection("dispatches").document(job_id).update({
                        "status": target_status,
                        "scheduled_time": new_sched_time,
                        "job_type": parsed_fields['job_type'] or "General Service",
                        "site_contact_name": parsed_fields['site_contact_name'],
                        "site_contact_phone": parsed_fields['site_contact_phone'],
                        "last_mutation_token": google_token,
                        "last_modified_timestamp": datetime.now(timezone.utc)
                    })

                    if parsed_fields['issue_description']:
                        intake_docs = firestore_db.collection("intake_ledger").where("tbc_job_number", "==", tbc_job_num).stream()
                        for doc in intake_docs:
                            doc.reference.update({"issue_description": parsed_fields['issue_description']})

                    logging.info(f"Cloud Firestore synchronized for Job {job_id}.")
            except Exception as e:
                logging.warning(f"Cloud update deferred: {e}")


if __name__ == "__main__":
    print("\n--- Running Standalone Verification Test for Inbound Calendar Listener ---")
    listener = GoogleCalendarListener(interval_seconds=3)
    listener.start_monitoring()
    try:
        time.sleep(4)
    except KeyboardInterrupt:
        pass
    listener.stop_monitoring()