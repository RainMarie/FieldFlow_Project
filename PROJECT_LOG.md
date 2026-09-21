# FieldFlow Automated Progress Blueprint

## Directory: src/backend

### 📄 calendar_listener.py
**Defined Functions/Classes:**
- `def parse_gcal_description(description_text: str) -> dict:`
- `def __init__(self, interval_seconds: int = 10, calendar_service: GoogleCalendarService = None):`
- `def start_monitoring(self):`
- `def stop_monitoring(self):`
- `def _monitor_loop(self):`
- `def check_for_calendar_updates(self):`

### 📄 calendar_manager.py
**Defined Functions/Classes:**
- `def build_gcal_ticket_description(ticket_data: dict) -> str:`
- `def __init__(self, calendar_service: GoogleCalendarService = None):`
- `def publish_appointment(self, job_id: str, summary: str, location: str, description: str, start_iso: str, end_iso: str):`

### 📄 calendar_service.py
**Defined Functions/Classes:**
- `def __init__(self, service_name: str = "Firebase", secret_key: str = "master_service_account"):`
- `def build_service(self, scopes: list = None):`

### 📄 check_results.py
**Defined Functions/Classes:**
- `def verify_local_status():`

### 📄 cleanup_db_tags.py
**Defined Functions/Classes:**
- `def clean_legacy_database_tags():`

### 📄 db_manager.py
**Defined Functions/Classes:**
- `def __init__(self, vault_path: str = "local_vault.enc", secret_key_path: str = ".vault_key"):`
- `def _init_cipher(self) -> Fernet:`
- `def _read_vault(self) -> Dict[str, str]:`
- `def _write_vault(self, data: Dict[str, str]):`
- `def set_credential(self, service: str, username: str, secret: str):`
- `def get_credential(self, service: str, username: str) -> Optional[str]:`
- `def __init__(self, db_path: str = "tbc_local.db"):`
- `def get_connection(self):`
- `def init_sqlite_schema(self):`
- `def resolve_location(`

### 📄 drive_listener.py
**Defined Functions/Classes:**
- `def __init__(self, interval_seconds: int = 30, drive_service=None):`
- `def start(self):`
- `def stop(self):`
- `def _monitor_loop(self):`
- `def check_for_new_pdfs(self, folder_id: str) -> List[Dict[str, Any]]:`

### 📄 drive_service.py
**Defined Functions/Classes:**
- `def get_drive_service():`
- `def create_project_drive_folder(job_number: str, project_name: str) -> Dict[str, str]:`
- `def upload_files_to_drive_folder(folder_id: str, file_paths: List[str]) -> List[str]:`
- `def send_receipt_email_with_drive_link(`
- `def process_new_service_request_submittal(`
- `def ensure_project_drive_folder(`
- `def list_files_in_drive_folder(folder_id: str) -> List[Dict[str, str]]:`

### 📄 email_service.py
**Defined Functions/Classes:**
- `def get_sales_rep_email_for_dispatch(job_id: str) -> str:`
- `def send_dispatch_receipt_email(job_id: str, receipt_data: Dict[str, Any]) -> bool:`

### 📄 export_master_schema_matrix.py
**Defined Functions/Classes:**
- `def export_master_schema_matrix():`

### 📄 folder_gate.py
**Defined Functions/Classes:**
- `def initialize_drive_auth():`
- `def run_midnight_sales_digest_sweep() -> list:`
- `def compile_and_lock_internal_broker_digest(digest_records: list) -> dict:`

### 📄 lifecycle_rules.py
**Defined Functions/Classes:**
- `def validate_project_space_exists(tbc_job_number: str) -> Tuple[bool, str]:`
- `def validate_service_request_dispatched(request_id: str) -> Tuple[bool, str]:`
- `def validate_status_transition(current_status: str, target_status: str, job_type: str) -> Tuple[bool, str]:`
- `def validate_user_role_permission(user_email: str, required_action: str) -> Tuple[bool, str]:`
- `def validate_intake_form_data(form_data: Dict[str, Any]) -> Tuple[bool, str]:`
- `def validate_field_form_photos(photo_list: List[Any], required_count: int = 1) -> Tuple[bool, str]:`

### 📄 media_processor.py
**Defined Functions/Classes:**
- `def ensure_staging_perimeter():`
- `def compress_profile_a(input_image_path, filename):`
- `def compress_profile_b(input_image_path, filename):`
- `def process_media_in_background(profile_type, input_image_path, filename, on_success_callback=None):`
- `def worker():`
- `def purge_cached_media_file(filename):`

### 📄 run_automation_test.py
**Defined Functions/Classes:**
- `def verify_local_status():`

### 📄 sales_digest.py
**Defined Functions/Classes:**
- `def __init__(self, corporate_domain: str = "tombarrow.com"):`
- `def fetch_daily_completed_jobs(self) -> List[Dict[str, Any]]:`
- `def filter_internal_recipients(self, email_list: List[str]) -> List[str]:`
- `def compile_and_lock_internal_broker_digest(self, digest_records: List[Dict[str, Any]]) -> Dict[str, Any]:`
- `def run_midnight_sales_digest_sweep(self) -> List[Dict[str, Any]]:`
- `def compile_and_send_digest(self, raw_recipient_list: List[str]):`

