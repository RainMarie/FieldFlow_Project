import json
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class GoogleCalendarService:
    """Centralized service manager for Google Calendar API authentication."""

    def __init__(self, service_name: str = "Firebase", secret_key: str = "master_service_account"):
        self.service_name = service_name
        self.secret_key = secret_key

    def build_service(self, scopes: list = None):
        """Retrieves credentials securely from the vault and builds an authorized API client."""
        if scopes is None:
            scopes = ['https://www.googleapis.com/auth/calendar']

        from src.backend.db_manager import cred_manager
        raw_creds = cred_manager.get_credential(self.service_name, self.secret_key)
        if not raw_creds:
            logging.error("Google Calendar Service aborted: Master credentials missing from vault.")
            return None

        try:
            creds_dict = json.loads(raw_creds)
            credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
            # Passing cache_discovery=False prevents file_cache warning logs and eliminates network discovery delays
            return build('calendar', 'v3', credentials=credentials, cache_discovery=False)
        except Exception as e:
            logging.error(f"Failed to build Google Calendar service client: {e}")
            return None