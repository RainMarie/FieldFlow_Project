"""
src/frontend/forms_component.py
Consolidated data entry and intake form module for FieldFlow using standardized key names,
auto-fill blur handlers, PO # support, Contractor PM labels, Dual-Action Project Creation pipeline,
full local + cloud asset registration, automatic form resets, and live search prefilling
for Salesmen, Contractor PMs, and Project Site Contacts.
"""

import os
import sys
import time
import uuid
import logging
from datetime import datetime
import flet as ft

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.frontend.theme import FieldFlowLightTheme
from src.backend import sync_engine
from src.backend.db_manager import (
    local_db, db as firestore_db, resolve_location,
    resolve_contractor, resolve_sales_user, resolve_pm_contact
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
    """Standardized label + control wrapper."""
    return ft.Container(
        content=ft.Column([
            ft.Text(label_text, size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            input_control
        ], spacing=4),
        expand=expand
    )


def on_contractor_blur_helper(tf_company: ft.TextField, tf_company_acct: ft.TextField, page: ft.Page):
    """Auto-fills contractor account or company name on blur."""
    comp_val = tf_company.value.strip() if tf_company.value else ""
    acct_val = tf_company_acct.value.strip() if tf_company_acct.value else ""

    if not comp_val and not acct_val:
        return

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            if acct_val:
                cursor.execute("SELECT company_name FROM contractors WHERE UPPER(tbco_account_number) = UPPER(?)", (acct_val,))
                row = cursor.fetchone()
                if row and row["company_name"]:
                    tf_company.value = row["company_name"]
            elif comp_val:
                cursor.execute("SELECT tbco_account_number FROM contractors WHERE LOWER(company_name) = LOWER(?)", (comp_val,))
                row = cursor.fetchone()
                if row and row["tbco_account_number"]:
                    tf_company_acct.value = row["tbco_account_number"]
    except Exception as err:
        logging.warning(f"Contractor blur helper note: {err}")

    if page:
        page.update()


# =========================================================================
# 1. PROJECT CREATION FORM COMPONENT
# =========================================================================
def build_project_creation_form(page: ft.Page, on_success_callback=None) -> ft.Control:
    """Project Creation Form saving flat project fields directly to SQLite and Firestore."""
    tf_job_num = ft.TextField(label="TBCo Job #*", hint_text="e.g. 287027TI", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_proj_name = ft.TextField(label="Project Name*", hint_text="e.g. Tower B Renovation", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_site_name = ft.TextField(label="Campus / Site Name*", hint_text="e.g. Tampa General Hospital Campus", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_po_num = ft.TextField(label="PO #", hint_text="e.g. PO-88210", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_street_1 = ft.TextField(label="Street Address 1*", hint_text="e.g. 500 Medical Way", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_street_2 = ft.TextField(label="Street Address 2 / Suite", hint_text="e.g. Suite 300", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_city = ft.TextField(label="City*", hint_text="e.g. Tampa", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_state = ft.TextField(label="State*", hint_text="e.g. FL", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_postal_code = ft.TextField(label="Postal Code*", hint_text="e.g. 33602", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    contractor_instructions_note = ft.Text(
        "Search existing contractor by Account # or Company Name to auto-fill contractor details below.",
        size=11, color=FieldFlowLightTheme.TEXT_MUTED
    )

    tf_company = ft.TextField(
        label="Contractor Company Name*", hint_text="e.g. Acme Mechanical",
        border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True,
        on_blur=lambda e: on_contractor_blur_helper(tf_company, tf_company_acct, page)
    )
    tf_company_acct = ft.TextField(
        label="Contractor Account #", hint_text="e.g. ACME-0091",
        border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True,
        on_blur=lambda e: on_contractor_blur_helper(tf_company, tf_company_acct, page)
    )

    tf_pm_first = ft.TextField(label="Contractor PM First Name", hint_text="e.g. Alex", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_last = ft.TextField(label="Contractor PM Last Name", hint_text="e.g. Smith", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_email = ft.TextField(label="Contractor PM Email", hint_text="e.g. asmith@acme.com", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_phone = ft.TextField(label="Contractor PM Phone", hint_text="e.g. 813-555-0199", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    sales_instructions_note = ft.Text(
        "Enter Sales Rep Email first to auto-fill details from database, or type new details below.",
        size=11, color=FieldFlowLightTheme.TEXT_MUTED
    )

    tf_sales_first = ft.TextField(label="Sales Rep First Name*", hint_text="e.g. Jane", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_last = ft.TextField(label="Sales Rep Last Name*", hint_text="e.g. Doe", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_phone = ft.TextField(label="Sales Rep Phone", hint_text="e.g. 813-555-0144", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    dd_team_code = ft.Dropdown(label="Team Code*", options=[ft.dropdown.Option(code) for code in VALID_TEAM_CODES], border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    def on_sales_email_blur(e):
        clean_email = tf_sales_email.value.strip().lower() if tf_sales_email.value else ""
        if not clean_email:
            return

        user_found = False
        if firestore_db is not None:
            try:
                doc = firestore_db.collection("users").document(clean_email).get()
                if doc.exists:
                    user_data = doc.to_dict()
                    tf_sales_first.value = user_data.get("first_name", "")
                    tf_sales_last.value = user_data.get("last_name", "")
                    tf_sales_phone.value = user_data.get("user_phone", "")
                    user_found = True
                    show_toast(page, "Loaded Sales Rep from Cloud Firestore.", kind="info")
            except Exception as err:
                logging.warning(f"Cloud sales user lookup error: {err}")

        if not user_found:
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT first_name, last_name, user_phone FROM users WHERE LOWER(user_email) = ?", (clean_email,))
                    row = cursor.fetchone()
                    if row:
                        tf_sales_first.value = row["first_name"] or ""
                        tf_sales_last.value = row["last_name"] or ""
                        tf_sales_phone.value = row["user_phone"] or ""
                        user_found = True
                        show_toast(page, "Loaded Sales Rep from local database.", kind="info")
            except Exception as err:
                logging.warning(f"Local sales user lookup error: {err}")

        if not user_found:
            show_toast(page, "New Sales Rep email. Enter details below to register user.", kind="info")

        if page:
            page.update()

    tf_sales_email = ft.TextField(
        label="Sales Rep Email*", hint_text="e.g. jdoe@tombarrow.com",
        border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True,
        on_blur=on_sales_email_blur
    )

    staged_photo_path = {"value": ""}
    staged_documents = []

    photo_status_txt = ft.Text("No Custom Picture Selected (Using Default Logo)", size=11, color=FieldFlowLightTheme.TEXT_MUTED)
    docs_status_txt = ft.Text("No Staged Documents", size=11, color=FieldFlowLightTheme.TEXT_MUTED)

    def on_photo_picked(e: ft.FilePickerResultEvent):
        if e.files:
            selected_file = e.files[0]
            file_path = getattr(selected_file, "path", None) or getattr(selected_file, "name", None)
            if file_path:
                staged_photo_path["value"] = file_path
                photo_status_txt.value = f"Photo Staged: {os.path.basename(file_path)}"
                photo_status_txt.color = FieldFlowLightTheme.PRIMARY_GREEN
                if page:
                    page.update()

    def on_docs_picked(e: ft.FilePickerResultEvent):
        if e.files:
            staged_documents.clear()
            for f in e.files:
                f_path = getattr(f, "path", None) or getattr(f, "name", None)
                if f_path:
                    staged_documents.append(f_path)
            docs_status_txt.value = f"{len(staged_documents)} Document(s) Staged"
            docs_status_txt.color = FieldFlowLightTheme.PRIMARY_GREEN
            if page:
                page.update()

    photo_picker = ft.FilePicker(on_result=on_photo_picked)
    docs_picker = ft.FilePicker(on_result=on_docs_picked)

    if photo_picker not in page.overlay:
        page.overlay.append(photo_picker)
    if docs_picker not in page.overlay:
        page.overlay.append(docs_picker)

    if page:
        page.update()

    btn_upload_photo = ft.OutlinedButton(
        "Select Photo",
        icon=ft.icons.IMAGE,
        style=FieldFlowLightTheme.get_secondary_button_style(),
        on_click=lambda _: photo_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["png", "jpg", "jpeg", "webp"]
        )
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

        tf_pm_first.value = ""
        tf_pm_last.value = ""
        tf_pm_email.value = ""
        tf_pm_phone.value = ""

        tf_sales_email.value = ""
        tf_sales_first.value = ""
        tf_sales_last.value = ""
        tf_sales_phone.value = ""
        dd_team_code.value = None

        staged_photo_path["value"] = ""
        staged_documents.clear()

        photo_status_txt.value = "No Custom Picture Selected (Using Default Logo)"
        photo_status_txt.color = FieldFlowLightTheme.TEXT_MUTED
        docs_status_txt.value = "No Staged Documents"
        docs_status_txt.color = FieldFlowLightTheme.TEXT_MUTED

        if page:
            page.update()

    def submit_project_creation(e):
        if not tf_job_num.value or not tf_proj_name.value or not tf_company.value or not tf_street_1.value or not tf_city.value or not tf_state.value:
            show_toast(page, "Job #, Project Name, Company, Street Address, City, and State are required!", kind="error")
            return

        job_num = tf_job_num.value.strip().upper()
        p_name = tf_proj_name.value.strip()
        s_name = tf_site_name.value.strip() if tf_site_name.value else p_name
        po_num = tf_po_num.value.strip() if tf_po_num.value else ""
        company = tf_company.value.strip()
        acct_no = tf_company_acct.value.strip().upper() if tf_company_acct.value else f"CON-{job_num[:4]}"

        street_1 = tf_street_1.value.strip()
        street_2 = tf_street_2.value.strip() if tf_street_2.value else ""
        city_val = tf_city.value.strip()
        state_val = tf_state.value.strip()
        zip_val = tf_postal_code.value.strip() if tf_postal_code.value else ""

        pm_first = tf_pm_first.value.strip() if tf_pm_first.value else ""
        pm_last = tf_pm_last.value.strip() if tf_pm_last.value else ""
        pm_email = tf_pm_email.value.strip().lower() if tf_pm_email.value else ""
        pm_phone = tf_pm_phone.value.strip() if tf_pm_phone.value else ""

        clean_site = resolve_location(s_name, street_1, street_2, city_val, state_val, zip_val, country="US")
        clean_acct = resolve_contractor(acct_no, company)

        clean_pm_id = None
        if pm_email:
            clean_pm_id = resolve_pm_contact(
                tbco_account_number=clean_acct,
                first_name=pm_first, last_name=pm_last,
                email=pm_email, phone=pm_phone, title="Project Manager"
            )

        sales_email_val = tf_sales_email.value.strip().lower() if tf_sales_email.value else ""
        if sales_email_val:
            resolve_sales_user(
                user_email=sales_email_val,
                first_name=tf_sales_first.value.strip() if tf_sales_first.value else "",
                last_name=tf_sales_last.value.strip() if tf_sales_last.value else "",
                user_phone=tf_sales_phone.value.strip() if tf_sales_phone.value else ""
            )

        drive_info = ensure_project_drive_folder(
            job_number=job_num,
            project_name=p_name,
            requestor_name=f"{tf_sales_first.value} {tf_sales_last.value}".strip(),
            requestor_email=sales_email_val,
            attached_file_paths=staged_documents
        )
        drive_id = drive_info.get("drive_id", f"FLD-GDRV-{job_num}")

        proj_payload = {
            "tbc_job_number": job_num, "site_name": clean_site, "tbco_account_number": clean_acct,
            "pm_contact_id": clean_pm_id, "project_name": p_name, "po_number": po_num,
            "contractor_company_name": company, "street_address_1": street_1, "street_address_2": street_2,
            "city": city_val, "state": state_val, "postal_code": zip_val, "country": "US",
            "pm_first_name": pm_first, "pm_last_name": pm_last, "pm_email": pm_email, "pm_phone": pm_phone,
            "sales_rep_email": sales_email_val, "sales_rep_phone": tf_sales_phone.value.strip() if tf_sales_phone.value else "",
            "team_code": dd_team_code.value if dd_team_code.value else "", "drive_id": drive_id, "stage": "In Progress",
            "photo_url": staged_photo_path["value"]
        }

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO projects (
                        tbc_job_number, site_name, tbco_account_number, pm_contact_id, project_name,
                        contractor_company_name, street_address_1, street_address_2, city, state,
                        postal_code, country, sales_rep_email, sales_rep_phone, team_code,
                        pm_first_name, pm_last_name, pm_email, pm_phone, po_number, drive_id, stage, photo_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_num, clean_site, clean_acct, clean_pm_id, p_name, company, street_1, street_2,
                    city_val, state_val, zip_val, "US", sales_email_val, tf_sales_phone.value.strip() if tf_sales_phone.value else "",
                    dd_team_code.value if dd_team_code.value else "", pm_first, pm_last, pm_email, pm_phone,
                    po_num, drive_id, "In Progress", staged_photo_path["value"]
                ))
                conn.commit()
        except Exception as sql_err:
            logging.error(f"SQLite project insert error: {sql_err}")

        if firestore_db is not None:
            try:
                firestore_db.collection("projects").document(job_num).set(proj_payload, merge=True)
            except Exception as fs_err:
                logging.error(f"Firestore project insert error: {fs_err}")

        show_toast(page, f"Project #{job_num} created successfully!", kind="success")
        clear_form()

        if on_success_callback:
            on_success_callback(proj_payload)

    form_container = ft.Container(
        content=ft.Column([
            ft.Row([tf_job_num, tf_proj_name], spacing=10),
            ft.Row([tf_site_name, tf_po_num], spacing=10),
            ft.Row([tf_street_1, tf_street_2], spacing=10),
            ft.Row([tf_city, tf_state, tf_postal_code], spacing=8),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            contractor_instructions_note,
            ft.Row([tf_company, tf_company_acct], spacing=10),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Row([tf_pm_first, tf_pm_last], spacing=10),
            ft.Row([tf_pm_email, tf_pm_phone], spacing=10),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            sales_instructions_note,
            ft.Row([tf_sales_email], spacing=10),
            ft.Row([tf_sales_first, tf_sales_last], spacing=10),
            ft.Row([tf_sales_phone, dd_team_code], spacing=10),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Row([btn_upload_photo, photo_status_txt], spacing=10),
            ft.Row([btn_upload_docs, docs_status_txt], spacing=10),
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.ElevatedButton("Create Project", style=FieldFlowLightTheme.get_primary_button_style(), on_click=submit_project_creation)
        ], spacing=10, scroll=ft.ScrollMode.AUTO, tight=True),
        padding=10
    )

    form_container.clear_form = clear_form
    form_container.submit_form = submit_project_creation

    return form_container

# =========================================================================
# 2. ASSET REGISTRATION TOOL COMPONENT
# =========================================================================
def build_asset_registration_tool(job_data: dict, on_proceed_callback=None, on_back_callback=None, show_toast_fn=None, page: ft.Page = None) -> ft.Column:
    """Asset registration wizard for searching and linking equipment tags to local SQLite and Cloud Firestore."""
    tbc_job_num = str(job_data.get("tbc_job_number", "889900XX"))

    search_input_field = ft.TextField(label="Search Equipment Serial Number...", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    serial_field_confirm = ft.TextField(label="Asset Serial Number*", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    model_field_confirm = ft.TextField(label="Asset Model Number", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    name_field_confirm = ft.TextField(label="Equipment Name / Tag*", border_color=FieldFlowLightTheme.ACCENT_BLUE)

    tf_manufacturer = ft.TextField(label="Manufacturer ID / Name", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    dd_serves = ft.Dropdown(
        label="Equipment Type",
        options=[
            ft.dropdown.Option("VFD Drive"),
            ft.dropdown.Option("Air Handler"),
            ft.dropdown.Option("Fan"),
            ft.dropdown.Option("Chiller"),
            ft.dropdown.Option("Pump")
        ],
        border_color=FieldFlowLightTheme.ACCENT_BLUE
    )

    def register_asset_event(e):
        name_val = name_field_confirm.value.strip() if name_field_confirm.value else ""
        serial_val = serial_field_confirm.value.strip().upper() if serial_field_confirm.value else ""
        model_val = model_field_confirm.value.strip() if model_field_confirm.value else ""
        mfr_val = tf_manufacturer.value.strip() if tf_manufacturer.value else ""

        if not name_val or not serial_val:
            if show_toast_fn and page:
                show_toast_fn(page, "Equipment Tag Name and Serial Number are required!", kind="error")
            return

        asset_id = f"AST-{uuid.uuid4().hex[:8].upper()}"
        site_name_val = job_data.get("site_name", "Default Campus")

        asset_payload = {
            "asset_id": asset_id,
            "tbc_job_number": tbc_job_num,
            "site_name": site_name_val,
            "manufacturer_id": mfr_val,
            "model_number": model_val,
            "serial_number": serial_val,
            "equipment_tag": name_val,
            "operational_status": "Operational"
        }

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO assets (asset_id, tbc_job_number, site_name, manufacturer_id, model_number, serial_number, equipment_tag, operational_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Operational')
                """, (asset_id, tbc_job_num, site_name_val, mfr_val, model_val, serial_val, name_val))
                conn.commit()
        except Exception as sql_err:
            logging.error(f"Asset local save error: {sql_err}")

        if firestore_db is not None:
            try:
                firestore_db.collection("assets").document(asset_id).set(asset_payload, merge=True)
            except Exception as fs_err:
                logging.error(f"Asset cloud save error: {fs_err}")

        if show_toast_fn and page:
            show_toast_fn(page, f"Asset '{name_val}' registered successfully!", kind="success")

        if on_proceed_callback:
            on_proceed_callback(asset_payload)

    register_btn = ft.ElevatedButton("Register Asset", style=FieldFlowLightTheme.get_primary_button_style(), on_click=register_asset_event)

    return ft.Column([
        ft.Row([ft.TextButton("<- Back", on_click=on_back_callback)]) if on_back_callback else ft.Container(),
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
    """Master Parts Catalog entry form."""
    tf_sku = ft.TextField(label="SKU / Part Number*", hint_text="e.g. SKU-VALVE-01", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_manufacturer = ft.TextField(label="Manufacturer", hint_text="e.g. Honeywell", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_description = ft.TextField(label="Description*", hint_text="e.g. 2-Way Control Valve 24V", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_unit_cost = ft.TextField(label="Unit Cost ($)", hint_text="e.g. 150.00", border_color=FieldFlowLightTheme.ACCENT_BLUE, value="0.00")

    def submit_part(e):
        sku = tf_sku.value.strip().upper() if tf_sku.value else ""
        desc = tf_description.value.strip() if tf_description.value else ""
        if not sku or not desc:
            show_toast(page, "SKU and Description are required!", kind="error")
            return

        payload = {"sku": sku, "manufacturer": tf_manufacturer.value.strip(), "description": desc, "unit_cost": float(tf_unit_cost.value or 0)}

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO parts_master (sku, manufacturer, description, unit_cost) VALUES (?, ?, ?, ?)",
                               (sku, payload["manufacturer"], desc, payload["unit_cost"]))
                conn.commit()
        except Exception as err:
            logging.error(f"Part save error: {err}")

        show_toast(page, f"Part '{sku}' saved to Master Catalog!", kind="success")
        if on_success_callback: on_success_callback(payload)

    return ft.Container(
        content=ft.Column([
            ft.Row([tf_sku, tf_manufacturer], spacing=10),
            ft.Row([tf_description, tf_unit_cost], spacing=10),
            ft.ElevatedButton("Save Part to Catalog", style=FieldFlowLightTheme.get_primary_button_style(), on_click=submit_part)
        ], spacing=10, tight=True), padding=10
    )


def build_manufacturer_form(page: ft.Page, on_success_callback=None) -> ft.Control:
    """Master Manufacturer Catalog entry form."""
    tf_mfr_id = ft.TextField(label="Manufacturer ID / Code*", hint_text="e.g. YASKAWA", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    tf_mfr_name = ft.TextField(label="Manufacturer Full Name*", hint_text="e.g. Yaskawa America Inc", border_color=FieldFlowLightTheme.ACCENT_BLUE)

    def submit_mfr(e):
        m_id = tf_mfr_id.value.strip().upper() if tf_mfr_id.value else ""
        m_name = tf_mfr_name.value.strip() if tf_mfr_name.value else ""
        if not m_id or not m_name:
            show_toast(page, "Manufacturer Code and Name required!", kind="error")
            return

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO manufacturers (manufacturer_id, name) VALUES (?, ?)", (m_id, m_name))
                conn.commit()
        except Exception as err:
            logging.error(f"Manufacturer save error: {err}")

        show_toast(page, f"Manufacturer '{m_name}' saved!", kind="success")
        if on_success_callback: on_success_callback({"manufacturer_id": m_id, "name": m_name})

    return ft.Container(
        content=ft.Column([
            ft.Row([tf_mfr_id, tf_mfr_name], spacing=10),
            ft.ElevatedButton("Save Manufacturer", style=FieldFlowLightTheme.get_primary_button_style(), on_click=submit_mfr)
        ], spacing=10, tight=True), padding=10
    )


def build_truck_form(page: ft.Page, get_tech_options_fn=None, on_success_callback=None) -> ft.Control:
    """Fleet Truck Inventory entry form."""
    tf_truck_id = ft.TextField(label="Fleet Truck Tag / Number*", hint_text="e.g. TRUCK-104", border_color=FieldFlowLightTheme.ACCENT_BLUE)
    dd_tech = ft.Dropdown(label="Assigned Technician", options=get_tech_options_fn() if get_tech_options_fn else [], border_color=FieldFlowLightTheme.ACCENT_BLUE)

    def submit_truck(e):
        t_id = tf_truck_id.value.strip().upper() if tf_truck_id.value else ""
        if not t_id:
            show_toast(page, "Truck Number is required!", kind="error")
            return

        tech_email = dd_tech.value or ""
        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO fleet_trucks (truck_id, assigned_tech_email) VALUES (?, ?)", (t_id, tech_email))
                conn.commit()
        except Exception as err:
            logging.error(f"Fleet truck save error: {err}")

        show_toast(page, f"Fleet Truck '{t_id}' saved!", kind="success")
        if on_success_callback: on_success_callback({"truck_id": t_id, "assigned_tech_email": tech_email})

    return ft.Container(
        content=ft.Column([
            ft.Row([tf_truck_id, dd_tech], spacing=10),
            ft.ElevatedButton("Save Fleet Truck", style=FieldFlowLightTheme.get_primary_button_style(), on_click=submit_truck)
        ], spacing=10, tight=True), padding=10
    )


def build_master_forms(page: ft.Page, get_tech_options_fn=None, on_success_callback=None) -> ft.Control:
    """Tabbed Master Data Catalog Container required by admin_dashboard.py."""
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
def build_service_intake_form(page: ft.Page, trigger_date_picker_fn=None, on_success_callback=None, get_tech_options_fn=None) -> ft.Control:
    """Service Ticket Intake Form featuring dual-stage prefilling for Sales Reps and clean independent Site Contacts."""
    tf_job_num = ft.TextField(label="TBCo Job #*", hint_text="e.g. 287027TI", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_proj_name = ft.TextField(label="Project Name*", hint_text="e.g. Tower B Renovation", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_site_name = ft.TextField(label="Campus / Site Name*", hint_text="e.g. Tampa General Hospital Campus", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_company = ft.TextField(label="Contractor Company Name*", hint_text="e.g. Acme Mechanical", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # Sales Representative Controls
    tf_sales_first = ft.TextField(label="Sales Rep First Name*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_last = ft.TextField(label="Sales Rep Last Name*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_email = ft.TextField(label="Sales Rep Email*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_phone = ft.TextField(label="Sales Rep Phone", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    dd_team_code = ft.Dropdown(label="Team Code*", options=[ft.dropdown.Option(code) for code in VALID_TEAM_CODES], border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # Contractor Project Manager Controls
    tf_pm_first = ft.TextField(label="Contractor PM First Name", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_last = ft.TextField(label="Contractor PM Last Name", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_email = ft.TextField(label="Contractor PM Email", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_phone = ft.TextField(label="Contractor PM Phone", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # Project Site Contact Controls
    tf_contact_first = ft.TextField(label="Site Contact First Name", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_last = ft.TextField(label="Site Contact Last Name", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_email = ft.TextField(label="Site Contact Email", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_phone = ft.TextField(label="Site Contact Phone", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_issue = ft.TextField(label="Issue Description*", multiline=True, min_lines=2, max_lines=4, border_color=FieldFlowLightTheme.ACCENT_BLUE)

    def clear_form(e=None):
        """Resets all intake form input controls to blank values."""
        tf_job_num.value = ""
        tf_proj_name.value = ""
        tf_site_name.value = ""
        tf_company.value = ""

        tf_sales_first.value = ""
        tf_sales_last.value = ""
        tf_sales_email.value = ""
        tf_sales_phone.value = ""
        dd_team_code.value = None

        tf_pm_first.value = ""
        tf_pm_last.value = ""
        tf_pm_email.value = ""
        tf_pm_phone.value = ""

        tf_contact_first.value = ""
        tf_contact_last.value = ""
        tf_contact_email.value = ""
        tf_contact_phone.value = ""

        tf_issue.value = ""
        if page:
            page.update()

    def populate_data(proj_data):
        """Populates intake form controls directly from dictionary payload with dual-stage Sales Rep prefilling."""
        if not isinstance(proj_data, dict):
            return

        job_num = proj_data.get("tbc_job_number", "")
        if job_num:
            tf_job_num.value = job_num

        tf_proj_name.value = proj_data.get("project_name", "")
        tf_site_name.value = proj_data.get("site_name", "")
        tf_company.value = proj_data.get("contractor_company_name", "")

        # 1. Sales Representative Prefill
        sales_email_val = proj_data.get("sales_rep_email") or proj_data.get("sales_email") or ""
        tf_sales_email.value = sales_email_val
        tf_sales_phone.value = proj_data.get("sales_rep_phone") or proj_data.get("sales_phone") or ""
        dd_team_code.value = proj_data.get("team_code") or None

        user_found = False
        if sales_email_val:
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT first_name, last_name, user_phone FROM users WHERE LOWER(user_email) = ?", (sales_email_val.lower(),))
                    u_row = cursor.fetchone()
                    if u_row:
                        tf_sales_first.value = u_row["first_name"] or ""
                        tf_sales_last.value = u_row["last_name"] or ""
                        if not tf_sales_phone.value:
                            tf_sales_phone.value = u_row["user_phone"] or ""
                        user_found = True
            except Exception as err:
                logging.warning(f"Sales user prefill lookup note: {err}")

        # Fallback to direct project dictionary keys if not found in users table
        if not user_found:
            tf_sales_first.value = proj_data.get("sales_rep_first_name") or proj_data.get("sales_first") or ""
            tf_sales_last.value = proj_data.get("sales_rep_last_name") or proj_data.get("sales_last") or ""

        # 2. Contractor Project Manager Prefill
        tf_pm_first.value = proj_data.get("pm_first_name", "")
        tf_pm_last.value = proj_data.get("pm_last_name", "")
        tf_pm_email.value = proj_data.get("pm_email", "")
        tf_pm_phone.value = proj_data.get("pm_phone", "")

        # 3. Independent Site Contact Prefill (no fallback to PM)
        tf_contact_first.value = proj_data.get("project_site_contact_first_name") or proj_data.get("contact_first_name") or ""
        tf_contact_last.value = proj_data.get("project_site_contact_last_name") or proj_data.get("contact_last_name") or ""
        tf_contact_email.value = proj_data.get("project_site_contact_email") or proj_data.get("contact_email") or ""
        tf_contact_phone.value = proj_data.get("project_site_contact_phone") or proj_data.get("contact_phone") or ""

        if page:
            page.update()

    def on_job_num_blur(e):
        """Automatically queries SQLite 'projects' table by Job # to prefill all roles."""
        job_num = tf_job_num.value.strip().upper() if tf_job_num.value else ""
        if not job_num:
            return

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM projects WHERE UPPER(tbc_job_number) = ?", (job_num,))
                proj_row = cursor.fetchone()
                if proj_row:
                    populate_data(dict(proj_row))
                    show_toast(page, f"Loaded project details for Job #{job_num} from database!", kind="info")
        except Exception as sql_err:
            logging.warning(f"Error prefilling intake form from job number: {sql_err}")

        if page:
            page.update()

    def on_sales_email_blur(e):
        """Live search lookup for Sales Rep details on email blur."""
        s_email = tf_sales_email.value.strip().lower() if tf_sales_email.value else ""
        if not s_email:
            return

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT first_name, last_name, user_phone FROM users WHERE LOWER(user_email) = ?", (s_email,))
                u_row = cursor.fetchone()
                if u_row:
                    tf_sales_first.value = u_row["first_name"] or ""
                    tf_sales_last.value = u_row["last_name"] or ""
                    tf_sales_phone.value = u_row["user_phone"] or ""
                    show_toast(page, f"Found Sales Rep {u_row['first_name']} {u_row['last_name']} in database!", kind="info")
        except Exception as err:
            logging.warning(f"Sales email blur lookup note: {err}")

        if page:
            page.update()

    def on_pm_email_blur(e):
        """Live search lookup for Contractor PM details on email blur."""
        p_email = tf_pm_email.value.strip().lower() if tf_pm_email.value else ""
        if not p_email:
            return

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT pm_first_name, pm_last_name, pm_phone FROM projects WHERE LOWER(pm_email) = ? LIMIT 1", (p_email,))
                p_row = cursor.fetchone()
                if p_row:
                    tf_pm_first.value = p_row["pm_first_name"] or ""
                    tf_pm_last.value = p_row["pm_last_name"] or ""
                    tf_pm_phone.value = p_row["pm_phone"] or ""
                    show_toast(page, "Found PM contact details in database!", kind="info")
        except Exception as err:
            logging.warning(f"PM email blur lookup note: {err}")

        if page:
            page.update()

    tf_job_num.on_blur = on_job_num_blur
    tf_sales_email.on_blur = on_sales_email_blur
    tf_pm_email.on_blur = on_pm_email_blur

    def submit_service_request(e):
        if not tf_job_num.value or not tf_proj_name.value or not tf_company.value:
            show_toast(page, "Job #, Project Name, and Contractor are required!", kind="error")
            return

        req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        job_num = tf_job_num.value.strip().upper()
        sales_email = tf_sales_email.value.strip().lower() if tf_sales_email.value else ""

        intake_payload = {
            "request_id": req_id,
            "tbc_job_number": job_num,
            "project_name": tf_proj_name.value.strip(),
            "site_name": tf_site_name.value.strip(),
            "contractor_company_name": tf_company.value.strip(),
            "sales_rep_email": sales_email,
            "sales_rep_phone": tf_sales_phone.value.strip(),
            "team_code": dd_team_code.value or "",
            "pm_first_name": tf_pm_first.value.strip(),
            "pm_last_name": tf_pm_last.value.strip(),
            "pm_email": tf_pm_email.value.strip().lower(),
            "pm_phone": tf_pm_phone.value.strip(),
            "project_site_contact_first_name": tf_contact_first.value.strip(),
            "project_site_contact_last_name": tf_contact_last.value.strip(),
            "project_site_contact_email": tf_contact_email.value.strip().lower(),
            "project_site_contact_phone": tf_contact_phone.value.strip(),
            "issue_description": tf_issue.value.strip(),
            "triage_status": "Unassigned",
            "submission_timestamp": datetime.now().isoformat()
        }

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO intake_ledger (
                        request_id, tbc_job_number, project_name, site_name, contractor_company_name,
                        sales_rep_email, sales_rep_phone, team_code, pm_first_name, pm_last_name,
                        pm_email, pm_phone, project_site_contact_first_name, project_site_contact_last_name,
                        project_site_contact_email, project_site_contact_phone, issue_description,
                        triage_status, submission_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Unassigned', ?)
                """, (
                    req_id, job_num, intake_payload["project_name"], intake_payload["site_name"], intake_payload["contractor_company_name"],
                    intake_payload["sales_rep_email"], intake_payload["sales_rep_phone"], intake_payload["team_code"],
                    intake_payload["pm_first_name"], intake_payload["pm_last_name"], intake_payload["pm_email"], intake_payload["pm_phone"],
                    intake_payload["project_site_contact_first_name"], intake_payload["project_site_contact_last_name"],
                    intake_payload["project_site_contact_email"], intake_payload["project_site_contact_phone"],
                    intake_payload["issue_description"], intake_payload["submission_timestamp"]
                ))
                conn.commit()
        except Exception as sql_err:
            logging.error(f"SQLite service intake save error: {sql_err}")

        if firestore_db is not None:
            try:
                firestore_db.collection("intake_ledger").document(req_id).set(intake_payload, merge=True)
            except Exception as fs_err:
                logging.error(f"Firestore service intake save error: {fs_err}")

        show_toast(page, f"Service Request #{req_id} Created!", kind="success")
        clear_form()

        if on_success_callback:
            on_success_callback(intake_payload)

    form_layout = ft.Container(
        content=ft.Column([
            ft.Row([tf_job_num, tf_proj_name], spacing=10),
            ft.Row([tf_site_name, tf_company], spacing=10),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Text("Sales Representative Details", size=12, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            ft.Row([tf_sales_first, tf_sales_last], spacing=10),
            ft.Row([tf_sales_email, tf_sales_phone, dd_team_code], spacing=10),

            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Text("Contractor Project Manager", size=12, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            ft.Row([tf_pm_first, tf_pm_last], spacing=10),
            ft.Row([tf_pm_email, tf_pm_phone], spacing=10),

            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Text("Project Site Contact", size=12, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            ft.Row([tf_contact_first, tf_contact_last], spacing=10),
            ft.Row([tf_contact_email, tf_contact_phone], spacing=10),

            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            tf_issue,
            ft.ElevatedButton("Submit Service Request", style=FieldFlowLightTheme.get_primary_button_style(), on_click=submit_service_request)
        ], spacing=10, scroll=ft.ScrollMode.AUTO, tight=True),
        padding=10
    )

    form_layout.clear_form = clear_form
    form_layout.populate_data = populate_data
    form_layout.submit_form = submit_service_request
    return form_layout