### 📄 search_engine.py
**Defined Functions/Classes:**
- `def search_admin_portal(search_term: str) -> List[Dict[str, Any]]:`
- `def search_mobile_portal(search_term: str, tech_email: str) -> List[Dict[str, Any]]:`

### 📄 sync_engine.py
**Defined Functions/Classes:**
- `def map_local_dispatch_to_cloud(db_client, local_row: dict) -> bool:`
- `def dispatch_sync_in_background(db_client, local_row: dict):`
- `def map_intake_to_cloud(db_client, intake_data: dict) -> bool:`
- `def sync_intake_in_background(db_client, intake_data: dict):`

### 📄 template_factory.py
**Defined Functions/Classes:**
- `def __init__(self, drive_service=None, docs_service=None):`
- `def docs_service(self):`
- `def duplicate_master_template(self, template_id: str, folder_id: str, new_file_name: str) -> Optional[str]:`
- `def parse_text_tokens(self, cloned_doc_id: str, tokens: Dict[str, str]) -> bool:`
- `def _compile_production_document(self, job_id: str, folder_id: str, client_name: str, template_id: str = "MASTER_TEMPLATE_ID") -> Optional[str]:`

### 📄 test_callbacks.py
**Defined Functions/Classes:**
- `def run_callback_diagnostics():`

### 📄 test_intake_engine.py
**Defined Functions/Classes:**
- `def run_intake_test():`

### 📄 validators.py
**Defined Functions/Classes:**
- `def is_valid_tbc_job_number(job_number: str) -> bool:`
- `def validate_inspection_metrics(job_type: str, metrics: Dict[str, Any]) -> Tuple[bool, str]:`

### 📄 verify_automation_loop.py
**Defined Functions/Classes:**
- `def __init__(self):`
- `def check_for_new_pdfs(self, folder_id: str):`
- `def execute_live_drop_test():`

### 📄 verify_dispatch_transition.py
**Defined Functions/Classes:**
- `def run_dispatch_transition_test():`

### 📄 verify_system_end_to_end.py
**Defined Functions/Classes:**
- `def run_system_verification():`

## Directory: src/frontend

### 📄 admin_dashboard.py
**Defined Functions/Classes:**
- `def main(page: ft.Page):`
- `def on_page_disconnect(e):`
- `def show_toast_local(message: str, kind: str = "success"):`
- `def open_drive_local(e, folder_id):`
- `def on_global_date_selected(e):`
- `def trigger_date_picker(target_control):`
- `def get_tech_options():`
- `def get_contractor_options():`
- `def get_location_options():`
- `def get_salesperson_options():`

### 📄 calendar_component.py
**Defined Functions/Classes:**
- `def build_calendar_widget(page: ft.Page, on_ticket_select_callback):`
- `def fetch_google_calendar_events(year: int, month: int):`
- `def fetch_dispatches(fetch_gcal: bool = False):`
- `def get_status_color(status_str: str):`
- `def build_tag_chip(dispatch_data):`
- `def build_month_grid_view(dispatches):`
- `def build_agenda_list_view(dispatches):`
- `def build_technician_group_view(dispatches):`
- `def refresh_calendar(fetch_gcal: bool = False):`
- `def change_month(delta_months: int):`

### 📄 cards_component.py
**Defined Functions/Classes:**
- `def build_truncating_text(text_val: str, size: int = 11, bold: bool = False, color_token=None) -> ft.Text:`
- `def build_clickable_email_link(page: ft.Page, email_addr: str, display_name: str = "") -> ft.Text:`
- `def calculate_ticket_progress(status_string: str) -> tuple[str, str]:`
- `def build_project_image_control(photo_url_or_path: str, height: int = 120) -> ft.Control:`
- `def build_project_card(`
- `def handle_service_request_click(e):`
- `def handle_drive_click(e):`
- `def handle_edit_click(e):`
- `def build_standard_ticket_card(`
- `def build_site_asset_card(asset_data: dict, is_serviced: bool = False, on_click_action=None) -> ft.Container:`

### 📄 check_my_db.py
**Defined Functions/Classes:**
- `def inspect_database():`

### 📄 desktop_sandbox.py
**Defined Functions/Classes:**
- `def main(page: ft.Page):`

### 📄 details_component.py
**Defined Functions/Classes:**
- `def build_image_control(photo_url_or_path: str, height: int = 180) -> ft.Control:`
- `def build_project_detail_modal(`
- `def build_section_header(title_text: str, color_token=FieldFlowLightTheme.PINK_PRIMARY):`
- `def on_photo_picked(e: ft.FilePickerResultEvent):`
- `def on_docs_picked(e: ft.FilePickerResultEvent):`
- `def populate_project_data(proj_data, contractor_options=None, location_options=None, sales_options=None):`
- `def save_project_detail_edits(e):`
- `def build_ticket_detail_modal(`
- `def build_section_header(title_text: str, color_token=FieldFlowLightTheme.PINK_PRIMARY):`
- `def populate_ticket_data(req_data: dict, dispatch_data: dict = None):`

