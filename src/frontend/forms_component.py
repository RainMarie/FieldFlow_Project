"""
src/frontend/forms_component.py
Consolidated data entry and intake form module for FieldFlow using standardized key names,
reordered search-first fields, auto-fill blur handlers, PO # support, Contractor PM labels,
Dual-Action Project Creation pipeline, and full local + cloud asset registration.
"""

import os
import sys
import time
import uuid
import logging
import flet as ft

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.frontend.theme import FieldFlowLightTheme
from src.backend import sync_engine
from src.backend.db_manager import (
    local_db, 
    db as firestore_db, 
    resolve_location, 
    resolve_contractor,
    resolve_sales_user,
    resolve_pm_contact
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
    """Helper utility to wrap Flet controls with standardized accent titles."""
    return ft.Container(
        content=ft.Column([
            ft.Text(label_text, size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            input_control
        ], spacing=2, tight=True),
        expand=expand
    )


def on_contractor_blur_helper(tf_company: ft.TextField, tf_company_acct: ft.TextField, page: ft.Page):
    """
    Search & Auto-Fill Handler for Contractor fields.
    Queries local SQLite and Cloud Firestore by Account # or Company Name.
    """
    clean_company = tf_company.value.strip() if tf_company.value else ""
    clean_acct = tf_company_acct.value.strip().upper() if tf_company_acct.value else ""

    if not clean_company and not clean_acct:
        return

    found_acct = None
    found_name = None

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            if clean_acct:
                cursor.execute(
                    "SELECT tbco_account_number, company_name FROM contractors WHERE tbco_account_number = ?", 
                    (clean_acct,)
                )
            else:
                cursor.execute(
                    "SELECT tbco_account_number, company_name FROM contractors WHERE LOWER(company_name) LIKE ? LIMIT 1", 
                    (f"%{clean_company.lower()}%",)
                )
            row = cursor.fetchone()
            if row:
                found_acct = row["tbco_account_number"]
                found_name = row["company_name"]
    except Exception as err:
        logging.warning(f"Local contractor lookup error: {err}")

    if not found_acct and firestore_db is not None:
        try:
            if clean_acct:
                doc = firestore_db.collection("contractors").document(clean_acct).get()
                if doc.exists:
                    data = doc.to_dict()
                    found_acct = data.get("tbco_account_number", clean_acct)
                    found_name = data.get("company_name", "")
            else:
                query = firestore_db.collection("contractors").stream()
                for doc in query:
                    data = doc.to_dict()
                    comp_name = data.get("company_name", "")
                    if clean_company.lower() in comp_name.lower():
                        found_acct = doc.id or data.get("tbco_account_number", "")
                        found_name = comp_name
                        break
        except Exception as err:
            logging.warning(f"Cloud contractor lookup error: {err}")

    if found_acct or found_name:
        if found_acct:
            tf_company_acct.value = found_acct
        if found_name:
            tf_company.value = found_name
        show_toast(page, f"Loaded Contractor: {found_name or found_acct}", kind="info")
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
        size=11,
        color=FieldFlowLightTheme.TEXT_MUTED
    )

    tf_company = ft.TextField(
        label="Contractor Company Name*", 
        hint_text="e.g. Acme Mechanical", 
        border_color=FieldFlowLightTheme.ACCENT_BLUE, 
        expand=True,
        on_blur=lambda e: on_contractor_blur_helper(tf_company, tf_company_acct, page)
    )
    tf_company_acct = ft.TextField(
        label="Contractor Account #", 
        hint_text="e.g. ACME-0091", 
        border_color=FieldFlowLightTheme.ACCENT_BLUE, 
        expand=True,
        on_blur=lambda e: on_contractor_blur_helper(tf_company, tf_company_acct, page)
    )

    tf_pm_first = ft.TextField(label="Contractor PM First Name", hint_text="e.g. Alex", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_last = ft.TextField(label="Contractor PM Last Name", hint_text="e.g. Smith", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_email = ft.TextField(label="Contractor PM Email", hint_text="e.g. asmith@acme.com", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_phone = ft.TextField(label="Contractor PM Phone", hint_text="e.g. 813-555-0199", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    sales_instructions_note = ft.Text(
        "Enter Sales Rep Email first to auto-fill details from database, or type new details below.",
        size=11,
        color=FieldFlowLightTheme.TEXT_MUTED
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
        label="Sales Rep Email*",
        hint_text="e.g. jdoe@tombarrow.com",
        border_color=FieldFlowLightTheme.ACCENT_BLUE,
        expand=True,
        on_blur=on_sales_email_blur
    )

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
        style=FieldFlowLightTheme.get_secondary_button_style(),
        on_click=lambda _: photo_picker.pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
    )
    btn_upload_docs = ft.OutlinedButton(
        "Upload Documents",
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

        if page: page.update()

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
                first_name=pm_first,
                last_name=pm_last,
                email=pm_email,
                phone=pm_phone,
                title="Project Manager"
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
            "tbc_job_number": job_num,
            "site_name": clean_site,
            "tbco_account_number": clean_acct,
            "pm_contact_id": clean_pm_id,
            "project_name": p_name,
            "po_number": po_num,
            "contractor_company_name": company,
            "street_address_1": street_1,
            "street_address_2": street_2,
            "city": city_val,
            "state": state_val,
            "postal_code": zip_val,
            "country": "US",
            "pm_first_name": pm_first,
            "pm_last_name": pm_last,
            "pm_email": pm_email,
            "pm_phone": pm_phone,
            "sales_rep_email": sales_email_val,
            "sales_rep_phone": tf_sales_phone.value.strip() if tf_sales_phone.value else "",
            "team_code": dd_team_code.value if dd_team_code.value else "",
            "drive_id": drive_id,
            "stage": "In Progress",
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
                    job_num, clean_site, clean_acct, clean_pm_id, p_name,
                    company, street_1, street_2, city_val, state_val,
                    zip_val, "US", sales_email_val, tf_sales_phone.value.strip() if tf_sales_phone.value else "",
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

def build_asset_registration_tool(
    job_data: dict,
    on_proceed_callback=None,
    on_back_callback=None,
    show_toast_fn=None,
    page: ft.Page = None
) -> ft.Column:
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

        # 1. Save to Local SQLite DB
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

        # 2. Save to Cloud Firestore
        if firestore_db is not None:
            try:
                firestore_db.collection("assets").document(asset_id).set(asset_payload, merge=True)
            except Exception as fs_err:
                logging.error(f"Asset cloud save error: {fs_err}")

        if show_toast_fn and page:
            show_toast_fn(page, f"Asset '{name_val}' registered successfully!", kind="success")

        if on_proceed_callback:
            on_proceed_callback(asset_payload)

    register_btn = ft.ElevatedButton(
        "Register Asset",
        style=FieldFlowLightTheme.get_primary_button_style(),
        on_click=register_asset_event
    )

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

        show_toast(page, f"Part '{sku_val}' saved!", kind="success")
        if on_success_callback: on_success_callback(part_payload)

    return ft.Container(content=ft.Column([tf_sku, tf_manufacturer, tf_description, tf_unit_cost, ft.ElevatedButton("Save Part", on_click=submit_part)], spacing=10))


def build_manufacturer_form(page: ft.Page, on_success_callback=None) -> ft.Control:
    """Master Manufacturer entry form."""
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

        show_toast(page, "Manufacturer saved!", kind="success")
        if on_success_callback: on_success_callback(payload)

    return ft.Container(content=ft.Column([tf_mfr_id, tf_company, ft.ElevatedButton("Save Vendor", on_click=submit_mfr)], spacing=10))


def build_truck_form(page: ft.Page, get_tech_options_fn=None, on_success_callback=None) -> ft.Control:
    """Fleet Truck entry form."""
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

        show_toast(page, "Truck saved!", kind="success")
        if on_success_callback: on_success_callback(payload)

    return ft.Container(content=ft.Column([tf_truck_id, tf_plate, ft.ElevatedButton("Save Truck", on_click=submit_truck)], spacing=10))


def build_master_forms(page: ft.Page, get_tech_options_fn=None, on_success_callback=None) -> ft.Control:
    """Tabbed Master Data Catalog Container."""
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
    """Service Ticket Intake Form querying flat project table directly without relational joins."""
    
    # 1. Sales Rep Search Controls
    sales_instructions_note = ft.Text(
        "Enter Sales Rep Email first to auto-fill details from database, or type new details below.",
        size=11,
        color=FieldFlowLightTheme.TEXT_MUTED
    )

    tf_sales_first = ft.TextField(label="Sales Rep First Name*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_last = ft.TextField(label="Sales Rep Last Name*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_sales_phone = ft.TextField(label="Sales Rep Phone", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    dd_team_code = ft.Dropdown(label="Team Code*", options=[ft.dropdown.Option(c) for c in VALID_TEAM_CODES], border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

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
        label="Sales Rep Email*", 
        border_color=FieldFlowLightTheme.ACCENT_BLUE, 
        expand=True,
        on_blur=on_sales_email_blur
    )

    # 2. Contractor Search Controls
    contractor_instructions_note = ft.Text(
        "Search existing contractor by Account # or Company Name to auto-fill contractor details below.",
        size=11,
        color=FieldFlowLightTheme.TEXT_MUTED
    )

    tf_company = ft.TextField(
        label="Contractor Company Name*", 
        hint_text="e.g. Acme Mechanical", 
        border_color=FieldFlowLightTheme.ACCENT_BLUE, 
        expand=True,
        on_blur=lambda e: on_contractor_blur_helper(tf_company, tf_company_acct, page)
    )
    tf_company_acct = ft.TextField(
        label="Contractor Account #", 
        hint_text="e.g. ACME-0091", 
        border_color=FieldFlowLightTheme.ACCENT_BLUE, 
        expand=True,
        on_blur=lambda e: on_contractor_blur_helper(tf_company, tf_company_acct, page)
    )

    # 3. Contractor Project Manager Controls
    tf_pm_first = ft.TextField(label="Contractor PM First Name", hint_text="e.g. Alex", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_last = ft.TextField(label="Contractor PM Last Name", hint_text="e.g. Smith", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_email = ft.TextField(label="Contractor PM Email", hint_text="e.g. asmith@acme.com", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_pm_phone = ft.TextField(label="Contractor PM Phone", hint_text="e.g. 813-555-0199", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # 4. Job & Location Controls with PO # (Direct Query without SQL JOINs)
    def on_job_num_blur(e):
        clean_job = tf_job_num.value.strip().upper() if tf_job_num.value else ""
        if not clean_job:
            return

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        tbc_job_number, project_name, site_name, po_number, tbco_account_number,
                        contractor_company_name, street_address_1, street_address_2, city, state,
                        postal_code, country, pm_first_name, pm_last_name, pm_email, pm_phone,
                        sales_rep_email, sales_rep_phone, team_code
                    FROM projects
                    WHERE UPPER(tbc_job_number) = ?
                    LIMIT 1
                """, (clean_job,))
                row = cursor.fetchone()
                if row:
                    populate_data(dict(row))
                    show_toast(page, f"Loaded shared project details for Job #{clean_job}", kind="info")
        except Exception as err:
            logging.warning(f"Job num blur lookup error: {err}")

    tf_job_num = ft.TextField(
        label="TBCo Job #*", 
        border_color=FieldFlowLightTheme.ACCENT_BLUE, 
        expand=True,
        on_blur=on_job_num_blur
    )
    tf_proj_name = ft.TextField(label="Project Name*", hint_text="e.g. Tower B Renovation", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_site_name = ft.TextField(label="Campus / Site Name*", hint_text="e.g. Tampa General Hospital Campus", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_po_num = ft.TextField(label="PO #", hint_text="e.g. PO-88210", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    tf_street_1 = ft.TextField(label="Street Address 1*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_street_2 = ft.TextField(label="Street Address 2 / Unit", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_city = ft.TextField(label="City*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_state = ft.TextField(label="State*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_postal = ft.TextField(label="Postal Code*", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # 5. Project Site Contact Controls
    tf_contact_first = ft.TextField(label="Project Site Contact First Name", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_last = ft.TextField(label="Project Site Contact Last Name", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_email = ft.TextField(label="Project Site Contact Email", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)
    tf_contact_phone = ft.TextField(label="Project Site Contact Phone", border_color=FieldFlowLightTheme.ACCENT_BLUE, expand=True)

    # 6. Service Request & Dispatch Controls
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

    def populate_data(proj_data):
        """Safely prefill form fields from flat dictionary payload or job number string with DB fallback."""
        if get_tech_options_fn:
            dd_technician.options = get_tech_options_fn()

        if isinstance(proj_data, str):
            payload = {}
            job_num = proj_data.strip().upper()
        else:
            payload = dict(proj_data or {})
            job_num = str(payload.get("tbc_job_number") or payload.get("job_number") or "").strip().upper()

        # Direct Database Fallback Lookup from flat projects table
        if job_num:
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT 
                            tbc_job_number, project_name, site_name, po_number, tbco_account_number,
                            contractor_company_name, street_address_1, street_address_2, city, state,
                            postal_code, country, pm_first_name, pm_last_name, pm_email, pm_phone,
                            sales_rep_email, sales_rep_phone, team_code
                        FROM projects
                        WHERE UPPER(tbc_job_number) = ?
                        LIMIT 1
                    """, (job_num,))
                    row = cursor.fetchone()
                    if row:
                        db_dict = dict(row)
                        for k, v in db_dict.items():
                            if k not in payload or not payload[k]:
                                payload[k] = v
            except Exception as err:
                logging.warning(f"Local prefill lookup note: {err}")

        # Resolve Sales User Details from 'users' table
        sales_email_val = str(payload.get("sales_rep_email") or "").strip().lower()
        if sales_email_val and not payload.get("sales_rep_first_name"):
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT first_name, last_name, user_phone FROM users WHERE LOWER(user_email) = ?", (sales_email_val,))
                    u_row = cursor.fetchone()
                    if u_row:
                        payload["sales_rep_first_name"] = u_row["first_name"] or ""
                        payload["sales_rep_last_name"] = u_row["last_name"] or ""
                        payload["sales_rep_phone"] = u_row["user_phone"] or ""
            except Exception as err:
                logging.warning(f"Sales user resolution note: {err}")

        # Populate Input Controls Safely
        tf_sales_email.value = sales_email_val
        tf_sales_first.value = payload.get("sales_rep_first_name") or payload.get("first_name") or ""
        tf_sales_last.value = payload.get("sales_rep_last_name") or payload.get("last_name") or ""
        tf_sales_phone.value = payload.get("sales_rep_phone") or payload.get("user_phone") or ""
        dd_team_code.value = payload.get("team_code") or None

        tf_company.value = payload.get("contractor_company_name") or payload.get("company_name") or ""
        tf_company_acct.value = payload.get("tbco_account_number") or ""

        tf_pm_first.value = payload.get("pm_first_name") or payload.get("project_site_contact_first_name") or ""
        tf_pm_last.value = payload.get("pm_last_name") or payload.get("project_site_contact_last_name") or ""
        tf_pm_email.value = payload.get("pm_email") or payload.get("project_site_contact_email") or ""
        tf_pm_phone.value = payload.get("pm_phone") or payload.get("project_site_contact_phone") or ""

        tf_job_num.value = job_num or payload.get("tbc_job_number", "")
        tf_site_name.value = payload.get("site_name", "")
        tf_proj_name.value = payload.get("project_name", "")
        tf_po_num.value = payload.get("po_number", "")

        tf_street_1.value = payload.get("street_address_1", "")
        tf_street_2.value = payload.get("street_address_2", "")
        tf_city.value = payload.get("city", "")
        tf_state.value = payload.get("state", "")
        tf_postal.value = payload.get("postal_code", "")

        tf_contact_first.value = payload.get("project_site_contact_first_name") or payload.get("pm_first_name") or ""
        tf_contact_last.value = payload.get("project_site_contact_last_name") or payload.get("pm_last_name") or ""
        tf_contact_email.value = payload.get("project_site_contact_email") or payload.get("pm_email") or ""
        tf_contact_phone.value = payload.get("project_site_contact_phone") or payload.get("pm_phone") or ""

        if page:
            page.update()

    def clear_form(e=None):
        if get_tech_options_fn:
            dd_technician.options = get_tech_options_fn()

        tf_sales_first.value = ""
        tf_sales_last.value = ""
        tf_sales_email.value = ""
        tf_sales_phone.value = ""
        dd_team_code.value = None

        tf_job_num.value = ""
        tf_company.value = ""
        tf_company_acct.value = ""
        tf_site_name.value = ""
        tf_proj_name.value = ""
        tf_po_num.value = ""

        tf_pm_first.value = ""
        tf_pm_last.value = ""
        tf_pm_email.value = ""
        tf_pm_phone.value = ""

        tf_street_1.value = ""
        tf_street_2.value = ""
        tf_city.value = ""
        tf_state.value = ""
        tf_postal.value = ""

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
            show_toast(page, "Job #, Campus Name, Project Name, Street, City, and Sales Rep First Name are required!", kind="error")
            return

        job_num = tf_job_num.value.strip().upper()
        proj_name = tf_proj_name.value.strip()
        site_name = tf_site_name.value.strip()
        po_num = tf_po_num.value.strip() if tf_po_num.value else ""

        sales_email_val = tf_sales_email.value.strip().lower() if tf_sales_email.value else ""
        if sales_email_val:
            resolve_sales_user(
                user_email=sales_email_val,
                first_name=tf_sales_first.value.strip(),
                last_name=tf_sales_last.value.strip(),
                user_phone=tf_sales_phone.value.strip()
            )

        acct_val = None
        if tf_company.value:
            acct_val = tf_company_acct.value.strip().upper() if tf_company_acct.value else f"CON-{job_num[:4]}"
            resolve_contractor(acct_val, tf_company.value.strip())

        pm_email_val = tf_pm_email.value.strip().lower() if tf_pm_email.value else ""
        clean_pm_id = None
        if pm_email_val and acct_val:
            clean_pm_id = resolve_pm_contact(
                tbco_account_number=acct_val,
                first_name=tf_pm_first.value.strip() if tf_pm_first.value else "",
                last_name=tf_pm_last.value.strip() if tf_pm_last.value else "",
                email=pm_email_val,
                phone=tf_pm_phone.value.strip() if tf_pm_phone.value else "",
                title="Project Manager"
            )

        clean_site = resolve_location(site_name, tf_street_1.value.strip(), tf_street_2.value.strip() if tf_street_2.value else "", tf_city.value.strip(), tf_state.value.strip(), tf_postal.value.strip() if tf_postal.value else "", country="US")

        # Step 1: Check if Project Space Exists in Local SQLite (Flat Write)
        drive_id = None
        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT drive_id FROM projects WHERE tbc_job_number = ?", (job_num,))
                proj_row = cursor.fetchone()

                if proj_row:
                    drive_id = proj_row["drive_id"]
                else:
                    drive_info = ensure_project_drive_folder(
                        job_number=job_num,
                        project_name=proj_name,
                        requestor_name=f"{tf_sales_first.value} {tf_sales_last.value}".strip(),
                        requestor_email=sales_email_val,
                        attached_file_paths=staged_documents
                    )
                    drive_id = drive_info.get("drive_id", f"FLD-GDRV-{job_num}")

                    cursor.execute("""
                        INSERT OR REPLACE INTO projects (
                            tbc_job_number, site_name, tbco_account_number, pm_contact_id, project_name,
                            contractor_company_name, street_address_1, street_address_2, city, state,
                            postal_code, country, sales_rep_email, sales_rep_phone, team_code,
                            pm_first_name, pm_last_name, pm_email, pm_phone, po_number, drive_id, stage
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'In Progress')
                    """, (
                        job_num, clean_site, acct_val, clean_pm_id, proj_name,
                        tf_company.value.strip(), tf_street_1.value.strip(), tf_street_2.value.strip() if tf_street_2.value else "",
                        tf_city.value.strip(), tf_state.value.strip(), tf_postal.value.strip() if tf_postal.value else "", "US",
                        sales_email_val, tf_sales_phone.value.strip() if tf_sales_phone.value else "",
                        dd_team_code.value if dd_team_code.value else "",
                        tf_pm_first.value.strip() if tf_pm_first.value else "",
                        tf_pm_last.value.strip() if tf_pm_last.value else "",
                        pm_email_val, tf_pm_phone.value.strip() if tf_pm_phone.value else "",
                        po_num, drive_id
                    ))
                    conn.commit()

                    if firestore_db is not None:
                        try:
                            firestore_db.collection("projects").document(job_num).set({
                                "tbc_job_number": job_num,
                                "site_name": clean_site,
                                "tbco_account_number": acct_val,
                                "pm_contact_id": clean_pm_id,
                                "project_name": proj_name,
                                "contractor_company_name": tf_company.value.strip(),
                                "street_address_1": tf_street_1.value.strip(),
                                "street_address_2": tf_street_2.value.strip() if tf_street_2.value else "",
                                "city": tf_city.value.strip(),
                                "state": tf_state.value.strip(),
                                "postal_code": tf_postal.value.strip() if tf_postal.value else "",
                                "country": "US",
                                "sales_rep_email": sales_email_val,
                                "sales_rep_phone": tf_sales_phone.value.strip() if tf_sales_phone.value else "",
                                "team_code": dd_team_code.value if dd_team_code.value else "",
                                "pm_first_name": tf_pm_first.value.strip() if tf_pm_first.value else "",
                                "pm_last_name": tf_pm_last.value.strip() if tf_pm_last.value else "",
                                "pm_email": pm_email_val,
                                "pm_phone": tf_pm_phone.value.strip() if tf_pm_phone.value else "",
                                "po_number": po_num,
                                "drive_id": drive_id,
                                "stage": "In Progress"
                            }, merge=True)
                        except Exception as fs_err:
                            logging.error(f"Firestore project auto-create sync error: {fs_err}")
        except Exception as p_err:
            logging.error(f"Project space check/create error: {p_err}")

        # Step 2: Save Service Request Ticket to INTAKE_LEDGER
        req_id = f"REQ-{int(time.time())}"
        triage_val = "Dispatched" if (dd_technician.value and dd_technician.value.strip()) else "Unassigned"
        
        intake_payload = {
            "request_id": req_id,
            "tbc_job_number": job_num,
            "team_code": dd_team_code.value or "",
            "site_name": clean_site,
            "project_name": proj_name,
            "contractor_company_name": tf_company.value.strip(),
            "tbco_account_number": acct_val or "",
            "pm_contact_id": clean_pm_id,
            "pm_first_name": tf_pm_first.value.strip() if tf_pm_first.value else "",
            "pm_last_name": tf_pm_last.value.strip() if tf_pm_last.value else "",
            "pm_email": pm_email_val,
            "pm_phone": tf_pm_phone.value.strip() if tf_pm_phone.value else "",
            "street_address_1": tf_street_1.value.strip(),
            "street_address_2": tf_street_2.value.strip() if tf_street_2.value else "",
            "city": tf_city.value.strip(),
            "state": tf_state.value.strip(),
            "postal_code": tf_postal.value.strip() if tf_postal.value else "",
            "country": "US",
            "sales_rep_email": sales_email_val,
            "sales_rep_phone": tf_sales_phone.value.strip() if tf_sales_phone.value else "",
            "sales_rep_first_name": tf_sales_first.value.strip() if tf_sales_first.value else "",
            "sales_rep_last_name": tf_sales_last.value.strip() if tf_sales_last.value else "",
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
                    INSERT INTO intake_ledger (
                        request_id, tbc_job_number, team_code, site_name, project_name,
                        contractor_company_name, street_address_1, street_address_2, city, state,
                        postal_code, country, sales_rep_email, sales_rep_phone,
                        project_site_contact_first_name, project_site_contact_last_name,
                        project_site_contact_email, project_site_contact_phone, issue_description,
                        triage_status, request_type, submission_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    intake_payload["request_id"], intake_payload["tbc_job_number"], intake_payload["team_code"],
                    intake_payload["site_name"], intake_payload["project_name"], intake_payload["contractor_company_name"],
                    intake_payload["street_address_1"], intake_payload["street_address_2"], intake_payload["city"],
                    intake_payload["state"], intake_payload["postal_code"], intake_payload["country"],
                    intake_payload["sales_rep_email"], intake_payload["sales_rep_phone"],
                    intake_payload["project_site_contact_first_name"], intake_payload["project_site_contact_last_name"],
                    intake_payload["project_site_contact_email"], intake_payload["project_site_contact_phone"],
                    intake_payload["issue_description"], intake_payload["triage_status"], intake_payload["request_type"],
                    intake_payload["submission_timestamp"]
                ))

                if dd_technician.value and tf_scheduled_time.value:
                    job_id = f"JOB-{int(time.time())}"
                    cursor.execute("""
                        INSERT INTO dispatches (job_id, tbc_job_number, technician_email, sales_rep_email, scheduled_time, status, job_type)
                        VALUES (?, ?, ?, ?, ?, 'Scheduled', ?)
                    """, (job_id, intake_payload["tbc_job_number"], dd_technician.value, sales_email_val, tf_scheduled_time.value.strip(), intake_payload["request_type"]))

                    dispatch_payload = {
                        "job_id": job_id,
                        "tbc_job_number": intake_payload["tbc_job_number"],
                        "technician_email": dd_technician.value.strip(),
                        "sales_rep_email": sales_email_val,
                        "scheduled_time": tf_scheduled_time.value.strip(),
                        "status": "Scheduled",
                        "job_type": intake_payload["request_type"],
                        "tbco_account_number": acct_val or "",
                        "site_name": clean_site
                    }
                    sync_engine.dispatch_sync_in_background(firestore_db, dispatch_payload)

                    try:
                        from src.backend.calendar_manager import GoogleCalendarManager, build_gcal_ticket_description
                        cal_manager = GoogleCalendarManager()
                        
                        full_address = f"{intake_payload['street_address_1']}, {intake_payload['city']}, {intake_payload['state']} {intake_payload['postal_code']}".strip(", ")
                        rich_desc = build_gcal_ticket_description(intake_payload)
                        sched_date = tf_scheduled_time.value.strip()
                        start_iso = f"{sched_date[:10]}T08:00:00Z" if len(sched_date) >= 10 else f"{time.strftime('%Y-%m-%d')}T08:00:00Z"
                        end_iso = f"{sched_date[:10]}T12:00:00Z" if len(sched_date) >= 10 else f"{time.strftime('%Y-%m-%d')}T12:00:00Z"
                        
                        cal_manager.publish_appointment(
                            job_id=job_id,
                            summary=f"Job #{intake_payload['tbc_job_number']} - {intake_payload['project_name']}",
                            location=full_address,
                            description=rich_desc,
                            start_iso=start_iso,
                            end_iso=end_iso
                        )
                    except Exception as cal_err:
                        logging.warning(f"Google Calendar sync deferred: {cal_err}")

                conn.commit()
        except Exception as sql_err:
            logging.error(f"SQLite intake insert error: {sql_err}")

        if firestore_db is not None:
            try:
                firestore_db.collection("intake_ledger").document(req_id).set(intake_payload, merge=True)
            except Exception as fs_err:
                logging.error(f"Firestore intake sync error: {fs_err}")

        show_toast(page, f"Service Request #{req_id} logged successfully!", kind="success")
        clear_form()

        if on_success_callback:
            on_success_callback(intake_payload)

    form_container = ft.Container(
        content=ft.Column([
            sales_instructions_note,
            ft.Row([tf_sales_email], spacing=10),
            ft.Row([tf_sales_first, tf_sales_last], spacing=10),
            ft.Row([tf_sales_phone, dd_team_code], spacing=10),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            contractor_instructions_note,
            ft.Row([tf_company, tf_company_acct], spacing=10),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Row([tf_pm_first, tf_pm_last], spacing=10),
            ft.Row([tf_pm_email, tf_pm_phone], spacing=10),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Row([tf_job_num, tf_proj_name], spacing=10),
            ft.Row([tf_site_name, tf_po_num], spacing=10),
            ft.Row([tf_street_1, tf_street_2], spacing=10),
            ft.Row([tf_city, tf_state, tf_postal], spacing=8),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Row([tf_contact_first, tf_contact_last], spacing=10),
            ft.Row([tf_contact_email, tf_contact_phone], spacing=10),
            
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Row([dd_request_type], spacing=10),
            tf_issue,
            ft.Row([dd_technician, tf_scheduled_time], spacing=10),
            ft.Row([
                ft.OutlinedButton("Upload Files", style=FieldFlowLightTheme.get_secondary_button_style(), on_click=lambda _: docs_picker.pick_files(allow_multiple=True)),
                docs_status_txt
            ], spacing=10),
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10)
        ], spacing=10, scroll=ft.ScrollMode.AUTO, tight=True),
        padding=10
    )

    form_container.submit_form = submit_service_request
    form_container.clear_form = clear_form
    form_container.populate_data = populate_data

    return form_container