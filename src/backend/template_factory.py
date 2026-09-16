import logging
from typing import Dict, Any, Optional
from googleapiclient.discovery import build
from src.backend.drive_service import get_drive_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class GoogleDocTemplateFactory:
    """Handles template duplication and token replacement for production document compilation."""

    def __init__(self, drive_service=None, docs_service=None):
        self.drive_service = drive_service or get_drive_service()
        self._docs_service = docs_service

    @property
    def docs_service(self):
        """Lazy-loads the Google Docs API client using existing Drive service credentials."""
        if self._docs_service is None and self.drive_service is not None:
            try:
                creds = getattr(self.drive_service, '_credentials', None)
                if creds:
                    self._docs_service = build('docs', 'v1', credentials=creds)
            except Exception as e:
                logging.error(f"Failed to initialize Google Docs service client: {e}")
        return self._docs_service

    def duplicate_master_template(self, template_id: str, folder_id: str, new_file_name: str) -> Optional[str]:
        """Copies a master Google Doc template into a target Google Drive folder."""
        if not self.drive_service:
            logging.error("Drive service unavailable for template duplication.")
            return None

        try:
            body = {
                'name': new_file_name,
                'parents': [folder_id]
            }
            cloned_file = self.drive_service.files().copy(
                fileId=template_id,
                body=body
            ).execute()

            cloned_id = cloned_file.get('id')
            logging.info(f"📄 Successfully cloned template {template_id} -> New Document ID: {cloned_id}")
            return cloned_id
        except Exception as e:
            logging.error(f"Failed to duplicate master template: {e}")
            return None

    def parse_text_tokens(self, cloned_doc_id: str, tokens: Dict[str, str]) -> bool:
        """Replaces placeholder tokens (e.g., {{JOB_ID}}) in a Google Doc with actual values."""
        if not self.docs_service:
            logging.error("Docs API service unavailable for token parsing.")
            return False

        try:
            requests = [
                {
                    'replaceAllText': {
                        'containsText': {'text': key, 'matchCase': True},
                        'replaceText': str(val)
                    }
                }
                for key, val in tokens.items()
            ]

            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=cloned_doc_id,
                    body={'requests': requests}
                ).execute()
                logging.info(f"✏️ Applied {len(requests)} token replacements to Document ID: {cloned_doc_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to parse text tokens in doc {cloned_doc_id}: {e}")
            return False

    def _compile_production_document(self, job_id: str, folder_id: str, client_name: str, template_id: str = "MASTER_TEMPLATE_ID") -> Optional[str]:
        """Orchestrates document generation by cloning a template and filling in project metadata."""
        new_doc_name = f"Service_Report_{job_id}_{client_name}"
        cloned_id = self.duplicate_master_template(template_id, folder_id, new_doc_name)

        if cloned_id:
            tokens = {
                "{{JOB_ID}}": job_id,
                "{{CLIENT_NAME}}": client_name
            }
            self.parse_text_tokens(cloned_id, tokens)
            return cloned_id
        return None


if __name__ == "__main__":
    print("\n--- Verification Test: Template Factory ---")
    factory = GoogleDocTemplateFactory()
    print(f"Template Factory initialized cleanly. Drive client online: {factory.drive_service is not None}")