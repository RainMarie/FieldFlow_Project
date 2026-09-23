"""
src/backend/drive_service.py
Google Drive integration module for FieldFlow. Handles Shared Drive folder provisioning,
file uploads with automatic thumbnail permission assignment, and receipt email notifications.
"""

import os
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

from src.backend.db_manager import cred_manager, local_db, db as firestore_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

ADMIN_EMAIL = "service@tbcotampaservice.com"
SHARED_DRIVE_PARENT_ID = os.getenv("SHARED_DRIVE_PARENT_ID", "0AFT7nUPO-vWvUk9PVA")


def get_drive_service():
    """Authenticates with Google Drive API using service account credentials."""
    try:
        raw_creds = cred_manager.get_credential("Firebase", "master_service_account")
        if not raw_creds:
            logging.error("Drive Service aborted: Credentials missing from vault.")
            return None

        creds_dict = json.loads(raw_creds)
        scopes = ['https://www.googleapis.com/auth/drive']
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        return build('drive', 'v3', credentials=credentials, cache_discovery=False)
    except Exception as e:
        logging.error(f"Failed to authenticate Google Drive service: {e}")
        return None


def create_project_drive_folder(job_number: str, project_name: str) -> Dict[str, str]:
    """Creates a project folder in the Shared Drive with fault-tolerant permission handling."""
    service = get_drive_service()
    folder_title = f"{job_number} - {project_name}"
    
    if not service:
        logging.warning("Drive service offline. Returning fallback mock drive ID.")
        return {
            "drive_id": f"FLD-GDRV-{job_number}",
            "drive_url": "https://drive.google.com/drive/my-drive",
            "registration_folder_id": f"FLD-REG-{job_number}"
        }

    try:
        # 1. Create Parent Project Folder in Target Shared Drive
        parent_metadata = {
            'name': folder_title,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [SHARED_DRIVE_PARENT_ID]
        }
        parent_folder = service.files().create(
            body=parent_metadata,
            fields='id, webViewLink',
            supportsAllDrives=True
        ).execute()

        parent_id = parent_folder.get('id')
        web_link = parent_folder.get('webViewLink')

        # 2a. Safely attempt link permissions (catch domain policy blocks)
        try:
            user_permission = {'type': 'anyone', 'role': 'reader'}
            service.permissions().create(
                fileId=parent_id,
                body=user_permission,
                fields='id',
                supportsAllDrives=True
            ).execute()
        except Exception as perm_err:
            logging.warning(f"Note: Public reader permission skipped due to domain policy: {perm_err}")

        # 2b. Safely attempt Admin Editor permissions
        try:
            admin_permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': ADMIN_EMAIL
            }
            service.permissions().create(
                fileId=parent_id,
                body=admin_permission,
                fields='id',
                sendNotificationEmail=False,
                supportsAllDrives=True
            ).execute()
        except Exception as admin_err:
            logging.warning(f"Note: Admin writer permission skipped: {admin_err}")

        # 3. Create Child 'registration' Subfolder
        reg_metadata = {
            'name': 'registration',
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        reg_folder = service.files().create(
            body=reg_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        reg_id = reg_folder.get('id')

        logging.info(f"Created Parent Project Folder in Shared Drive: '{folder_title}' (ID: {parent_id})")

        return {
            "drive_id": parent_id,
            "drive_url": web_link,
            "registration_folder_id": reg_id
        }

    except Exception as e:
        logging.error(f"Error creating Google Drive project structure: {e}")
        return {
            "drive_id": f"FLD-GDRV-{job_number}",
            "drive_url": "https://drive.google.com/drive/my-drive",
            "registration_folder_id": f"FLD-REG-{job_number}"
        }


def upload_files_to_drive_folder(folder_id: str, file_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Uploads local files into the specified Google Drive folder, applies public view permissions,
    and returns detailed file metadata including direct streamable thumbnail URLs[cite: 3].
    """
    service = get_drive_service()
    uploaded_files = []

    if not service or not folder_id or folder_id.startswith("FLD-"):
        logging.warning("Drive service or valid Folder ID unavailable. Skipping upload.")
        return uploaded_files

    for path in file_paths:
        if os.path.exists(path) and os.path.isfile(path):
            try:
                filename = os.path.basename(path)
                file_metadata = {'name': filename, 'parents': [folder_id]}
                media = MediaFileUpload(path, resumable=True)
                uploaded_file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink',
                    supportsAllDrives=True
                ).execute()

                file_id = uploaded_file.get('id')
                web_link = uploaded_file.get('webViewLink')

                # Grant public reader permission so Flet controls can stream direct thumbnail images
                try:
                    file_permission = {'type': 'anyone', 'role': 'reader'}
                    service.permissions().create(
                        fileId=file_id,
                        body=file_permission,
                        fields='id',
                        supportsAllDrives=True
                    ).execute()
                except Exception as perm_err:
                    logging.warning(f"Note: File permission grant skipped: {perm_err}")

                direct_photo_url = f"https://lh3.googleusercontent.com/d/{file_id}"

                uploaded_files.append({
                    "file_id": file_id,
                    "web_view_link": web_link,
                    "photo_url": direct_photo_url,
                    "file_name": filename
                })

                logging.info(f"Uploaded '{filename}' to Drive Folder ID '{folder_id}' (File ID: {file_id}).")
            except Exception as e:
                logging.error(f"Failed to upload file '{path}' to Drive: {e}")

    return uploaded_files


def send_receipt_email_with_drive_link(
    requestor_email: str,
    requestor_name: str,
    job_number: str,
    project_name: str,
    drive_url: str
) -> bool:
    """Sends a confirmation email containing the Drive folder link[cite: 3]."""
    if not requestor_email or "@" not in requestor_email:
        logging.warning("Invalid requestor email. Skipping email dispatch.")
        return False

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    subject = f"Service Request Receipt - Job #{job_number} ({project_name})"
    email_body = f"""Hello {requestor_name or 'Valued Client'},

Thank you for submitting your service request for Job #{job_number}.

Your Google Drive project folder link is ready below:
📂 {drive_url}

Best regards,
FieldFlow Service Team
Tom Barrow Company
"""

    msg = MIMEMultipart()
    msg['From'] = smtp_user if smtp_user else "service-alerts@tombarrow.com"
    msg['To'] = requestor_email
    msg['Subject'] = subject
    msg.attach(MIMEText(email_body, 'plain'))

    if not smtp_user or not smtp_pass:
        logging.warning("SMTP credentials unconfigured. Displaying email preview:\n")
        print("=" * 60)
        print(email_body)
        print("=" * 60)
        return True

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(msg['From'], [requestor_email], msg.as_string())
        server.quit()
        logging.info(f"Confirmation email sent to {requestor_email}.")
        return True
    except Exception as e:
        logging.error(f"Failed to send confirmation email: {e}")
        return False


def process_new_service_request_submittal(
    job_number: str,
    project_name: str,
    requestor_name: str,
    requestor_email: str,
    attached_file_paths: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Master pipeline wrapper: creates folder, uploads files, and emails receipt[cite: 3]."""
    drive_info = create_project_drive_folder(job_number, project_name)
    drive_id = drive_info["drive_id"]
    drive_url = drive_info["drive_url"]

    uploaded_files = []
    if attached_file_paths:
        uploaded_files = upload_files_to_drive_folder(drive_id, attached_file_paths)

    send_receipt_email_with_drive_link(
        requestor_email=requestor_email,
        requestor_name=requestor_name,
        job_number=job_number,
        project_name=project_name,
        drive_url=drive_url
    )

    drive_info["uploaded_files"] = uploaded_files
    drive_info["photo_url"] = uploaded_files[0]["photo_url"] if uploaded_files else ""
    return drive_info


def ensure_project_drive_folder(
    job_number: str,
    project_name: str,
    requestor_name: str = "",
    requestor_email: str = "",
    attached_file_paths: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Check-and-Reuse Drive folder pipeline with structured upload photo URL returning[cite: 3]."""
    clean_job_num = job_number.strip().upper()
    existing_drive_id = None

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT drive_id FROM projects WHERE tbc_job_number = ?", (clean_job_num,))
            row = cursor.fetchone()
            if row and row["drive_id"] and not str(row["drive_id"]).startswith("FLD-"):
                existing_drive_id = row["drive_id"]
    except Exception as e:
        logging.error(f"Error querying database for Job #{clean_job_num}: {e}")

    if existing_drive_id:
        logging.info(f"Reusing Drive folder for Job #{clean_job_num} ({existing_drive_id}).")
        uploaded_files = []
        if attached_file_paths:
            uploaded_files = upload_files_to_drive_folder(existing_drive_id, attached_file_paths)

        existing_drive_url = f"https://drive.google.com/drive/folders/{existing_drive_id}"
        if requestor_email:
            send_receipt_email_with_drive_link(requestor_email, requestor_name, clean_job_num, project_name, existing_drive_url)

        main_photo_url = uploaded_files[0]["photo_url"] if uploaded_files else ""
        return {
            "drive_id": existing_drive_id,
            "drive_url": existing_drive_url,
            "uploaded_files": uploaded_files,
            "photo_url": main_photo_url,
            "is_new_folder": False
        }

    logging.info(f"Provisioning new Shared Drive folder for Job #{clean_job_num}...")
    drive_info = process_new_service_request_submittal(
        job_number=clean_job_num,
        project_name=project_name,
        requestor_name=requestor_name,
        requestor_email=requestor_email,
        attached_file_paths=attached_file_paths
    )

    new_drive_id = drive_info.get("drive_id")

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO projects (tbc_job_number, project_name, drive_id, stage)
                VALUES (?, ?, ?, 'In Progress')
            """, (clean_job_num, project_name, new_drive_id))
            conn.commit()
    except Exception as e:
        logging.error(f"Failed to register project in local database: {e}")

    if firestore_db is not None:
        try:
            firestore_db.collection("projects").document(clean_job_num).set({
                "tbc_job_number": clean_job_num,
                "project_name": project_name,
                "drive_id": new_drive_id,
                "stage": "In Progress"
            }, merge=True)
        except Exception as e:
            logging.warning(f"Cloud project sync deferred: {e}")

    drive_info["is_new_folder"] = True
    return drive_info


def list_files_in_drive_folder(folder_id: str) -> List[Dict[str, str]]:
    """Lists active files in a specified Google Drive folder[cite: 3]."""
    service = get_drive_service()
    if not service or not folder_id or folder_id.startswith("FLD-"):
        logging.warning(f"Drive service or folder ID '{folder_id}' invalid. Skipping.")
        return []

    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, webViewLink, mimeType)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = results.get('files', [])
        logging.info(f"Retrieved {len(files)} file(s) from Drive folder ID '{folder_id}'.")
        return files
    except Exception as e:
        logging.error(f"Error fetching files from Drive folder {folder_id}: {e}")
        return []