"""
src/frontend/admin_dashboard.py
Control Tower Admin Dashboard integrating side-by-side cockpit, Projects Registry,
User Management, Master Catalog, and Audit Trail tabs with full FieldFlowLightTheme styling.
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import flet as ft
import json
import time
import threading
from datetime import datetime, timedelta
from google.cloud.firestore_v1.base_query import FieldFilter

# Backend Module Imports
from src.backend.lifecycle_rules import validate_user_role_permission, validate_project_space_exists
from src.backend.search_engine import search_admin_portal
from src.frontend.theme import FieldFlowLightTheme
from src.backend.db_manager import db, local_db
from src.backend.calendar_listener import GoogleCalendarListener
from src.backend.drive_service import (
    process_new_service_request_submittal,
    create_project_drive_folder,
    list_files_in_drive_folder,
    ensure_project_drive_folder
)

# Consolidated Frontend Module Imports
from src.frontend.shared_utils import show_toast, open_drive_link
from src.frontend.cards_component import (
    build_standard_ticket_card,
    build_truncating_text,
    build_clickable_email_link,
    build_project_card,
    build_user_card
)
from src.frontend.details_component import (
    build_ticket_detail_modal,
    build_project_detail_modal
)
from src.frontend.forms_component import (
    build_service_intake_form,
    build_project_creation_form,
    build_master_forms as build_master_data_management_view
)
from src.frontend.calendar_component import build_calendar_widget


# =========================================================================
# --- MAIN APPLICATION DASHBOARD ---
# =========================================================================
def main(page: ft.Page):
    page.title = "FieldFlow Admin Control Tower"
    page.window_maximized = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = FieldFlowLightTheme.BG_LIGHT
    TITLE_FONT_SIZE = 18

    # Start background Google Calendar synchronization listener
    calendar_listener = GoogleCalendarListener(interval_seconds=10)
    calendar_listener.start_monitoring()

    def on_page_disconnect(e):
        calendar_listener.stop_monitoring()

    page.on_disconnect = on_page_disconnect

    def show_toast_local(message: str, kind: str = "success"):
        show_toast(page, message, kind)

    def open_drive_local(e, folder_id):
        open_drive_link(page, folder_id, show_toast_local)

    active_date_target = {"control": None}

    def on_global_date_selected(e):
        if global_date_picker.value and active_date_target["control"]:
            active_date_target["control"].value = global_date_picker.value.strftime("%Y-%m-%d")
            active_date_target["control"].update()

    global_date_picker = ft.DatePicker(
        first_date=datetime(2026, 1, 1),
        last_date=datetime(2030, 12, 31),
        on_change=on_global_date_selected
    )
    page.overlay.append(global_date_picker)

    def trigger_date_picker(target_control):
        active_date_target["control"] = target_control
        global_date_picker.pick_date()

    projects_view_filter = {"is_grid": True}

    # =========================================================================
    # --- DYNAMIC DROPDOWN OPTION HELPERS ---
    # =========================================================================
    def get_tech_options():
        options = []
        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_email, first_name, last_name, role 
                    FROM users 
                    WHERE role IN ('Technician', 'Admin') AND active_status = 'Active'
                """)
                for row in cursor.fetchall():
                    full_name = f"{row['first_name']} {row['last_name']}".strip() or row['user_email']
                    options.append(ft.dropdown.Option(row["user_email"], f"{full_name} ({row['user_email']})"))
        except Exception as err:
            print(f"Error fetching technicians: {err}")

        if not options:
            options = [
                ft.dropdown.Option("tech1@tbcotampaservice.com", "Bob Tech (tech1@tbcotampaservice.com)"),
                ft.dropdown.Option("tech2@tbcotampaservice.com", "Alex Tech (tech2@tbcotampaservice.com)"),
                ft.dropdown.Option("admin@tombarrow.com", "Alice Admin (admin@tombarrow.com)")
            ]
        return options

    def get_contractor_options():
        options = []
        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT tbco_account_number, company_name FROM contractors ORDER BY company_name ASC")
                for row in cursor.fetchall():
                    account_num = row["tbco_account_number"]
                    comp_name = row["company_name"] or "Unknown Contractor"
                    options.append(ft.dropdown.Option(key=str(account_num), text=f"{comp_name} (Acct #{account_num})"))
        except Exception as err:
            print(f"Error fetching contractors: {err}")
        return options

    def get_location_options():
        options = []
        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT site_name, street_address_1 FROM locations ORDER BY site_name ASC")
                for row in cursor.fetchall():
                    s_name = row["site_name"]
                    s_addr = row["street_address_1"] or ""
                    options.append(ft.dropdown.Option(key=s_name, text=f"{s_name} - {s_addr}".strip(" -")))
        except Exception as err:
            print(f"Error fetching locations: {err}")
        return options

    def get_salesperson_options():
        options = []
        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_email, first_name, last_name FROM users WHERE role IN ('Sales', 'Admin') AND active_status = 'Active'")
                for row in cursor.fetchall():
                    full_name = f"{row['first_name']} {row['last_name']}".strip() or row['user_email']
                    options.append(ft.dropdown.Option(key=row["user_email"], text=f"{full_name} ({row['user_email']})"))
        except Exception as err:
            print(f"Error fetching sales reps: {err}")
        return options

    # =========================================================================
    # --- TRIAGE INBOX UI CONTAINER DECLARATION ---
    # =========================================================================
    triage_cards_container = ft.Column(spacing=10, scroll=ft.ScrollMode.ALWAYS, expand=True)

    # =========================================================================
    # --- LIVE TRIAGE INBOX FEED LOADER ---
    # =========================================================================
    def load_live_triage_feed():
        triage_cards_container.controls.clear()
        pending_records = []

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM intake_requests
                    WHERE triage_status IN ('Unassigned', 'PENDING_TRIAGE', 'Pending')
                    ORDER BY submission_timestamp DESC
                """)
                for row in cursor.fetchall():
                    r_dict = dict(row)
                    r_dict["drive_id"] = f"FLD-GDRV-{r_dict.get('tbc_job_number') or 'NEW'}"
                    pending_records.append(r_dict)
        except Exception as err:
            print(f"Local triage query note: {err}")

        if not pending_records and db is not None:
            try:
                query = db.collection("intake_ledger").where(filter=FieldFilter("triage_status", "in", ["Unassigned", "PENDING_TRIAGE"])).stream()
                for doc in query:
                    record = doc.to_dict()
                    record["request_id"] = doc.id
                    job_num = record.get("tbc_job_number")
                    if not record.get("drive_id"):
                        record["drive_id"] = f"FLD-GDRV-{job_num or 'NEW'}"
                    pending_records.append(record)
            except Exception as err:
                print(f"Firebase triage fetch error: {err}")

        if not pending_records:
            triage_cards_container.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, color=FieldFlowLightTheme.PRIMARY_GREEN, size=20), 
                        ft.Text("Inbox Clear! All tickets assigned.", size=13, color=FieldFlowLightTheme.PRIMARY_GREEN)
                    ]),
                    bgcolor=FieldFlowLightTheme.BG_GREEN_TINT, padding=12, border_radius=6, border=ft.border.all(1, FieldFlowLightTheme.PRIMARY_GREEN)
                )
            )
            page.update()
            return

        for record in pending_records:
            drive_id = record.get("drive_id") or f"FLD-GDRV-{record.get('tbc_job_number', 'NEW')}"

            card_tech_dropdown = ft.Dropdown(
                label="Assign Technician*",
                hint_text="-- Choose Tech --",
                options=get_tech_options(),
                border_color=FieldFlowLightTheme.BORDER_PINK_EDGE,
                text_size=12,
                dense=True,
                expand=False
            )

            card_date_input = ft.TextField(
                label="Scheduled Date",
                value=datetime.now().strftime("%Y-%m-%d"),
                border_color=FieldFlowLightTheme.BORDER_PINK_EDGE,
                text_size=12,
                dense=True,
                expand=True
            )

            card_date_btn = ft.IconButton(
                icon=ft.icons.CALENDAR_MONTH,
                icon_color=FieldFlowLightTheme.PINK_PRIMARY,
                tooltip="Pick Date",
                on_click=lambda e, tf=card_date_input: trigger_date_picker(tf)
            )

            card = build_standard_ticket_card(
                record_data=record,
                card_context="triage",
                card_tech_dropdown=card_tech_dropdown,
                card_date_input=card_date_input,
                card_date_btn=card_date_btn,
                on_primary_action=lambda e, r=record, td=card_tech_dropdown, di=card_date_input: dispatch_from_triage_card(r, td, di),
                on_details_action=lambda e, r=record: open_service_ticket_detail(r),
                on_drive_action=lambda e, dr=drive_id: open_drive_local(e, dr),
                page=page
            )
            triage_cards_container.controls.append(card)
        page.update()

    # =========================================================================
    # --- MODALS INTEGRATION ---
    # =========================================================================
    intake_form_widget = build_service_intake_form(
        page,
        on_success_callback=lambda payload: [
            setattr(intake_modal, 'open', False),
            load_live_triage_feed(),
            refresh_calendar_fn(),
            execute_live_search(None)
        ]
    )

    intake_modal = ft.AlertDialog(
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        title=ft.Row([
            ft.Icon(ft.icons.POST_ADD, color=FieldFlowLightTheme.PINK_PRIMARY, size=26), 
            ft.Text("New Service Request Intake", size=18, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY)
        ]),
        content=ft.Container(content=intake_form_widget, width=760, height=540, padding=0),
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: [setattr(intake_modal, 'open', False), page.update()]),
            ft.ElevatedButton("Create Service Request", style=FieldFlowLightTheme.get_primary_button_style(), on_click=lambda e: intake_form_widget.submit_form(e) if hasattr(intake_form_widget, 'submit_form') else None)
        ]
    )
    page.overlay.append(intake_modal)

    def open_service_request_for_project(proj_record):
        job_num = proj_record.get("tbc_job_number", "") if isinstance(proj_record, dict) else (proj_record[0] if proj_record else "")

        is_valid_proj, proj_msg = validate_project_space_exists(job_num)
        if not is_valid_proj:
            show_toast_local(proj_msg, kind="error")
            return

        if hasattr(intake_form_widget, "populate_data"):
            intake_form_widget.populate_data(proj_record)

        intake_modal.open = True
        show_toast_local(f"📋 Initiating Service Request for Job #{job_num}", kind="info")
        page.update()

    project_form_widget = build_project_creation_form(
        page,
        on_success_callback=lambda payload: [
            setattr(direct_project_modal, 'open', False),
            execute_live_search(None)
        ]
    )

    direct_project_modal = ft.AlertDialog(
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        title=ft.Row([
            ft.Icon(ft.icons.CREATE_NEW_FOLDER, color=FieldFlowLightTheme.PRIMARY_GREEN, size=26), 
            ft.Text("Create New Project Folder", size=18, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY)
        ]),
        content=ft.Container(content=project_form_widget, width=520, padding=10),
        actions=[ft.TextButton("Cancel", on_click=lambda _: [setattr(direct_project_modal, 'open', False), page.update()])]
    )
    page.overlay.append(direct_project_modal)

    ticket_detail_modal, populate_ticket_data = build_ticket_detail_modal(
        page=page, get_tech_options_fn=get_tech_options, trigger_date_picker_fn=trigger_date_picker,
        on_save_callback=lambda payload: [load_live_triage_feed(), refresh_calendar_fn(), execute_live_search(None)]
    )
    page.overlay.append(ticket_detail_modal)

    def open_service_ticket_detail(req_data):
        req_id = req_data.get("request_id")
        job_num = req_data.get("tbc_job_number")
        row, dispatch_row = None, None
        
        if db is not None:
            try:
                if req_id:
                    doc = db.collection("intake_ledger").document(req_id).get()
                    if doc.exists: row = doc.to_dict()
                if not row and job_num:
                    query = db.collection("intake_ledger").where("tbc_job_number", "==", job_num).limit(1).stream()
                    for d in query: row = d.to_dict()
            except Exception as err:
                print(f"Error loading ticket record: {err}")

        if row: req_data = row
        populate_ticket_data(req_data, dispatch_row)
        ticket_detail_modal.open = True
        page.update()

    project_detail_modal, populate_project_data = build_project_detail_modal(
        page=page, open_drive_link_fn=open_drive_local, show_toast_fn=show_toast_local,
        on_save_callback=lambda payload: execute_live_search(None)
    )
    page.overlay.append(project_detail_modal)

    def open_edit_project_dialog(proj_row):
        populate_project_data(
            proj_row,
            contractor_options=get_contractor_options(),
            location_options=get_location_options(),
            sales_options=get_salesperson_options()
        )
        project_detail_modal.open = True
        page.update()

    calendar_widget, refresh_calendar_fn = build_calendar_widget(page=page, on_ticket_select_callback=open_service_ticket_detail)

    def dispatch_from_triage_card(req_data, tech_dropdown, date_input):
        is_valid_role, role_msg = validate_user_role_permission("admin@tombarrow.com", "ADMIN_ACTION")
        if not is_valid_role:
            show_toast_local(role_msg, kind="error")
            return

        selected_tech = tech_dropdown.value
        scheduled_date = date_input.value.strip() if date_input.value else datetime.now().strftime("%Y-%m-%d")

        if not selected_tech:
            show_toast_local("Please select a technician from the dropdown!", kind="warning")
            return

        req_id = req_data.get("request_id") or "REQ-NEW"
        job_num = req_data.get("tbc_job_number") or "123456XX"
        job_type = req_data.get("request_type") or "VFD Startup"

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE intake_requests
                    SET triage_status = 'Dispatched', tbc_job_number = ?
                    WHERE request_id = ?
                """, (job_num, req_id))

                cursor.execute("""
                    INSERT OR REPLACE INTO dispatches (job_id, tbc_job_number, technician_email, scheduled_time, status, job_type)
                    VALUES (?, ?, ?, ?, 'Scheduled', ?)
                """, (f"JOB-{job_num}", job_num, selected_tech, scheduled_date, job_type))
                conn.commit()

            if db is not None:
                db.collection("intake_ledger").document(req_id).set({"triage_status": "Dispatched"}, merge=True)

            show_toast_local(f"🚀 Dispatched Job #{job_num} to {selected_tech}!", kind="success")
            load_live_triage_feed()
            refresh_calendar_fn()
            execute_live_search(None)
            refresh_audit_trail_table()
        except Exception as err:
            show_toast_local(f"Dispatch Error: {err}", kind="error")

    # =========================================================================
    # --- COCKPIT PANEL ASSEMBLY ---
    # =========================================================================
    left_triage_panel = ft.Container(
        content=ft.Column([
            ft.Text("1. TRIAGE INBOX", size=TITLE_FONT_SIZE, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.PINK_PRIMARY),
            triage_cards_container
        ], expand=True, spacing=12),
        width=380,
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        padding=16,
        border_radius=10,
        border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
        shadow=FieldFlowLightTheme.get_card_shadow()
    )

    right_calendar_panel = ft.Container(
        content=ft.Column([
            ft.Text("2. DISPATCH & CALENDAR SCHEDULER", size=TITLE_FONT_SIZE, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.PRIMARY_GREEN),
            calendar_widget
        ], expand=True, spacing=12),
        expand=True,
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        padding=16,
        border_radius=10,
        border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
        shadow=FieldFlowLightTheme.get_card_shadow()
    )

    side_by_side_cockpit = ft.Row(
        controls=[left_triage_panel, right_calendar_panel],
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        expand=True
    )

    # =========================================================================
    # --- SEARCH ENGINE & PROJECTS MANIFEST ---
    # =========================================================================
    projects_list_container = ft.Row(wrap=True, spacing=12)

    def toggle_grid_list_view_mode(e):
        projects_view_filter["is_grid"] = not projects_view_filter["is_grid"]
        if projects_view_filter["is_grid"]:
            view_mode_button.icon = ft.icons.VIEW_LIST
            view_mode_button.tooltip = "Switch to Compact List View"
        else:
            view_mode_button.icon = ft.icons.VIEW_MODULE
            view_mode_button.tooltip = "Switch to Grid View"
        execute_live_search(None)

    view_mode_button = ft.IconButton(
        icon=ft.icons.VIEW_LIST,
        icon_color=FieldFlowLightTheme.PINK_PRIMARY,
        tooltip="Switch to Compact List View",
        on_click=toggle_grid_list_view_mode
    )

    search_input = ft.TextField(
        label="Search Client Footprints...",
        prefix_icon=ft.icons.SEARCH,
        border_color=FieldFlowLightTheme.BORDER_PINK_EDGE,
        expand=True,
        on_submit=lambda e: execute_live_search(e)
    )

    def open_new_request_dialog(e=None):
        if hasattr(intake_form_widget, "clear_form"):
            intake_form_widget.clear_form()
        intake_modal.open = True
        page.update()

    new_request_button = ft.ElevatedButton(
        "+ New Service Request",
        icon=ft.icons.ADD,
        style=FieldFlowLightTheme.get_primary_button_style(),
        on_click=open_new_request_dialog
    )

    def open_new_project_dialog(e=None):
        if hasattr(project_form_widget, "clear_form"):
            project_form_widget.clear_form()
        direct_project_modal.open = True
        page.update()

    new_project_button = ft.ElevatedButton(
        "+ New Project",
        icon=ft.icons.CREATE_NEW_FOLDER,
        style=ft.ButtonStyle(bgcolor=FieldFlowLightTheme.PINK_PRIMARY, color="white"),
        on_click=open_new_project_dialog
    )

    top_search_bar = ft.Container(
        content=ft.Row([search_input, view_mode_button, new_request_button, new_project_button], spacing=12), 
        padding=12,
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        border_radius=8,
        border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
        shadow=FieldFlowLightTheme.get_card_shadow()
    )

    def execute_live_search(e):
        """Executes Cloud-First project search fetching photo_url for full image rendering."""
        search_query = search_input.value.strip().lower() if search_input and search_input.value else ""
        projects_list_container.controls.clear()
        is_grid_mode = projects_view_filter["is_grid"]

        db_rows = []

        if db is not None:
            try:
                projects_stream = db.collection("projects").stream()
                for doc in projects_stream:
                    p_dict = doc.to_dict()
                    p_dict["tbc_job_number"] = doc.id or p_dict.get("tbc_job_number")
                    
                    job_num = str(p_dict.get("tbc_job_number", "")).lower()
                    p_name = str(p_dict.get("project_name", "")).lower()
                    s_name = str(p_dict.get("site_name", "")).lower()
                    c_name = str(p_dict.get("contractor_company_name") or p_dict.get("contractor_name") or p_dict.get("company_name", "")).lower()

                    if not search_query or (search_query in job_num or search_query in p_name or search_query in s_name or search_query in c_name):
                        if not p_dict.get("drive_id"):
                            p_dict["drive_id"] = f"FLD-DRIVE-{p_dict.get('tbc_job_number')}"
                        p_dict["contractor_name"] = c_name or "Partner"
                        db_rows.append(p_dict)
            except Exception as cloud_err:
                print(f"Cloud project search offline/error: {cloud_err}")

        if not db_rows:
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT p.tbc_job_number, p.project_name, p.site_name, p.drive_id,
                               p.tbco_account_number, c.company_name
                        FROM projects p
                        LEFT JOIN contractors c ON p.tbco_account_number = c.tbco_account_number
                    """)
                    for row in cursor.fetchall():
                        r_dict = dict(row)
                        r_dict["contractor_name"] = r_dict.get("company_name") or "Partner"
                        if not r_dict.get("drive_id"):
                            r_dict["drive_id"] = f"FLD-DRIVE-{r_dict['tbc_job_number']}"

                        if not search_query:
                            db_rows.append(r_dict)
                        else:
                            job_num = str(r_dict.get("tbc_job_number", "")).lower()
                            p_name = str(r_dict.get("project_name", "")).lower()
                            s_name = str(r_dict.get("site_name", "")).lower()
                            c_name = str(r_dict.get("contractor_name", "")).lower()
                            if search_query in job_num or search_query in p_name or search_query in s_name or search_query in c_name:
                                db_rows.append(r_dict)
            except Exception as err:
                print(f"Projects local search query error: {err}")

        for row in db_rows:
            p_card = build_project_card(
                project_data=row,
                is_grid_mode=is_grid_mode,
                on_edit_action=lambda e, r=row: open_edit_project_dialog(r),
                on_drive_action=lambda e, d_id=row.get("drive_id", ""): open_drive_local(e, d_id),
                on_service_request_action=lambda e, r=row: open_service_request_for_project(r)
            )
            projects_list_container.controls.append(p_card)
        
        page.update()

    projects_view = ft.Container(
        content=ft.Column(
            [projects_list_container],
            scroll=ft.ScrollMode.ALWAYS,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        ),
        padding=16,
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        border_radius=8,
        border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
        shadow=FieldFlowLightTheme.get_card_shadow(),
        expand=True
    )

    # =========================================================================
    # --- USER ACCOUNT MANAGEMENT WIDGET (RESTORED) ---
    # =========================================================================
    user_email_input = ft.TextField(label="User Email*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    user_first_name_input = ft.TextField(label="First Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    user_last_name_input = ft.TextField(label="Last Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE, expand=True)
    user_role_dropdown = ft.Dropdown(
        label="Assigned Role*",
        options=[
            ft.dropdown.Option("Admin", "Admin"),
            ft.dropdown.Option("Technician", "Technician"),
            ft.dropdown.Option("Sales", "Sales")
        ],
        value="Sales",
        border_color=FieldFlowLightTheme.BORDER_PINK_EDGE,
        expand=True
    )

    users_list_container = ft.Row(wrap=True, spacing=12)

    edit_user_email_input = ft.TextField(label="User Email (Read Only)", disabled=True, border_color=FieldFlowLightTheme.BORDER_PINK_EDGE)
    edit_user_first_name_input = ft.TextField(label="First Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE)
    edit_user_last_name_input = ft.TextField(label="Last Name*", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE)
    edit_user_role_dropdown = ft.Dropdown(
        label="Assigned Role*",
        options=[
            ft.dropdown.Option("Admin", "Admin"),
            ft.dropdown.Option("Technician", "Technician"),
            ft.dropdown.Option("Sales", "Sales")
        ],
        border_color=FieldFlowLightTheme.BORDER_PINK_EDGE
    )
    edit_user_status_dropdown = ft.Dropdown(
        label="Account Status*",
        options=[
            ft.dropdown.Option("Active", "Active"),
            ft.dropdown.Option("Inactive", "Inactive"),
            ft.dropdown.Option("Archived", "Archived")
        ],
        border_color=FieldFlowLightTheme.BORDER_PINK_EDGE
    )

    target_delete_email = {"email": ""}

    def refresh_users_list(e=None):
        users_list_container.controls.clear()
        rows = []

        if db is not None:
            try:
                users_stream = db.collection("users").stream()
                for doc in users_stream:
                    u_data = doc.to_dict()
                    u_data["user_email"] = doc.id or u_data.get("user_email")
                    rows.append(u_data)
            except Exception as cloud_err:
                print(f"Cloud fetch users offline/error: {cloud_err}")

        if not rows:
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_email, first_name, last_name, role, active_status FROM users ORDER BY first_name ASC")
                    rows = [dict(r) for r in cursor.fetchall()]
            except Exception as err:
                print(f"Error fetching users: {err}")

        if not rows:
            users_list_container.controls.append(ft.Text("No user accounts found.", size=12, color=FieldFlowLightTheme.TEXT_MUTED))
        else:
            for r_dict in rows:
                card = build_user_card(user_data=r_dict, on_edit_action=lambda e, u=r_dict: open_edit_user_dialog(u))
                users_list_container.controls.append(card)

        if page: page.update()

    def save_user_account(e):
        email = user_email_input.value.strip().lower() if user_email_input.value else ""
        first_name = user_first_name_input.value.strip() if user_first_name_input.value else ""
        last_name = user_last_name_input.value.strip() if user_last_name_input.value else ""
        role = user_role_dropdown.value

        if not email or not first_name:
            show_toast_local("Email and First Name required.", kind="warning")
            return

        payload = {"user_email": email, "first_name": first_name, "last_name": last_name, "role": role, "active_status": "Active"}

        if db is not None:
            try: db.collection("users").document(email).set(payload, merge=True)
            except Exception as err: print(f"Cloud user creation note: {err}")

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_email, first_name, last_name, role, active_status)
                    VALUES (?, ?, ?, ?, 'Active')
                    ON CONFLICT(user_email) DO UPDATE SET first_name = excluded.first_name, last_name = excluded.last_name, role = excluded.role
                """, (email, first_name, last_name, role))
                conn.commit()
        except Exception as err: print(f"Local user cache note: {err}")

        show_toast_local(f"User '{first_name} {last_name}' saved!", kind="success")
        user_email_input.value, user_first_name_input.value, user_last_name_input.value = "", "", ""
        refresh_users_list()

    def save_edited_user_account(e):
        email = edit_user_email_input.value
        first_name = edit_user_first_name_input.value.strip() if edit_user_first_name_input.value else ""
        last_name = edit_user_last_name_input.value.strip() if edit_user_last_name_input.value else ""
        role = edit_user_role_dropdown.value
        status = edit_user_status_dropdown.value

        payload = {"first_name": first_name, "last_name": last_name, "role": role, "active_status": status}

        if db is not None:
            try: db.collection("users").document(email).set(payload, merge=True)
            except Exception as err: print(f"Cloud user update note: {err}")

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET first_name = ?, last_name = ?, role = ?, active_status = ? WHERE user_email = ?", (first_name, last_name, role, status, email))
                conn.commit()
        except Exception as err: print(f"Local user update note: {err}")

        edit_user_modal.open = False
        show_toast_local(f"User '{first_name}' updated!", kind="success")
        refresh_users_list()

    def archive_user_account(e):
        email = edit_user_email_input.value
        if db is not None:
            try: db.collection("users").document(email).set({"active_status": "Archived"}, merge=True)
            except Exception as err: print(f"Cloud archive note: {err}")

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET active_status = 'Archived' WHERE user_email = ?", (email,))
                conn.commit()
        except Exception as err: print(f"Local archive note: {err}")

        edit_user_modal.open = False
        show_toast_local(f"User '{email}' archived.", kind="info")
        refresh_users_list()

    def confirm_delete_user_account(e):
        email = target_delete_email["email"]
        if not email: return

        if db is not None:
            try: db.collection("users").document(email).delete()
            except Exception as err: print(f"Cloud delete note: {err}")

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE user_email = ?", (email,))
                conn.commit()
        except Exception as err: print(f"Local delete note: {err}")

        confirm_delete_modal.open = False
        edit_user_modal.open = False
        show_toast_local(f"User '{email}' deleted permanently.", kind="warning")
        refresh_users_list()

    confirm_delete_modal = ft.AlertDialog(
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        title=ft.Row([ft.Icon(ft.icons.WARNING_AMBER, color="red", size=24), ft.Text("Confirm Permanent Deletion", size=16, weight=ft.FontWeight.BOLD)]),
        content=ft.Text("Are you sure you want to permanently delete this user account?", size=13),
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: [setattr(confirm_delete_modal, 'open', False), page.update()]),
            ft.ElevatedButton("Yes, Delete User", style=ft.ButtonStyle(bgcolor="red", color="white"), on_click=confirm_delete_user_account)
        ]
    )
    page.overlay.append(confirm_delete_modal)

    edit_user_modal = ft.AlertDialog(
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        title=ft.Row([ft.Icon(ft.icons.EDIT, color=FieldFlowLightTheme.PINK_PRIMARY, size=24), ft.Text("Edit User Account", size=18, weight=ft.FontWeight.BOLD)]),
        content=ft.Container(
            content=ft.Column([edit_user_email_input, edit_user_first_name_input, edit_user_last_name_input, edit_user_role_dropdown, edit_user_status_dropdown], spacing=12, tight=True),
            width=420, padding=10
        ),
        actions=[
            ft.TextButton("Delete User", icon=ft.icons.DELETE, icon_color="red", on_click=lambda e: [setattr(target_delete_email, 'email', edit_user_email_input.value), setattr(confirm_delete_modal, 'open', True), page.update()]),
            ft.TextButton("Archive", icon=ft.icons.ARCHIVE, icon_color="amber", on_click=archive_user_account),
            ft.TextButton("Cancel", on_click=lambda _: [setattr(edit_user_modal, 'open', False), page.update()]),
            ft.ElevatedButton("Save Changes", style=FieldFlowLightTheme.get_primary_button_style(), on_click=save_edited_user_account)
        ]
    )
    page.overlay.append(edit_user_modal)

    def open_edit_user_dialog(user_row):
        edit_user_email_input.value = user_row.get("user_email", "")
        edit_user_first_name_input.value = user_row.get("first_name", "")
        edit_user_last_name_input.value = user_row.get("last_name", "")
        edit_user_role_dropdown.value = user_row.get("role", "Sales")
        edit_user_status_dropdown.value = user_row.get("active_status", "Active")
        edit_user_modal.open = True
        page.update()

    users_management_view = ft.Container(
        content=ft.Column([
            ft.Text("USER ACCOUNT GOVERNANCE", size=16, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.PINK_PRIMARY),
            ft.Row([user_email_input, user_first_name_input, user_last_name_input, user_role_dropdown], spacing=10),
            ft.ElevatedButton("Save / Update User", style=FieldFlowLightTheme.get_primary_button_style(), on_click=save_user_account),
            ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=10),
            ft.Text("REGISTERED SYSTEM USERS", size=14, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
            users_list_container
        ], spacing=12, scroll=ft.ScrollMode.ALWAYS, expand=True),
        padding=16, bgcolor=FieldFlowLightTheme.SURFACE_CARD, border_radius=8,
        border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE), shadow=FieldFlowLightTheme.get_card_shadow(), expand=True
    )

    # =========================================================================
    # --- AUDIT TRAIL VIEWER WIDGET (RESTORED) ---
    # =========================================================================
    audit_table_container = ft.Column(spacing=6)
    entity_filter_picker = ft.Dropdown(
        label="Filter Entity Type",
        options=[
            ft.dropdown.Option("ALL", "All Entities"),
            ft.dropdown.Option("PROJECT", "Projects"),
            ft.dropdown.Option("INTAKE", "Intake Requests"),
            ft.dropdown.Option("DISPATCH", "Dispatches"),
            ft.dropdown.Option("USER", "Users")
        ],
        value="ALL", border_color=FieldFlowLightTheme.BORDER_PINK_EDGE
    )

    def refresh_audit_trail_table(e=None):
        audit_table_container.controls.clear()
        selected_entity = entity_filter_picker.value

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                if selected_entity == "ALL":
                    cursor.execute("SELECT log_id, user_email, entity_type, entity_id, timestamp, old_value, new_value FROM audit_log ORDER BY timestamp DESC LIMIT 50")
                else:
                    cursor.execute("SELECT log_id, user_email, entity_type, entity_id, timestamp, old_value, new_value FROM audit_log WHERE entity_type = ? ORDER BY timestamp DESC LIMIT 50", (selected_entity,))
                
                rows = cursor.fetchall()
                if not rows:
                    audit_table_container.controls.append(ft.Text("No audit log records found.", size=12, color=FieldFlowLightTheme.TEXT_MUTED))
                else:
                    for r in rows:
                        audit_table_container.controls.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Text(f"[{r['timestamp'][:19]}]", size=11, color=FieldFlowLightTheme.TEXT_MUTED),
                                    ft.Text(f"{r['user_email'] or 'System'}", size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.PINK_PRIMARY),
                                    ft.Text(f"{r['entity_type']} #{r['entity_id']}", size=11, color=FieldFlowLightTheme.TEXT_PRIMARY),
                                    ft.Text(f"Value: {r['old_value']} -> {r['new_value']}", size=11, italic=True, color=FieldFlowLightTheme.PRIMARY_GREEN)
                                ], spacing=10),
                                padding=6, bgcolor=FieldFlowLightTheme.SURFACE_HOVER, border_radius=4
                            )
                        )
        except Exception as err:
            audit_table_container.controls.append(ft.Text(f"Error loading audit log: {err}", size=12, color=FieldFlowLightTheme.SUN_AMBER))

        page.update()

    entity_filter_picker.on_change = refresh_audit_trail_table

    audit_trail_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("SYSTEM AUDIT TRAIL VIEWER", size=16, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.PRIMARY_GREEN),
                entity_filter_picker
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            audit_table_container
        ], spacing=12, scroll=ft.ScrollMode.ALWAYS),
        padding=16, bgcolor=FieldFlowLightTheme.SURFACE_CARD, border_radius=8,
        border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE), shadow=FieldFlowLightTheme.get_card_shadow(), expand=True
    )

    # =========================================================================
    # --- MASTER CATALOG TAB WIDGET ---
    # =========================================================================
    master_catalog_view = build_master_data_management_view(
        page=page,
        get_tech_options_fn=get_tech_options,
        on_success_callback=lambda payload: execute_live_search(None)
    )

    # =========================================================================
    # --- TAB MANAGER ASSEMBLY (EXACT SPECIFIED TAB ORDER) ---
    # =========================================================================
    tab_manager = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Control Tower Cockpit", icon=ft.icons.DASHBOARD, content=side_by_side_cockpit),
            ft.Tab(text="Projects Registry", icon=ft.icons.ASSIGNMENT, content=projects_view),
            ft.Tab(text="User Management", icon=ft.icons.SUPERVISED_USER_CIRCLE, content=users_management_view),
            ft.Tab(text="Master Catalog", icon=ft.icons.SETTINGS, content=master_catalog_view),
            ft.Tab(text="Audit Trail", icon=ft.icons.RECEIPT_LONG, content=audit_trail_view),
        ],
        expand=True
    )

    page.add(ft.Column([top_search_bar, tab_manager], expand=True, spacing=8))
    
    # Initial Data Feed Load
    load_live_triage_feed()
    refresh_calendar_fn()
    execute_live_search(None)
    refresh_audit_trail_table()
    refresh_users_list()

    # =========================================================================
    # --- AUTOMATIC BACKGROUND REFRESH WORKER ---
    # =========================================================================
    def auto_refresh_worker():
        while True:
            time.sleep(5)
            try:
                load_live_triage_feed()
                refresh_calendar_fn()
            except Exception as err:
                print(f"Auto-refresh worker note: {err}")

    refresh_thread = threading.Thread(target=auto_refresh_worker, daemon=True)
    refresh_thread.start()


if __name__ == "__main__":
    assets_folder = os.path.join(CURRENT_DIR, "assets")
    ft.app(target=main, assets_dir=assets_folder)