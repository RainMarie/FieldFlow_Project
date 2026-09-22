"""
src/frontend/details_component.py
Consolidated detail modal views for FieldFlow using standardized key names,
a tabbed multi-view layout, hybrid local-first (SQLite + Firestore) project tab lookups,
and automatic Google Drive photo uploads for Project Master Records.
"""

import os
import sys
import logging
import glob
import uuid
from datetime import datetime
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
    resolve_sales_user
)
from src.frontend.cards_component import (
    build_site_asset_card,
    build_visit_history_card
)
from src.frontend.shared_utils import find_any_local_logo, get_base64_from_file, show_toast

VALID_TEAM_CODES = [
    "TC", "TI", "TJ", "TK", "TN", "TO", "TS", "TT", "TY",
    "FH", "FM", "FW", "JY", "JB", "JC", "JG", "JJ", "JK",
    "PJ", "PL", "PY", "RB", "RC", "RD", "RJ", "RO", "RQ", "RT", "RU"
]


def build_image_control(photo_url_or_path: str, height: int = 180) -> ft.Control:
    """Renders network images, local disk images, or fallback brand containers."""
    val = (photo_url_or_path or "").strip()
    if val.startswith("http://") or val.startswith("https://"):
        return ft.Image(src=val, height=height, fit=ft.ImageFit.COVER, border_radius=6)

    target_file = None
    if val and os.path.exists(val):
        if os.path.isfile(val):
            target_file = val
        elif os.path.isdir(val):
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.PNG"]:
                found = glob.glob(os.path.join(val, ext))
                if found:
                    target_file = found[0]
                    break

    if not target_file:
        target_file = find_any_local_logo()

    if target_file:
        b64 = get_base64_from_file(target_file)
        if b64:
            return ft.Container(
                content=ft.Image(src_base64=b64, height=height, fit=ft.ImageFit.CONTAIN),
                bgcolor=FieldFlowLightTheme.SURFACE_CARD, padding=6, border_radius=6, alignment=ft.alignment.center
            )

    return ft.Container(
        content=ft.Row([ft.Text("TBCo PROJECT SITE", weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.PINK_PRIMARY, size=13)], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
        bgcolor=FieldFlowLightTheme.BG_PINK_TINT, height=height, border_radius=6, border=ft.border.all(1, FieldFlowLightTheme.BORDER_PINK_EDGE), alignment=ft.alignment.center
    )


def build_project_detail_modal(
    page: ft.Page,
    open_drive_link_fn,
    show_toast_fn,
    on_save_callback=None,
    on_delete_callback=None
):
    """
    Renders an interactive, tabbed Project Detail Modal displaying Core Vitals,
    associated Service Requests, Site Assets, and Field Dispatches using hybrid lookups.
    """
    project_detail_modal_dialog = None

    active_project_state = {"tbc_job_number": None, "drive_id": None}

    def build_section_header(title_text: str, color_token=FieldFlowLightTheme.PINK_PRIMARY):
        return ft.Container(
            content=ft.Text(title_text.upper(), size=12, weight=ft.FontWeight.BOLD, color=color_token),
            padding=ft.padding.only(top=8, bottom=2)
        )

    # Form Fields for Tab 1: Project Vitals
    edit_project_job_num = ft.TextField(label="TBCo Job #*", read_only=True, border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_project_name = ft.TextField(label="Project Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_stage = ft.Dropdown(
        label="Project Stage",
        options=[
            ft.dropdown.Option("Active"),
            ft.dropdown.Option("In Progress"),
            ft.dropdown.Option("Completed"),
            ft.dropdown.Option("Archived")
        ],
        value="In Progress",
        border_color=FieldFlowLightTheme.BORDER_PINK_EDGE,
        expand=True
    )
    edit_drive_id = ft.TextField(label="Google Drive Folder ID", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)

    edit_company_name = ft.TextField(label="Contractor / Client Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_company_acct = ft.TextField(label="Company Account #", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)

    edit_site_name = ft.TextField(label="Campus / Site Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_street_1 = ft.TextField(label="Street Address 1*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_street_2 = ft.TextField(label="Street Address 2 / Unit", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_city = ft.TextField(label="City*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_state = ft.TextField(label="State*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_postal_code = ft.TextField(label="Postal Code*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_country = ft.TextField(label="Country", value="US", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)

    edit_pm_first_name = ft.TextField(label="Project Site Contact First Name", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_pm_last_name = ft.TextField(label="Project Site Contact Last Name", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_pm_email = ft.TextField(label="Project Site Contact Email", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    edit_pm_phone = ft.TextField(label="Project Site Contact Phone", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)

    staged_photo_path = {"value": ""}
    staged_documents = []

    photo_status_txt = ft.Text("No Custom Picture Selected", size=11, color=FieldFlowLightTheme.TEXT_MUTED)
    docs_status_txt = ft.Text("No Staged Documents", size=11, color=FieldFlowLightTheme.TEXT_MUTED)

    # Containers for Dynamic Tabs (Tabs 2, 3, & 4)
    requests_list_view = ft.Column(spacing=8, scroll=ft.ScrollMode.ALWAYS)
    assets_list_view = ft.Column(spacing=8, scroll=ft.ScrollMode.ALWAYS)
    dispatches_list_view = ft.Column(spacing=8, scroll=ft.ScrollMode.ALWAYS)

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

    if photo_picker not in page.overlay:
        page.overlay.append(photo_picker)
    if docs_picker not in page.overlay:
        page.overlay.append(docs_picker)

    def populate_project_data(proj_data, contractor_options=None, location_options=None, sales_options=None):
        """Populates Vitals form and performs dual lookup (SQLite + Firestore) for Requests, Assets, and Dispatches."""
        if isinstance(proj_data, dict):
            job_num = proj_data.get("tbc_job_number", "")
            proj_name = proj_data.get("project_name", "")
            client = proj_data.get("contractor_company_name") or proj_data.get("contractor_name") or proj_data.get("company_name", "")
            acct_num = proj_data.get("tbco_account_number", "")
            stage_val = proj_data.get("stage") or "In Progress"
            drive_val = proj_data.get("drive_id", "")
            
            s_name = proj_data.get("site_name", "")
            st1 = proj_data.get("street_address_1", "")
            st2 = proj_data.get("street_address_2", "")
            c_city = proj_data.get("city", "")
            c_state = proj_data.get("state", "")
            c_zip = proj_data.get("postal_code", "")
            c_country = proj_data.get("country", "US")

            pm_f = proj_data.get("pm_first_name") or proj_data.get("first_name", "")
            pm_l = proj_data.get("pm_last_name") or proj_data.get("last_name", "")
            pm_em = proj_data.get("pm_email") or proj_data.get("email", "")
            pm_ph = proj_data.get("pm_phone") or proj_data.get("phone", "")
            
            photo_val = proj_data.get("photo_url", "")
        else:
            return

        active_project_state["tbc_job_number"] = job_num
        active_project_state["drive_id"] = drive_val

        # Populate Tab 1 Inputs
        edit_project_job_num.value = str(job_num or "")
        edit_project_name.value = str(proj_name or "")
        edit_company_name.value = str(client or "")
        edit_company_acct.value = str(acct_num or "")
        edit_stage.value = str(stage_val or "In Progress")
        edit_drive_id.value = str(drive_val or "")

        edit_site_name.value = str(s_name or "")
        edit_street_1.value = str(st1 or "")
        edit_street_2.value = str(st2 or "")
        edit_city.value = str(c_city or "")
        edit_state.value = str(c_state or "")
        edit_postal_code.value = str(c_zip or "")
        edit_country.value = str(c_country or "US")

        edit_pm_first_name.value = str(pm_f or "")
        edit_pm_last_name.value = str(pm_l or "")
        edit_pm_email.value = str(pm_em or "")
        edit_pm_phone.value = str(pm_ph or "")

        staged_photo_path["value"] = photo_val
        if photo_val:
            photo_status_txt.value = f"Current Photo: {os.path.basename(photo_val)}"
            photo_status_txt.color = FieldFlowLightTheme.PRIMARY_GREEN
        else:
            photo_status_txt.value = "No Custom Picture Selected"
            photo_status_txt.color = FieldFlowLightTheme.TEXT_MUTED

        # --- Dual Retrieval: Step 1: Local SQLite Query ---
        local_requests = []
        local_assets = []
        local_dispatches = []
        if job_num:
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute("""
                        SELECT request_id, request_type, triage_status, issue_description, submission_timestamp
                        FROM intake_requests
                        WHERE tbc_job_number = ?
                        ORDER BY submission_timestamp DESC
                    """, (job_num,))
                    local_requests = [dict(r) for r in cursor.fetchall()]

                    cursor.execute("""
                        SELECT asset_id, equipment_tag, model_number, serial_number, operational_status
                        FROM assets
                        WHERE tbc_job_number = ?
                    """, (job_num,))
                    local_assets = [dict(r) for r in cursor.fetchall()]

                    cursor.execute("""
                        SELECT job_id, technician_email, scheduled_time, status, job_type
                        FROM dispatches
                        WHERE tbc_job_number = ?
                        ORDER BY scheduled_time DESC
                    """, (job_num,))
                    local_dispatches = [dict(r) for r in cursor.fetchall()]

            except Exception as sql_err:
                logging.error(f"SQLite project detail tab lookup error: {sql_err}")

        # --- Dual Retrieval: Step 2: Cloud Firestore Hybrid Query & Merge ---
        cloud_requests = []
        cloud_assets = []
        cloud_dispatches = []
        if job_num and firestore_db is not None:
            try:
                fs_reqs = firestore_db.collection("intake_requests").where("tbc_job_number", "==", job_num).stream()
                for doc in fs_reqs:
                    d = doc.to_dict()
                    d["request_id"] = doc.id
                    cloud_requests.append(d)

                fs_assets = firestore_db.collection("assets").where("tbc_job_number", "==", job_num).stream()
                for doc in fs_assets:
                    d = doc.to_dict()
                    d["asset_id"] = doc.id
                    cloud_assets.append(d)

                fs_disp = firestore_db.collection("dispatches").where("tbc_job_number", "==", job_num).stream()
                for doc in fs_disp:
                    d = doc.to_dict()
                    d["job_id"] = doc.id
                    cloud_dispatches.append(d)
            except Exception as fs_err:
                logging.error(f"Firestore project detail tab lookup note: {fs_err}")

        # Merge local & cloud records cleanly using key IDs
        req_map = {r.get("request_id"): r for r in local_requests if r.get("request_id")}
        for r in cloud_requests:
            if r.get("request_id") and r.get("request_id") not in req_map:
                req_map[r.get("request_id")] = r
        merged_requests = list(req_map.values())

        ast_map = {a.get("asset_id"): a for a in local_assets if a.get("asset_id")}
        for a in cloud_assets:
            if a.get("asset_id") and a.get("asset_id") not in ast_map:
                ast_map[a.get("asset_id")] = a
        merged_assets = list(ast_map.values())

        disp_map = {d.get("job_id"): d for d in local_dispatches if d.get("job_id")}
        for d in cloud_dispatches:
            if d.get("job_id") and d.get("job_id") not in disp_map:
                disp_map[d.get("job_id")] = d
        merged_dispatches = list(disp_map.values())

        # Render Tab 2: Service Requests List
        requests_list_view.controls.clear()
        if merged_requests:
            for req in merged_requests:
                requests_list_view.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Request #{req.get('request_id', 'N/A')}", weight=ft.FontWeight.BOLD, size=13, color=FieldFlowLightTheme.TEXT_PRIMARY),
                                ft.Text(req.get("triage_status", "Unassigned"), size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(f"Type: {req.get('request_type', 'General')}  |  Date: {str(req.get('submission_timestamp', ''))[:10]}", size=11, color=FieldFlowLightTheme.TEXT_MUTED),
                            ft.Text(f"Issue: {req.get('issue_description', 'N/A')}", size=11, color=FieldFlowLightTheme.TEXT_PRIMARY)
                        ], spacing=3),
                        bgcolor=FieldFlowLightTheme.SURFACE_HOVER,
                        padding=10,
                        border_radius=6,
                        border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE)
                    )
                )
        else:
            requests_list_view.controls.append(
                ft.Text("No service requests found for this job.", size=12, italic=True, color=FieldFlowLightTheme.TEXT_MUTED)
            )

        # Render Tab 3: Assets List
        assets_list_view.controls.clear()
        if merged_assets:
            for ast in merged_assets:
                assets_list_view.controls.append(build_site_asset_card(ast))
        else:
            assets_list_view.controls.append(
                ft.Text("No registered assets found for this job.", size=12, italic=True, color=FieldFlowLightTheme.TEXT_MUTED)
            )

        # Render Tab 4: Dispatches List
        dispatches_list_view.controls.clear()
        if merged_dispatches:
            for disp in merged_dispatches:
                dispatches_list_view.controls.append(build_visit_history_card(disp))
        else:
            dispatches_list_view.controls.append(
                ft.Text("No field dispatches scheduled for this job.", size=12, italic=True, color=FieldFlowLightTheme.TEXT_MUTED)
            )

        # UI Refresh
        if page:
            page.update()

    def save_project_detail_edits(e):
        if not edit_project_job_num.value or not edit_project_name.value or not edit_company_name.value or not edit_site_name.value or not edit_street_1.value or not edit_city.value or not edit_state.value:
            show_toast(page, "Job #, Project Name, Contractor, Site Name, Street, City, and State are required!", kind="error")
            return

        job_num = edit_project_job_num.value.strip().upper()
        proj_name = edit_project_name.value.strip()
        company_name = edit_company_name.value.strip()
        company_acct = edit_company_acct.value.strip().upper() if edit_company_acct.value else f"CON-{job_num[:4]}"

        site_name = edit_site_name.value.strip()
        street_1 = edit_street_1.value.strip()
        street_2 = edit_street_2.value.strip() if edit_street_2.value else ""
        city_val = edit_city.value.strip()
        state_val = edit_state.value.strip()
        postal_val = edit_postal_code.value.strip() if edit_postal_code.value else ""
        country_val = edit_country.value.strip() if edit_country.value else "US"

        pm_first = edit_pm_first_name.value.strip() if edit_pm_first_name.value else ""
        pm_last = edit_pm_last_name.value.strip() if edit_pm_last_name.value else ""
        pm_email = edit_pm_email.value.strip().lower() if edit_pm_email.value else ""
        pm_phone = edit_pm_phone.value.strip() if edit_pm_phone.value else ""

        stage_val = edit_stage.value or "In Progress"
        drive_id_val = edit_drive_id.value.strip() if edit_drive_id.value else f"FLD-DRIVE-{job_num}"

        # Collect all staged files (Cover photo + multi-file documents)
        files_to_upload = []
        raw_photo_path = staged_photo_path["value"]
        if raw_photo_path and os.path.exists(raw_photo_path) and os.path.isfile(raw_photo_path):
            files_to_upload.append(raw_photo_path)

        for doc_p in staged_documents:
            if doc_p and os.path.exists(doc_p) and os.path.isfile(doc_p) and doc_p not in files_to_upload:
                files_to_upload.append(doc_p)

        # Perform Google Drive upload and extract direct thumbnail URL
        final_photo_url = raw_photo_path
        if files_to_upload:
            try:
                from src.backend.drive_service import ensure_project_drive_folder
                drive_info = ensure_project_drive_folder(
                    job_number=job_num,
                    project_name=proj_name,
                    requestor_name=f"{pm_first} {pm_last}".strip() or "FieldFlow User",
                    requestor_email=pm_email or "user@tombarrow.com",
                    attached_file_paths=files_to_upload
                )
                if drive_info.get("photo_url"):
                    final_photo_url = drive_info.get("photo_url")
            except Exception as drive_err:
                logging.warning(f"Google Drive photo upload note: {drive_err}")

        updated_payload = {
            "tbc_job_number": job_num,
            "site_name": site_name,
            "tbco_account_number": company_acct,
            "project_name": proj_name,
            "contractor_company_name": company_name,
            "contractor_name": company_name,
            "street_address_1": street_1,
            "street_address_2": street_2,
            "city": city_val,
            "state": state_val,
            "postal_code": postal_val,
            "country": country_val,
            "pm_first_name": pm_first,
            "pm_last_name": pm_last,
            "pm_email": pm_email,
            "pm_phone": pm_phone,
            "stage": stage_val,
            "drive_id": drive_id_val,
            "photo_url": final_photo_url
        }

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()

                # Dynamic Schema Migration Check for photo_url
                cursor.execute("PRAGMA table_info(projects);")
                proj_cols = [row[1] for row in cursor.fetchall()]
                if "photo_url" not in proj_cols:
                    cursor.execute("ALTER TABLE projects ADD COLUMN photo_url TEXT;")

                # Step 1: Upsert into LOCATIONS table
                cursor.execute("""
                    INSERT OR REPLACE INTO locations (
                        site_name, street_address_1, street_address_2, city, state, postal_code, country
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (site_name, street_1, street_2, city_val, state_val, postal_val, country_val))

                # Step 2: Upsert into CONTRACTORS table
                cursor.execute("""
                    INSERT OR REPLACE INTO contractors (tbco_account_number, company_name)
                    VALUES (?, ?)
                """, (company_acct, company_name))

                # Step 3: Upsert into CONTACTS table (if PM contact details provided)
                pm_contact_id = None
                if pm_email:
                    cursor.execute("SELECT contact_id FROM contacts WHERE LOWER(email) = ?", (pm_email,))
                    row = cursor.fetchone()
                    pm_contact_id = row["contact_id"] if row else f"CONT-{uuid.uuid4().hex[:8].upper()}"

                    cursor.execute("""
                        INSERT OR REPLACE INTO contacts (
                            contact_id, tbco_account_number, first_name, last_name, title, phone, email
                        ) VALUES (?, ?, ?, ?, 'Project Manager', ?, ?)
                    """, (pm_contact_id, company_acct, pm_first, pm_last, pm_phone, pm_email))

                updated_payload["pm_contact_id"] = pm_contact_id

                # Step 4: Upsert into PROJECTS master table (including photo_url)
                cursor.execute("""
                    INSERT OR REPLACE INTO projects (
                        tbc_job_number, site_name, tbco_account_number, pm_contact_id,
                        project_name, drive_id, stage, photo_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (job_num, site_name, company_acct, pm_contact_id, proj_name, drive_id_val, stage_val, final_photo_url))

                # Step 5: Sync all matching records in INTAKE_REQUESTS table
                cursor.execute("""
                    UPDATE intake_requests
                    SET project_name = ?, contractor_company_name = ?, site_name = ?,
                        street_address_1 = ?, street_address_2 = ?, city = ?, state = ?,
                        postal_code = ?, country = ?, project_site_contact_first_name = ?,
                        project_site_contact_last_name = ?, project_site_contact_email = ?,
                        project_site_contact_phone = ?
                    WHERE tbc_job_number = ?
                """, (
                    proj_name, company_name, site_name, street_1, street_2, city_val, state_val,
                    postal_val, country_val, pm_first, pm_last, pm_email, pm_phone, job_num
                ))

                conn.commit()

            # Step 6: Firestore Cloud Mirror Write
            if firestore_db is not None:
                try:
                    firestore_db.collection("projects").document(job_num).set(updated_payload, merge=True)
                except Exception as fs_err:
                    logging.error(f"Firestore project update error: {fs_err}")

            show_toast(page, f"Project #{job_num} Master Record Saved!", kind="success")
            if project_detail_modal_dialog:
                project_detail_modal_dialog.open = False
            page.update()

            if on_save_callback:
                on_save_callback(updated_payload)

        except Exception as sql_err:
            logging.error(f"SQLite project detail save error: {sql_err}")
            show_toast(page, f"Save Failed: {str(sql_err)}", kind="error")

    # Tab 1 View: Form Container
    vitals_tab_content = ft.Container(
        padding=ft.padding.only(left=8, right=16, top=8, bottom=8),
        content=ft.Column([
            build_section_header("1. Core Project Vitals"),
            ft.Row([edit_project_job_num, edit_project_name], spacing=10),
            ft.Row([edit_stage, edit_drive_id], spacing=10),

            build_section_header("2. Contractor & Client Details"),
            ft.Row([edit_company_name, edit_company_acct], spacing=10),

            build_section_header("3. Site Location & Address Details"),
            ft.Row([edit_site_name], spacing=10),
            ft.Row([edit_street_1, edit_street_2], spacing=10),
            ft.Row([edit_city, edit_state, edit_postal_code, edit_country], spacing=8),

            build_section_header("4. Project Site Contact"),
            ft.Row([edit_pm_first_name, edit_pm_last_name], spacing=10),
            ft.Row([edit_pm_email, edit_pm_phone], spacing=10),

            build_section_header("5. Project Media & Attachments", color_token=FieldFlowLightTheme.PRIMARY_GREEN),
            ft.Row([
                ft.OutlinedButton("Upload Photo", icon=ft.icons.IMAGE, style=FieldFlowLightTheme.get_secondary_button_style(), on_click=lambda _: photo_picker.pick_files(allow_multiple=False)),
                ft.OutlinedButton("Upload Files", icon=ft.icons.ATTACH_FILE, style=FieldFlowLightTheme.get_secondary_button_style(), on_click=lambda _: docs_picker.pick_files(allow_multiple=True))
            ], spacing=10),
            ft.Row([photo_status_txt]),
            ft.Row([docs_status_txt])
        ], spacing=10, scroll=ft.ScrollMode.ALWAYS)
    )

    # Multi-Tab Layout Construction
    modal_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=200,
        tabs=[
            ft.Tab(text="Project Vitals", content=vitals_tab_content),
            ft.Tab(text="Service Requests", content=ft.Container(padding=10, content=requests_list_view)),
            ft.Tab(text="Site Assets", content=ft.Container(padding=10, content=assets_list_view)),
            ft.Tab(text="Dispatches", content=ft.Container(padding=10, content=dispatches_list_view)),
        ],
        expand=True
    )

    project_detail_modal_dialog = ft.AlertDialog(
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        title=ft.Row([
            ft.Icon(ft.icons.BUSINESS, color=FieldFlowLightTheme.PINK_PRIMARY, size=26),
            ft.Text("Project Master Record & Activity Hub", size=18, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY)
        ]),
        content=ft.Container(
            width=760, height=580, padding=ft.padding.all(6),
            content=modal_tabs
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: [setattr(project_detail_modal_dialog, 'open', False), page.update()]),
            ft.ElevatedButton("Save Project Details", icon=ft.icons.SAVE, style=FieldFlowLightTheme.get_primary_button_style(), on_click=save_project_detail_edits)
        ]
    )

    return project_detail_modal_dialog, populate_project_data


def build_ticket_detail_modal(
    page: ft.Page,
    get_tech_options_fn,
    trigger_date_picker_fn,
    on_save_callback=None
):
    """Editable Service Ticket Detail Modal using normalized schema and sales user lookups."""
    active_ticket_state = {"request_id": None, "tbc_job_number": None}

    def build_section_header(title_text: str, color_token=FieldFlowLightTheme.PINK_PRIMARY):
        return ft.Container(
            content=ft.Text(title_text.upper(), size=12, weight=ft.FontWeight.BOLD, color=color_token),
            padding=ft.padding.only(top=8, bottom=2)
        )

    dt_sales_first_name = ft.TextField(label="Sales Rep First Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_sales_last_name = ft.TextField(label="Sales Rep Last Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_sales_email = ft.TextField(label="Sales Rep Email*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_sales_phone = ft.TextField(label="Sales Rep Phone", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_team_code = ft.Dropdown(label="Team Code*", options=[ft.dropdown.Option(code) for code in VALID_TEAM_CODES], border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)

    dt_job_num = ft.TextField(label="TBCo Job #*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_company_name = ft.TextField(label="Contractor / Client Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_site_name = ft.TextField(label="Campus / Site Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_project_name = ft.TextField(label="Project Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)

    dt_street_1 = ft.TextField(label="Street Address 1*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_street_2 = ft.TextField(label="Street Address 2 / Unit", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_city = ft.TextField(label="City*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_state = ft.TextField(label="State*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_postal_code = ft.TextField(label="Postal Code*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_country = ft.TextField(label="Country", value="US", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)

    dt_request_type = ft.Dropdown(
        label="Request Type*",
        options=[
            ft.dropdown.Option("VFD Startup"),
            ft.dropdown.Option("Troubleshooting & Repair"),
            ft.dropdown.Option("Warranty Registration"),
            ft.dropdown.Option("Preventative Maintenance")
        ],
        border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True
    )
    dt_issue = ft.TextField(label="Issue Description*", multiline=True, min_lines=2, max_lines=4, border_color=FieldFlowLightTheme.BORDER_PINK_EDGE)

    dt_contact_first_name = ft.TextField(label="Project Site Contact First Name", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_contact_last_name = ft.TextField(label="Project Site Contact Last Name", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_contact_email = ft.TextField(label="Project Site Contact Email", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_contact_phone = ft.TextField(label="Project Site Contact Phone", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)

    dt_tech_select = ft.Dropdown(label="Assigned Tech Email", options=get_tech_options_fn(), border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_date_select = ft.TextField(label="Scheduled Date", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    dt_status_select = ft.Dropdown(
        label="Triage Status*",
        options=[
            ft.dropdown.Option("Unassigned"),
            ft.dropdown.Option("Dispatched"),
            ft.dropdown.Option("Completed"),
            ft.dropdown.Option("Cancelled")
        ],
        border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True
    )

    def populate_ticket_data(req_data: dict, dispatch_data: dict = None):
        """Populates modal fields looking up sales user details directly from users table."""
        active_ticket_state["request_id"] = req_data.get("request_id")
        active_ticket_state["tbc_job_number"] = req_data.get("tbc_job_number") or ""

        sales_email_val = req_data.get("sales_rep_email") or ""
        dt_sales_email.value = sales_email_val
        dt_sales_phone.value = req_data.get("sales_rep_phone") or ""
        dt_team_code.value = req_data.get("team_code") or None

        if sales_email_val:
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT first_name, last_name, user_phone FROM users WHERE LOWER(user_email) = ?", (sales_email_val.lower(),))
                    row = cursor.fetchone()
                    if row:
                        dt_sales_first_name.value = row["first_name"] or ""
                        dt_sales_last_name.value = row["last_name"] or ""
                        if not dt_sales_phone.value:
                            dt_sales_phone.value = row["user_phone"] or ""
            except Exception as err:
                logging.warning(f"Error fetching sales rep details for modal: {err}")

        dt_job_num.value = req_data.get("tbc_job_number") or ""
        dt_company_name.value = req_data.get("contractor_company_name") or ""
        dt_site_name.value = req_data.get("site_name") or ""
        dt_project_name.value = req_data.get("project_name") or ""

        dt_street_1.value = req_data.get("street_address_1") or ""
        dt_street_2.value = req_data.get("street_address_2") or ""
        dt_city.value = req_data.get("city") or ""
        dt_state.value = req_data.get("state") or ""
        dt_postal_code.value = req_data.get("postal_code") or ""
        dt_country.value = req_data.get("country") or "US"

        dt_request_type.value = req_data.get("request_type") or "VFD Startup"
        dt_issue.value = req_data.get("issue_description") or ""

        dt_contact_first_name.value = req_data.get("project_site_contact_first_name") or ""
        dt_contact_last_name.value = req_data.get("project_site_contact_last_name") or ""
        dt_contact_email.value = req_data.get("project_site_contact_email") or ""
        dt_contact_phone.value = req_data.get("project_site_contact_phone") or ""

        dt_status_select.value = req_data.get("triage_status") or "Unassigned"

        if dispatch_data:
            dt_tech_select.value = dispatch_data.get("technician_email") or None
            dt_date_select.value = dispatch_data.get("scheduled_time") or datetime.now().strftime("%Y-%m-%d")

    def save_ticket_detail_edits(e):
        if not dt_job_num.value or not dt_site_name.value or not dt_street_1.value or not dt_city.value or not dt_state.value:
            show_toast(page, "Job #, Campus Name, Street, City, and State are required!", kind="error")
            return

        req_id = active_ticket_state["request_id"]
        job_num = dt_job_num.value.strip().upper()
        sales_email = dt_sales_email.value.strip().lower() if dt_sales_email.value else ""

        if sales_email:
            resolve_sales_user(
                user_email=sales_email,
                first_name=dt_sales_first_name.value.strip() if dt_sales_first_name.value else "",
                last_name=dt_sales_last_name.value.strip() if dt_sales_last_name.value else "",
                user_phone=dt_sales_phone.value.strip() if dt_sales_phone.value else ""
            )

        updated_payload = {
            "request_id": req_id,
            "tbc_job_number": job_num,
            "team_code": dt_team_code.value or "",
            "site_name": dt_site_name.value.strip(),
            "project_name": dt_project_name.value.strip(),
            "contractor_company_name": dt_company_name.value.strip(),
            "street_address_1": dt_street_1.value.strip(),
            "street_address_2": dt_street_2.value.strip() if dt_street_2.value else "",
            "city": dt_city.value.strip(),
            "state": dt_state.value.strip(),
            "postal_code": dt_postal_code.value.strip() if dt_postal_code.value else "",
            "country": dt_country.value.strip() if dt_country.value else "US",
            "sales_rep_email": sales_email,
            "sales_rep_phone": dt_sales_phone.value.strip() if dt_sales_phone.value else "",
            "project_site_contact_first_name": dt_contact_first_name.value.strip() if dt_contact_first_name.value else "",
            "project_site_contact_last_name": dt_contact_last_name.value.strip() if dt_contact_last_name.value else "",
            "project_site_contact_email": dt_contact_email.value.strip() if dt_contact_email.value else "",
            "project_site_contact_phone": dt_contact_phone.value.strip() if dt_contact_phone.value else "",
            "issue_description": dt_issue.value.strip() if dt_issue.value else "",
            "triage_status": dt_status_select.value or "Unassigned",
            "request_type": dt_request_type.value or "VFD Startup"
        }

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE intake_requests
                    SET tbc_job_number = ?, team_code = ?, site_name = ?, project_name = ?,
                        contractor_company_name = ?, street_address_1 = ?, street_address_2 = ?,
                        city = ?, state = ?, postal_code = ?, country = ?, sales_rep_email = ?,
                        sales_rep_phone = ?, project_site_contact_first_name = ?,
                        project_site_contact_last_name = ?, project_site_contact_email = ?,
                        project_site_contact_phone = ?, issue_description = ?,
                        triage_status = ?, request_type = ?
                    WHERE request_id = ?
                """, (
                    job_num, updated_payload["team_code"], updated_payload["site_name"], updated_payload["project_name"],
                    updated_payload["contractor_company_name"], updated_payload["street_address_1"], updated_payload["street_address_2"],
                    updated_payload["city"], updated_payload["state"], updated_payload["postal_code"], updated_payload["country"],
                    updated_payload["sales_rep_email"], updated_payload["sales_rep_phone"], updated_payload["project_site_contact_first_name"],
                    updated_payload["project_site_contact_last_name"], updated_payload["project_site_contact_email"],
                    updated_payload["project_site_contact_phone"], updated_payload["issue_description"],
                    updated_payload["triage_status"], updated_payload["request_type"], req_id
                ))
                conn.commit()
        except Exception as sql_err:
            logging.error(f"SQLite update error: {sql_err}")

        if firestore_db is not None:
            try:
                firestore_db.collection("intake_requests").document(req_id).set(updated_payload, merge=True)
            except Exception as fs_err:
                logging.error(f"Firestore update error: {fs_err}")

        show_toast(page, f"Service Ticket {req_id} Saved Successfully!", kind="success")
        ticket_detail_modal_dialog.open = False
        page.update()

        if on_save_callback:
            on_save_callback(updated_payload)

    ticket_detail_modal_dialog = ft.AlertDialog(
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        title=ft.Row([
            ft.Icon(ft.icons.EDIT_NOTE, color=FieldFlowLightTheme.PINK_PRIMARY, size=26),
            ft.Text("Editable Service Ticket Details", size=18, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY)
        ]),
        content=ft.Container(
            content=ft.Column([
                build_section_header("1. Sales Rep Details"),
                ft.Row([dt_sales_first_name, dt_sales_last_name], spacing=10),
                ft.Row([dt_sales_email, dt_sales_phone, dt_team_code], spacing=10),

                build_section_header("2. Job & Site Details"),
                ft.Row([dt_job_num, dt_company_name], spacing=10),
                ft.Row([dt_site_name, dt_project_name], spacing=10),

                build_section_header("3. Address Details"),
                ft.Row([dt_street_1, dt_street_2], spacing=10),
                ft.Row([dt_city, dt_state, dt_postal_code, dt_country], spacing=8),

                build_section_header("4. Service Description"),
                ft.Row([dt_request_type]),
                dt_issue,

                build_section_header("5. Project Site Contact"),
                ft.Row([dt_contact_first_name, dt_contact_last_name], spacing=10),
                ft.Row([dt_contact_email, dt_contact_phone], spacing=10),

                build_section_header("6. Dispatch Allocation", color_token=FieldFlowLightTheme.PRIMARY_GREEN),
                ft.Row([dt_tech_select, dt_date_select], spacing=8),
                ft.Row([dt_status_select])
            ], spacing=10, scroll=ft.ScrollMode.ALWAYS),
            width=760, height=580, padding=ft.padding.only(left=12, right=20, top=10, bottom=10)
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: [setattr(ticket_detail_modal_dialog, 'open', False), page.update()]),
            ft.ElevatedButton("Save Ticket Details", icon=ft.icons.SAVE, style=FieldFlowLightTheme.get_primary_button_style(), on_click=save_ticket_detail_edits)
        ]
    )

    return ticket_detail_modal_dialog, populate_ticket_data