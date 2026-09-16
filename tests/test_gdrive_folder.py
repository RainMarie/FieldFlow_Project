import os
import sys

# Dynamic path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from googleapiclient.discovery import build
from src.backend.folder_gate import initialize_drive_auth

# ⚠️ YOUR GOOGLE EMAIL ADDRESS FOR PERMISSION ACCESS
TARGET_USER_EMAIL = "service@tbcoTampaservice.com"

def run_gdrive_share_test():
    print("\n" + "="*65)
    print("🔑 FIELDFLOW: GOOGLE DRIVE CREATION & AUTO-SHARE TEST")
    print("="*65 + "\n")

    test_job_number = "990011XX"
    folder_name = f"PROJECT - {test_job_number}"

    print("1️⃣ Authenticating Service Account...")
    creds = initialize_drive_auth()
    if not creds:
        print("❌ Could not load Google Drive credentials.")
        return

    service = build('drive', 'v3', credentials=creds)

    # Step 1: Create the folder in Google Drive
    print(f"2️⃣ Creating Folder '{folder_name}'...")
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    drive_id = folder.get('id')
    print(f"   ✅ Folder Created! ID: {drive_id}")

    # Step 2: Grant permissions to your work email
    print(f"3️⃣ Sharing folder edit access with '{TARGET_USER_EMAIL}'...")
    try:
        user_permission = {
            'type': 'user',
            'role': 'writer',  # Full Editor access
            'emailAddress': TARGET_USER_EMAIL
        }
        service.permissions().create(
            fileId=drive_id,
            body=user_permission,
            fields='id'
        ).execute()
        print(f"   🎉 SUCCESS! Access permission granted to {TARGET_USER_EMAIL}")
    except Exception as perm_err:
        print(f"   ❌ Sharing Error: {perm_err}")

    drive_url = f"https://drive.google.com/drive/folders/{drive_id}"
    print("\n" + "="*65)
    print("🌐 DIRECT ACCESSIBLE GOOGLE DRIVE URL:")
    print(f"   👉 {drive_url}")
    print("="*65 + "\n")

if __name__ == "__main__":
    run_gdrive_share_test()