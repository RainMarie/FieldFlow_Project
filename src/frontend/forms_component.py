"""
src/frontend/forms_component.py
Consolidated data entry and intake form module for FieldFlow using standardized key names.
"""

import os
import sys
import time
import logging
import flet as ft

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.frontend.theme import FieldFlowLightTheme
from src.backend.db_manager import (
    local_db, 
    db as firestore_db, 
    resolve_location, 
    resolve_contractor
)
from src.backend.drive_service import ensure_project_drive_folder
from src.frontend.shared_utils import find_any_local_logo, show_toast

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

VALID_TEAM_CODES = [
    "TC", "TI", "TJ", "TK", "TN", "TO", "TS", "TT", "TY",
    "FH", "FM", "FW", "JY", "JB", "JC", "JG", "JJ", "JK",
    "PJ", "PL", "PY", "RB", "RC", "RD", "RJ", "RO", "RQ", "RT", "RU"
]


def make_field(label_text: str, input_control: ft.Control, expand: bool = True) -> ft.Container:
    return ft.Container(
        content=ft.Column([
            ft.Text(label_text, size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            input_control
        ], spacing=2, tight=True),
        expand=expand
    )


# =========================================================================
# 1. PROJECT CREATION FORM COMPONENT
# =========================================================================

def build_project_creation_form(page: ft.Page, on_success_callback=None) -> ft.Control:
    # 1. Core Project Controls
    tf_job_num = ft.TextField(label="TBCo Job #*", hint_text="e.g. 287027TI", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_proj_name = ft.TextField(label="Project Name*", hint_text="e.g. Tower B Renovation", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_site_name = ft.TextField(label="Campus / Site Name*", hint_text="e.g. Tampa General Hospital Campus", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_po_num = ft.TextField(label="PO #", hint_text="e.g. PO-88210", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # 2. Location & Address Controls
    tf_street_1 = ft.TextField(label="Street Address 1*", hint_text="e.g. 500 Medical Way", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_street_2 = ft.TextField(label="Street Address 2 / Suite", hint_text="e.g. Suite 300", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_city = ft.TextField(label="City*", hint_text="e.g. Tampa", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_state = ft.TextField(label="State*", hint_text="e.g. FL", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_postal_code = ft.TextField(label="Postal Code*", hint_text="e.g. 33602", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_country = ft.TextField(label="Country", value="US", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_company = ft.TextField(label="Contractor Name*", hint_text="e.g. Acme Mechanical", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_company_acct = ft.TextField(label="Company Account #", hint_text="e.g. ACME-0091", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # 3. Project Site Contact Controls
    tf_contact_first = ft.TextField(label="Site Contact First Name", hint_text="e.g. Alex", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_last = ft.TextField(label="Site Contact Last Name", hint_text="e.g. Smith", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_email = ft.TextField(label="Site Contact Email", hint_text="e.g. asmith@site.com", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_phone = ft.TextField(label="Site Contact Phone", hint_text="e.g. 813-555-0199", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # 4. Sales Rep Controls
    tf_sales_first = ft.TextField(label="Sales Rep First Name", hint_text="e.g. Jane", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_last = ft.TextField(label="Sales Rep Last Name", hint_text="e.g. Doe", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_email = ft.TextField(label="Sales Rep Email", hint_text="e.g. jdoe@tombarrow.com", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_phone = ft.TextField(label="Sales Rep Phone", hint_text="e.g. 813-555-0144", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    dd_team_code = ft.Dropdown(label="Team Code", options=[ft.dropdown.Option(code) for code in VALID_TEAM_CODES], border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # 5. File Upload Controls & Status
    staged_photo_path = {"value": ""}
    staged_documents = []

    photo_status_txt = ft.Text("No Custom Picture Selected (Using Default Logo)", size=11, color=FieldFlowLightTheme.TEXT_MUTED)
    docs_status_txt = ft.Text("No Staged Documents", size=11, color=FieldFlowLightTheme.TEXT_MUTED)

    def on_photo_picked(e: ft.FilePickerResultEvent):
        if e.files:
            selected_file = e.files[0]
            staged_photo_path["value"] = selected_file.path if hasattr(selected_file, 'path') and selected_file.path else selected_file.name
            photo_status_txt.value = f"Photo Staged: {os.path.basename(staged_photo_path['value'])}"
            photo_status_txt.color = FieldFlowLightTheme.PRIMARY_GREEN
            page.update()

    def on_docs_picked(e: ft.FilePickerResultEvent):
        if e.files:
            staged_documents.clear()
            for f in e.files:
                staged_documents.append(f.path if hasattr(f, 'path') and f.path else f.name)
            docs_status_txt.value = f"{len(staged_documents)} Document(s) Staged"
            docs_status_txt.color = FieldFlowLightTheme.PRIMARY_GREEN
            page.update()

    photo_picker = ft.FilePicker(on_result=on_photo_picked)
    docs_picker = ft.FilePicker(on_result=on_docs_picked)
    page.overlay.extend([photo_picker, docs_picker])

    btn_upload_photo = ft.OutlinedButton(
        "Select Photo",
        icon=ft.icons.IMAGE,
        style=FieldFlowLightTheme.get_secondary_button_style(),
        on_click=lambda _: photo_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
    )
    btn_upload_docs = ft.OutlinedButton(
        "Upload Documents",
        icon=ft.icons.ATTACH_FILE,
        style=FieldFlowLightTheme.get_secondary_button_style(),
        on_click=lambda _: docs_picker.pick_files(allow_multiple=True)
    )

    def clear_form(e=None):
        tf_job_num.value = ""
        tf_proj_name.value = ""
        tf_site_name.value = ""
        tf_po_num.value = ""
        tf_company.value = ""
        tf_company_acct.value = ""

        tf_street_1.value = ""
        tf_street_2.value = ""
        tf_city.value = ""
        tf_state.value = ""
        tf_postal_code.value = ""
        tf_country.value = "US"

        tf_contact_first.value = ""
        tf_contact_last.value = ""
        tf_contact_email.value = ""
        tf_contact_phone.value = ""

        tf_sales_first.value = ""
        tf_sales_last.value = ""
        tf_sales_email.value = ""
        tf_sales_phone.value = ""
        dd_team_code.value = None

        staged_photo_path["value"] = ""
        staged_documents.clear()

        photo_status_txt.value = "No Custom Picture Selected (Using Default Logo)"
        photo_status_txt.color = FieldFlowLightTheme.TEXT_MUTED
        docs_status_txt.value = "No Staged Documents"
        docs_status_txt.color = FieldFlowLightTheme.TEXT_MUTED

        if page: page.update()

    def submit_project_creation(e):
        if not tf_job_num.value or not tf_proj_name.value or not tf_company.value or not tf_street_1.value or not tf_city.value or not tf_state.value:
            show_toast(page, "❌ Job #, Project Name, Company, Street Address, City, and State are required!", kind="error")
            return

        job_num = tf_job_num.value.strip().upper()
        p_name = tf_proj_name.value.strip()
        s_name = tf_site_name.value.strip() if tf_site_name.value else p_name
        company = tf_company.value.strip()
        acct_no = tf_company_acct.value.strip().upper() if tf_company_acct.value else f"CON-{job_num[:4]}"

        street_1 = tf_street_1.value.strip()
        street_2 = tf_street_2.value.strip() if tf_street_2.value else ""
        city_val = tf_city.value.strip()
        state_val = tf_state.value.strip()
        zip_val = tf_postal_code.value.strip() if tf_postal_code.value else ""
        country_val = tf_country.value.strip() if tf_country.value else "US"

        clean_site = resolve_location(s_name, street_1, street_2, city_val, state_val, zip_val, country_val)
        clean_acct = resolve_contractor(acct_no, company)

        # Automatically Provision Google Drive Folder inside Shared Drive
        drive_info = ensure_project_drive_folder(
            job_number=job_num,
            project_name=p_name,
            requestor_name=f"{tf_sales_first.value} {tf_sales_last.value}".strip(),
            requestor_email=tf_sales_email.value.strip().lower() if tf_sales_email.value else "",
            attached_file_paths=staged_documents
        )
        drive_id = drive_info.get("drive_id", f"FLD-GDRV-{job_num}")

        # Complete Payload for Cloud Storage
        proj_payload = {
            "tbc_job_number": job_num,
            "site_name": clean_site,
            "tbco_account_number": clean_acct,
            "project_name": p_name,
            "contractor_name": company,
            "contractor_company_name": company,
            "street_address_1": street_1,
            "street_address_2": street_2,
            "city": city_val,
            "state": state_val,
            "postal_code": zip_val,
            "country": country_val,
            "project_site_contact_first_name": tf_contact_first.value.strip() if tf_contact_first.value else "",
            "project_site_contact_last_name": tf_contact_last.value.strip() if tf_contact_last.value else "",
            "project_site_contact_email": tf_contact_email.value.strip().lower() if tf_contact_email.value else "",
            "project_site_contact_phone": tf_contact_phone.value.strip() if tf_contact_phone.value else "",
            "sales_rep_first_name": tf_sales_first.value.strip() if tf_sales_first.value else "",
            "sales_rep_last_name": tf_sales_last.value.strip() if tf_sales_last.value else "",
            "sales_rep_email": tf_sales_email.value.strip().lower() if tf_sales_email.value else "",
            "sales_rep_phone": tf_sales_phone.value.strip() if tf_sales_phone.value else "",
            "team_code": dd_team_code.value if dd_team_code.value else "",
            "drive_id": drive_id,
            "stage": "In Progress"
        }

        # SQLite Insert matching STRICT 6-column schema
        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO projects (
                        tbc_job_number, site_name, tbco_account_number, project_name, drive_id, stage
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    job_num, clean_site, clean_acct, p_name, drive_id, "In Progress"
                ))
                conn.commit()
        except Exception as sql_err:
            logging.error(f"SQLite project insert error: {sql_err}")

        # Sync complete payload to Cloud Firestore
        if firestore_db is not None:
            try:
                firestore_db.collection("projects").document(job_num).set(proj_payload, merge=True)
            except Exception as fs_err:
                logging.error(f"Firestore project insert error: {fs_err}")

        show_toast(page, f"🎉 Project #{job_num} created successfully!", kind="success")
        clear_form()

        if on_success_callback:
            on_success_callback(proj_payload)

    form_container = ft.Container(
        content=ft.Column([
            ft.Row([tf_job_num, tf_proj_name], spacing=10),
            ft.Row([tf_site_name, tf_po_num], spacing=10),
            ft.Row([tf_street_1, tf_street_2], spacing=10),
            ft.Row([tf_city, tf_state, tf_postal_code, tf_country], spacing=8),
            ft.Row([tf_company, tf_company_acct], spacing=10),
            ft.Row([tf_contact_first, tf_contact_last], spacing=10),
            ft.Row([tf_contact_email, tf_contact_phone], spacing=10),
            ft.Row([tf_sales_first, tf_sales_last], spacing=10),
            ft.Row([tf_sales_email, tf_sales_phone, dd_team_code], spacing=10),
            ft.Row([btn_upload_photo, photo_status_txt], spacing=10),
            ft.Row([btn_upload_docs, docs_status_txt], spacing=10),
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.ElevatedButton("Create Project", icon=ft.icons.FOLDER, style=FieldFlowLightTheme.get_primary_button_style(), on_click=submit_project_creation)
        ], spacing=10, scroll=ft.ScrollMode.AUTO, tight=True),
        padding=10
    )

    form_container.clear_form = clear_form
    form_container.submit_form = submit_project_creation

    return form_container


# =========================================================================
# 2. ASSET REGISTRATION TOOL COMPONENT
# =========================================================================

def build_asset_registration_tool(
    job_data: dict,
    on_proceed_callback,
    on_back_callback,
    show_toast_fn,
    page: ft.Page
) -> ft.Column:
    tbc_job_num = str(job_data.get("tbc_job_number", "889900XX"))

    search_input_field = ft.TextField(label="Search Equipment Serial Number...", prefix_icon=ft.icons.SEARCH, border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    serial_field_confirm = ft.TextField(label="Asset Serial Number*", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    model_field_confirm = ft.TextField(label="Asset Model Number", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    name_field_confirm = ft.TextField(label="Equipment Name / Tag*", border_color=FieldFlowLightTheme.ACCENT_BLUE)

    tf_manufacturer = ft.TextField(label="Manufacturer", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    dd_serves = ft.Dropdown(label="Serves", options=[ft.dropdown.Option("Air Handler"), ft.dropdown.Option("Fan"), ft.dropdown.Option("Chiller"), ft.dropdown.Option("Pump")], border_color=FieldFlowLightTheme.ACCENT_BLUE)

    register_btn = ft.ElevatedButton("➕ Register Asset", style=FieldFlowLightTheme.get_primary_button_style())

    return ft.Column([
        ft.Row([ft.TextButton("<- Back", on_click=on_back_callback)]),
        ft.Text(f"Asset Registration for Job #{tbc_job_num}", size=18, weight=ft.FontWeight.BOLD),
        search_input_field,
        name_field_confirm, serial_field_confirm, model_field_confirm,
        ft.Row([tf_manufacturer, dd_serves], spacing=10),
        register_btn
    ], spacing=10)


# =========================================================================
# 3. MASTER CATALOG FORMS COMPONENT
# =========================================================================

def build_parts_master_form(page: ft.Page, on_success_callback=None) -> ft.Control:
    tf_sku = ft.TextField(hint_text="e.g. SKU-VALVE-01", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_manufacturer = ft.TextField(hint_text="e.g. Honeywell", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_description = ft.TextField(hint_text="e.g. 2-Way Control Valve 24V", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_unit_cost = ft.TextField(hint_text="e.g. 150.00", border_color=FieldFlowLightTheme.ACCENT_BLUE, value="0.00")

    def submit_part(e):
        sku_val = tf_sku.value.strip().upper() if tf_sku.value else ""
        desc_val = tf_description.value.strip() if tf_description.value else ""
        if not sku_val or not desc_val:
            show_toast(page, "SKU and Description are required!", kind="error")
            return

        part_payload = {"sku": sku_val, "manufacturer": tf_manufacturer.value, "part_description": desc_val, "unit_cost": float(tf_unit_cost.value or 0)}

        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO parts_master VALUES (?, ?, ?, ?)", (sku_val, tf_manufacturer.value, desc_val, float(tf_unit_cost.value or 0)))
            conn.commit()

        if firestore_db is not None:
            firestore_db.collection("parts_master").document(sku_val).set(part_payload, merge=True)

        show_toast(page, f"🎉 Part '{sku_val}' saved!", kind="success")
        if on_success_callback: on_success_callback(part_payload)

    return ft.Container(content=ft.Column([tf_sku, tf_manufacturer, tf_description, tf_unit_cost, ft.ElevatedButton("Save Part", on_click=submit_part)], spacing=10))


def build_manufacturer_form(page: ft.Page, on_success_callback=None) -> ft.Control:
    tf_mfr_id = ft.TextField(hint_text="e.g. MFR-HW", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_company = ft.TextField(hint_text="e.g. Honeywell", border_color=FieldFlowLightTheme.ACCENT_BLUE)

    def submit_mfr(e):
        if not tf_mfr_id.value or not tf_company.value:
            show_toast(page, "ID and Company required!", kind="error")
            return

        payload = {"manufacturer_id": tf_mfr_id.value, "company_name": tf_company.value}
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO manufacturers (manufacturer_id, company_name) VALUES (?, ?)", (tf_mfr_id.value, tf_company.value))
            conn.commit()

        if firestore_db is not None:
            firestore_db.collection("manufacturers").document(tf_mfr_id.value).set(payload, merge=True)

        show_toast(page, f"🎉 Manufacturer saved!", kind="success")
        if on_success_callback: on_success_callback(payload)

    return ft.Container(content=ft.Column([tf_mfr_id, tf_company, ft.ElevatedButton("Save Vendor", on_click=submit_mfr)], spacing=10))


def build_truck_form(page: ft.Page, get_tech_options_fn=None, on_success_callback=None) -> ft.Control:
    tf_truck_id = ft.TextField(hint_text="e.g. TRUCK-01", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_plate = ft.TextField(hint_text="e.g. FL-88021", border_color=FieldFlowLightTheme.ACCENT_BLUE)

    def submit_truck(e):
        if not tf_truck_id.value:
            show_toast(page, "Truck ID required!", kind="error")
            return

        payload = {"truck_id": tf_truck_id.value, "truck_number": tf_plate.value}
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO trucks (truck_id, truck_number) VALUES (?, ?)", (tf_truck_id.value, tf_plate.value))
            conn.commit()

        if firestore_db is not None:
            firestore_db.collection("trucks").document(tf_truck_id.value).set(payload, merge=True)

        show_toast(page, f"🎉 Truck saved!", kind="success")
        if on_success_callback: on_success_callback(payload)

    return ft.Container(content=ft.Column([tf_truck_id, tf_plate, ft.ElevatedButton("Save Truck", on_click=submit_truck)], spacing=10))


def build_master_forms(page: ft.Page, get_tech_options_fn=None, on_success_callback=None) -> ft.Control:
    return ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Parts Catalog", content=build_parts_master_form(page, on_success_callback)),
            ft.Tab(text="Manufacturers", content=build_manufacturer_form(page, on_success_callback)),
            ft.Tab(text="Fleet Trucks", content=build_truck_form(page, get_tech_options_fn, on_success_callback)),
        ]
    )


# =========================================================================
# 4. SERVICE TICKET INTAKE FORM COMPONENT
# =========================================================================

def build_service_intake_form(
    page: ft.Page,
    trigger_date_picker_fn=None,
    on_success_callback=None,
    get_tech_options_fn=None
) -> ft.Control:
    """Form to submit new service intake requests using standardized field names across all layers."""
    
    tf_sales_first = ft.TextField(label="Sales Rep First Name*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_last = ft.TextField(label="Sales Rep Last Name*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_email = ft.TextField(label="Sales Rep Email*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_phone = ft.TextField(label="Sales Rep Phone", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    dd_team_code = ft.Dropdown(label="Team Code*", options=[ft.dropdown.Option(c) for c in VALID_TEAM_CODES], border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_job_num = ft.TextField(label="TBCo Job #*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_company = ft.TextField(label="Contractor / Client Name*", hint_text="e.g. Acme Mechanical", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_site_name = ft.TextField(label="Campus / Site Name*", hint_text="e.g. Tampa General Hospital Campus", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_proj_name = ft.TextField(label="Project Name*", hint_text="e.g. Tower B Renovation", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_street_1 = ft.TextField(label="Street Address 1*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_street_2 = ft.TextField(label="Street Address 2 / Unit", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_city = ft.TextField(label="City*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_state = ft.TextField(label="State*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_postal = ft.TextField(label="Postal Code*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_country = ft.TextField(label="Country", value="US", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_contact_first = ft.TextField(label="Project Site Contact First Name", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_last = ft.TextField(label="Project Site Contact Last Name", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_email = ft.TextField(label="Project Site Contact Email", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_phone = ft.TextField(label="Project Site Contact Phone", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    dd_request_type = ft.Dropdown(
        label="Request Type*",
        options=[
            ft.dropdown.Option("VFD Startup"),
            ft.dropdown.Option("Troubleshooting & Repair"),
            ft.dropdown.Option("Warranty Registration"),
            ft.dropdown.Option("Preventative Maintenance")
        ],
        value="VFD Startup",
        border_color=FieldFlowLightTheme.ACCENT_BLUE,
        expand=True
    )
    tf_issue = ft.TextField(label="Issue Description*", multiline=True, min_lines=2, max_lines=4, border_color=FieldFlowLightTheme.ACCENT_BLUE)

    tech_options = get_tech_options_fn() if get_tech_options_fn else []
    dd_technician = ft.Dropdown(label="Assigned Technician", options=tech_options, border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_scheduled_time = ft.TextField(label="Scheduled Date & Time Assigned", hint_text="e.g. 2026-09-20 09:00", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    staged_documents = []
    docs_status_txt = ft.Text("No Staged Documents", size=11, color=FieldFlowLightTheme.TEXT_MUTED)

    def on_docs_picked(e: ft.FilePickerResultEvent):
        if e.files:
            staged_documents.clear()
            for f in e.files:
                staged_documents.append(f.path if hasattr(f, 'path') and f.path else f.name)
            docs_status_txt.value = f"{len(staged_documents)} Document(s) Staged"
            docs_status_txt.color = FieldFlowLightTheme.PRIMARY_GREEN
            if page:
                page.update()

    docs_picker = ft.FilePicker(on_result=on_docs_picked)
    if docs_picker not in page.overlay:
        page.overlay.append(docs_picker)

    def populate_data(proj_data: dict):
        if not isinstance(proj_data, dict):
            return

        tf_sales_first.value = proj_data.get("sales_rep_first_name") or proj_data.get("sales_first_name", "")
        tf_sales_last.value = proj_data.get("sales_rep_last_name") or proj_data.get("sales_last_name", "")
        tf_sales_email.value = proj_data.get("sales_rep_email") or proj_data.get("sales_email", "")
        tf_sales_phone.value = proj_data.get("sales_rep_phone") or proj_data.get("sales_phone", "")
        dd_team_code.value = proj_data.get("team_code") or proj_data.get("sales_team", None)

        tf_job_num.value = proj_data.get("tbc_job_number", "")
        tf_proj_name.value = proj_data.get("project_name", "")
        tf_company.value = proj_data.get("contractor_company_name") or proj_data.get("contractor_name") or proj_data.get("company_name", "")
        tf_site_name.value = proj_data.get("site_name", "")

        tf_street_1.value = proj_data.get("street_address_1", "")
        tf_street_2.value = proj_data.get("street_address_2", "")
        tf_city.value = proj_data.get("city", "")
        tf_state.value = proj_data.get("state", "")
        tf_postal.value = proj_data.get("postal_code", "")
        tf_country.value = proj_data.get("country", "US")

        tf_contact_first.value = proj_data.get("project_site_contact_first_name") or proj_data.get("pm_first_name", "")
        tf_contact_last.value = proj_data.get("project_site_contact_last_name") or proj_data.get("pm_last_name", "")
        tf_contact_email.value = proj_data.get("project_site_contact_email") or proj_data.get("pm_email", "")
        tf_contact_phone.value = proj_data.get("project_site_contact_phone") or proj_data.get("pm_phone", "")

        if page:
            page.update()

    def clear_form(e=None):
        tf_sales_first.value = ""
        tf_sales_last.value = ""
        tf_sales_email.value = ""
        tf_sales_phone.value = ""
        dd_team_code.value = None

        tf_job_num.value = ""
        tf_company.value = ""
        tf_site_name.value = ""
        tf_proj_name.value = ""

        tf_street_1.value = ""
        tf_street_2.value = ""
        tf_city.value = ""
        tf_state.value = ""
        tf_postal.value = ""
        tf_country.value = "US"

        tf_contact_first.value = ""
        tf_contact_last.value = ""
        tf_contact_email.value = ""
        tf_contact_phone.value = ""

        dd_request_type.value = "VFD Startup"
        tf_issue.value = ""
        dd_technician.value = None
        tf_scheduled_time.value = ""
        staged_documents.clear()
        docs_status_txt.value = "No Staged Documents"
        docs_status_txt.color = FieldFlowLightTheme.TEXT_MUTED

        if page: page.update()

    def submit_service_request(e):
        if not tf_job_num.value or not tf_site_name.value or not tf_proj_name.value or not tf_street_1.value or not tf_city.value or not tf_sales_first.value:
            show_toast(page, "❌ Job #, Campus Name, Project Name, Street, City, and Sales Rep First Name are required!", kind="error")
            return

        req_id = f"REQ-{int(time.time())}"
        triage_val = "Dispatched" if (dd_technician.value and dd_technician.value.strip()) else "Unassigned"
        
        intake_payload = {
            "request_id": req_id,
            "tbc_job_number": tf_job_num.value.strip().upper(),
            "team_code": dd_team_code.value or "",
            "site_name": tf_site_name.value.strip(),
            "project_name": tf_proj_name.value.strip(),
            "contractor_company_name": tf_company.value.strip(),
            "street_address_1": tf_street_1.value.strip(),
            "street_address_2": tf_street_2.value.strip() if tf_street_2.value else "",
            "city": tf_city.value.strip(),
            "state": tf_state.value.strip(),
            "postal_code": tf_postal.value.strip() if tf_postal.value else "",
            "country": tf_country.value.strip() if tf_country.value else "US",
            "sales_rep_first_name": tf_sales_first.value.strip(),
            "sales_rep_last_name": tf_sales_last.value.strip() if tf_sales_last.value else "",
            "sales_rep_email": tf_sales_email.value.strip().lower() if tf_sales_email.value else "",
            "sales_rep_phone": tf_sales_phone.value.strip() if tf_sales_phone.value else "",
            "project_site_contact_first_name": tf_contact_first.value.strip() if tf_contact_first.value else "",
            "project_site_contact_last_name": tf_contact_last.value.strip() if tf_contact_last.value else "",
            "project_site_contact_email": tf_contact_email.value.strip().lower() if tf_contact_email.value else "",
            "project_site_contact_phone": tf_contact_phone.value.strip() if tf_contact_phone.value else "",
            "issue_description": tf_issue.value.strip() if tf_issue.value else "",
            "triage_status": triage_val,
            "request_type": dd_request_type.value or "VFD Startup",
            "submission_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO intake_requests (
                        request_id, tbc_job_number, team_code, site_name, project_name,
                        contractor_company_name, street_address_1, street_address_2, city, state,
                        postal_code, country, sales_rep_first_name, sales_rep_last_name, sales_rep_email,
                        sales_rep_phone, project_site_contact_first_name, project_site_contact_last_name,
                        project_site_contact_email, project_site_contact_phone, issue_description,
                        triage_status, request_type, submission_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, tuple(intake_payload.values()))

                if dd_technician.value and tf_scheduled_time.value:
                    job_id = f"JOB-{int(time.time())}"
                    cursor.execute("""
                        INSERT INTO dispatches (job_id, tbc_job_number, technician_email, sales_rep_email, scheduled_time, status, job_type)
                        VALUES (?, ?, ?, ?, ?, 'Scheduled', ?)
                    """, (job_id, intake_payload["tbc_job_number"], dd_technician.value, intake_payload["sales_rep_email"], tf_scheduled_time.value.strip(), intake_payload["request_type"]))

                conn.commit()
        except Exception as sql_err:
            logging.error(f"SQLite intake insert error: {sql_err}")

        if firestore_db is not None:
            try:
                firestore_db.collection("intake_ledger").document(req_id).set(intake_payload, merge=True)
            except Exception as fs_err:
                logging.error(f"Firestore intake sync error: {fs_err}")

        show_toast(page, f"🎉 Service Request #{req_id} logged successfully!", kind="success")
        clear_form()

        if on_success_callback:
            on_success_callback(intake_payload)

    form_container = ft.Container(
        content=ft.Column([
            ft.Row([tf_sales_first, tf_sales_last], spacing=10),
            ft.Row([tf_sales_email, tf_sales_phone, dd_team_code], spacing=10),
            ft.Row([tf_job_num, tf_company], spacing=10),
            ft.Row([tf_site_name, tf_proj_name], spacing=10),
            ft.Row([tf_street_1, tf_street_2], spacing=10),
            ft.Row([tf_city, tf_state, tf_postal, tf_country], spacing=8),
            ft.Row([tf_contact_first, tf_contact_last], spacing=10),
            ft.Row([tf_contact_email, tf_contact_phone], spacing=10),
            ft.Row([dd_request_type], spacing=10),
            tf_issue,
            ft.Row([dd_technician, tf_scheduled_time], spacing=10),
            ft.Row([
                ft.OutlinedButton("Upload Files", icon=ft.icons.ATTACH_FILE, style=FieldFlowLightTheme.get_secondary_button_style(), on_click=lambda _: docs_picker.pick_files(allow_multiple=True)),
                docs_status_txt
            ], spacing=10),
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.ElevatedButton("Create Service Request", icon=ft.icons.SEND, style=FieldFlowLightTheme.get_primary_button_style(), on_click=submit_service_request)
        ], spacing=10, scroll=ft.ScrollMode.AUTO, tight=True),
        padding=10
    )

    form_container.submit_form = submit_service_request
    form_container.clear_form = clear_form
    form_container.populate_data = populate_data

    return form_container