### 📄 form_sandbox.py
**Defined Functions/Classes:**
- `def main(page: ft.Page):`
- `def countdown_clock_worker():`
- `def handle_field_focus(e):`
- `def start_submit_sequence(e):`
- `def validate_evidence_locks():`
- `def upload_data_plate(e):`
- `def upload_control_screen(e):`
- `def handle_typing(e):`
- `def handle_save(e):`

### 📄 forms_component.py
**Defined Functions/Classes:**
- `def make_field(label_text: str, input_control: ft.Control, expand: bool = True) -> ft.Container:`
- `def on_contractor_blur_helper(tf_company: ft.TextField, tf_company_acct: ft.TextField, page: ft.Page):`
- `def build_project_creation_form(page: ft.Page, on_success_callback=None) -> ft.Control:`
- `def on_sales_email_blur(e):`
- `def on_photo_picked(e: ft.FilePickerResultEvent):`
- `def on_docs_picked(e: ft.FilePickerResultEvent):`
- `def clear_form(e=None):`
- `def submit_project_creation(e):`
- `def build_asset_registration_tool(`
- `def build_parts_master_form(page: ft.Page, on_success_callback=None) -> ft.Control:`

### 📄 main.py
**Defined Functions/Classes:**
- `def main(page: ft.Page):`
- `def evaluate_viewport_governance(e=None):`

### 📄 mobile_suite.py
**Defined Functions/Classes:**
- `def update_project_asset_details(tbc_job_number: str, old_serial: str, new_name: str, new_serial: str, new_model: str) -> bool:`
- `def log_part_usage_submission(job_id: str, sku: str, qty: float, is_unlisted: bool, description: str, cost: float) -> str:`
- `def main(page: ft.Page):`
- `def show_toast_local(message: str, kind: str = "success"):`
- `def open_drive_local(folder_id: str):`
- `def open_map_local(address: str):`
- `def render_viewport(content_item):`
- `def load_service_form_view(asset_data, job_data):`
- `def handle_service_form_submit(asset_serial, target_status, metrics_payload):`
- `def load_asset_info_detail_view(asset_data, job_data):`

### 📄 project_scheduler.py
**Defined Functions/Classes:**
- `def create_context_locked_scheduler(project_data: dict, on_scheduled_callback=None):`
- `def handle_confirm_schedule(e):`
- `def main(page: ft.Page):`

### 📄 searchable_input_component.py
**Defined Functions/Classes:**
- `def build_searchable_input(`
- `def select_option(item_data):`
- `def on_text_changed(e):`

### 📄 shared_utils.py
**Defined Functions/Classes:**
- `def show_toast(page: ft.Page, message: str, kind: str = "success") -> None:`
- `def find_any_local_logo() -> str:`
- `def get_base64_from_file(file_path: str):`
- `def open_drive_link(page: ft.Page, folder_id: str, show_toast_fn=None) -> None:`
- `def open_navigation_map(page: ft.Page, address: str) -> None:`

### 📄 sidecar_portal.py
**Defined Functions/Classes:**
- `def init_portal_database():`
- `def fetch_pending_tickets():`
- `def mark_warranty_registration_complete(tbc_job_number: str, registration_file_name: str) -> bool:`
- `def build_field_copy_card(`
- `def handle_copy_click(e):`
- `def main(page: ft.Page):`
- `def show_toast_local(message: str, kind: str = "success"):`
- `def on_registration_file_picked(e: ft.FilePickerResultEvent):`
- `def build_field_copy_desk(ticket):`
- `def refresh_desktop_portal_view():`

### 📄 technician_clock_component.py
**Defined Functions/Classes:**
- `def update_dispatch_status(job_identifier: str, new_status: str) -> bool:`
- `def record_travel_start(job_id: str, tech_email: str, travel_type: str = "Outbound") -> bool:`
- `def record_travel_arrival(job_id: str) -> bool:`
- `def finish_workday_lifecycle(job_id: str, job_type: str) -> str:`
- `def build_technician_clock(`
- `def handle_clock_click(e):`

### 📄 theme.py
**Defined Functions/Classes:**
- `def get_primary_button_style() -> ft.ButtonStyle:`
- `def get_secondary_button_style() -> ft.ButtonStyle:`
- `def get_card_shadow() -> list[ft.BoxShadow]:`
- `def get_toast_style(kind: str = "info") -> dict:`
- `def resolve_status_badge_colors(status_string: str) -> tuple[str, str]:`

### 📄 vfd_form_component.py
**Defined Functions/Classes:**
- `def build_vfd_service_form(`
- `def on_field_change(e):`
- `def make_compact_tf(label, value="", multiline=False, expand=False):`
- `def make_compact_dd(label, value, options, expand=False):`
- `def make_photo_box(label_text):`
- `def bind_photo_click(box, icon, text, key):`
- `def on_click(e):`
- `def assemble_vfd_payload():`
- `def assemble_gs_payload():`
- `def update_wizard_ui():`

