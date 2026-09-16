"""
src/frontend/sidecar_portal.py
Technician Desktop Portal using normalized relational queries and canonical keys.
"""

import flet as ft
import os
import sys
import time
import json
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from google.cloud.firestore_v1.base_query import FieldFilter
from src.backend.db_manager import db, local_db
from src.backend.drive_service import upload_files_to_drive_folder
from src.frontend.theme import FieldFlowLightTheme

from src.frontend.cards_component import build_standard_ticket_card
from src.frontend.shared_utils import show_toast, open_drive_link


def init_portal_database():
    if db is None:
        return
    try:
        portals_ref = db.collection("manufacturer_portals")
        docs = list(portals_ref.limit(1).stream())
        if not docs:
            default_portals = [
                {"portal_id": 1, "name": "YASKAWA", "url": "https://www.yaskawa.com", "color": "#15803D"}
            ]
            for portal in default_portals:
                portals_ref.document(portal["name"]).set(portal)
    except Exception as e:
        print(f"Error initializing portal DB in Firestore: {e}")


def fetch_pending_tickets():
    tickets_map = {}

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.job_id, d.tbc_job_number, d.technician_email, d.sales_rep_email,
                       d.scheduled_time, d.status, d.job_type,
                       p.project_name, p.drive_id AS project_drive_id,
                       l.street_address_1 || ', ' || l.city || ', ' || l.state AS site_address,
                       c.company_name AS contractor_company_name,
                       a.model_number, a.serial_number, a.equipment_tag,
                       u.first_name AS sales_first_name, u.last_name AS sales_last_name,
                       i.project_site_contact_first_name, i.project_site_contact_last_name,
                       i.project_site_contact_phone,
                       ai.inspection_metrics
                FROM dispatches d
                LEFT JOIN projects p ON d.tbc_job_number = p.tbc_job_number
                LEFT JOIN locations l ON p.site_name = l.site_name
                LEFT JOIN contractors c ON p.tbco_account_number = c.tbco_account_number
                LEFT JOIN assets a ON p.tbc_job_number = a.tbc_job_number
                LEFT JOIN intake_requests i ON d.tbc_job_number = i.tbc_job_number
                LEFT JOIN users u ON i.sales_rep_email = u.user_email
                LEFT JOIN asset_inspections ai ON d.job_id = ai.job_id
                WHERE LOWER(TRIM(d.status)) = 'pending'
            """)
            rows = cursor.fetchall()
            for row in rows:
                r_dict = dict(row)
                j_id = str(r_dict.get("job_id"))

                if r_dict.get("project_drive_id"):
                    r_dict["drive_id"] = r_dict["project_drive_id"]

                vfd_data = {}
                if r_dict.get("inspection_metrics"):
                    try:
                        vfd_data = json.loads(r_dict["inspection_metrics"])
                    except Exception:
                        pass
                r_dict["vfd_data"] = vfd_data

                if j_id:
                    tickets_map[j_id] = r_dict
    except Exception as e:
        print(f"Error querying local pending tickets: {e}")

    if db is not None:
        try:
            dispatches_query = db.collection("dispatches").where(filter=FieldFilter("status", "==", "Pending")).stream()
            for doc in dispatches_query:
                ticket_data = doc.to_dict()
                job_id = str(doc.id)
                ticket_data["job_id"] = job_id
                tbc_num = str(ticket_data.get("tbc_job_number") or "")

                insp_query = db.collection("asset_inspections").where(filter=FieldFilter("job_id", "==", job_id)).limit(1).stream()
                vfd_data = {}
                for i_doc in insp_query:
                    i_data = i_doc.to_dict()
                    raw_metrics = i_data.get("inspection_metrics", {})
                    if isinstance(raw_metrics, str):
                        try:
                            vfd_data = json.loads(raw_metrics)
                        except Exception:
                            vfd_data = {}
                    elif isinstance(raw_metrics, dict):
                        vfd_data = raw_metrics
                ticket_data["vfd_data"] = vfd_data

                if tbc_num:
                    proj_doc = db.collection("projects").document(tbc_num).get()
                    if proj_doc.exists:
                        p_data = proj_doc.to_dict()
                        ticket_data["project_name"] = p_data.get("project_name")
                        ticket_data["contractor_company_name"] = p_data.get("contractor_company_name")
                        ticket_data["drive_id"] = p_data.get("drive_id")

                    asset_query = db.collection("assets").where(filter=FieldFilter("tbc_job_number", "==", tbc_num)).limit(1).stream()
                    for a_doc in asset_query:
                        a_data = a_doc.to_dict()
                        ticket_data["model_number"] = a_data.get("model_number")
                        ticket_data["serial_number"] = a_data.get("serial_number")
                        ticket_data["equipment_tag"] = a_data.get("equipment_tag")

                    intake_query = db.collection("intake_requests").where(filter=FieldFilter("tbc_job_number", "==", tbc_num)).limit(1).stream()
                    for i_doc in intake_query:
                        i_data = i_doc.to_dict()
                        ticket_data["project_site_contact_first_name"] = i_data.get("project_site_contact_first_name")
                        ticket_data["project_site_contact_last_name"] = i_data.get("project_site_contact_last_name")
                        ticket_data["project_site_contact_phone"] = i_data.get("project_site_contact_phone")
                        ticket_data["sales_rep_email"] = i_data.get("sales_rep_email")

                tickets_map[job_id] = ticket_data
        except Exception as e:
            print(f"Error querying cloud pending tickets: {e}")

    return list(tickets_map.values())


def mark_warranty_registration_complete(tbc_job_number: str, registration_file_name: str) -> bool:
    clean_job_num = str(tbc_job_number)

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET stage = 'Completed' WHERE tbc_job_number = ?", (clean_job_num,))
            cursor.execute("UPDATE dispatches SET status = 'Completed' WHERE tbc_job_number = ?", (clean_job_num,))
            conn.commit()
    except Exception as e:
        print(f"Error completing local warranty registration: {e}")

    if db is None:
        return True

    try:
        db.collection("projects").document(clean_job_num).set({"stage": "Completed"}, merge=True)
        disp_query = db.collection("dispatches").where(filter=FieldFilter("tbc_job_number", "==", clean_job_num)).stream()
        for doc in disp_query:
            doc.reference.update({"status": "Completed"})
        return True
    except Exception as e:
        print(f"Error completing cloud warranty registration: {e}")
        return False


def build_field_copy_card(
    label_title: str,
    raw_val: any,
    page: ft.Page,
    show_toast_fn,
    icon_name=ft.icons.COPY
) -> ft.Container:
    field_val = str(raw_val) if raw_val is not None and str(raw_val).strip() != "" else "N/A"
    
    def handle_copy_click(e):
        if field_val and field_val != "N/A":
            page.set_clipboard(field_val)
            show_toast_fn(f"📋 Copied {label_title}: '{field_val}'", kind="info")
        else:
            show_toast_fn(f"⚠️ {label_title} is empty.", kind="warning")

    return ft.Container(
        content=ft.Row([
            ft.Icon(icon_name, color=FieldFlowLightTheme.ACCENT_BLUE, size=18),
            ft.Column([
                ft.Text(label_title, size=11, color=FieldFlowLightTheme.TEXT_MUTED, weight=ft.FontWeight.W_500),
                ft.Text(
                    field_val, 
                    size=13, 
                    weight=ft.FontWeight.BOLD, 
                    color=FieldFlowLightTheme.TEXT_PRIMARY, 
                    font_family="monospace" if any(k in label_title for k in ["Number", "Job", "Voltage", "Amps", "Serial", "Model", "Tag"]) else "sans-serif",
                    no_wrap=False
                )
            ], spacing=1, expand=True),
            ft.ElevatedButton(
                "Copy 📋",
                style=FieldFlowLightTheme.get_secondary_button_style(),
                on_click=handle_copy_click
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=FieldFlowLightTheme.SURFACE_HOVER,
        padding=10,
        border_radius=6,
        border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE),
        expand=True
    )


def main(page: ft.Page):
    page.title = "FieldFlow - Technician Desktop Review Portal"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = FieldFlowLightTheme.BG_LIGHT
    page.window_maximized = True
    page.padding = 20

    init_portal_database()
    selected_ticket_state = {"ticket": None}

    def show_toast_local(message: str, kind: str = "success"):
        show_toast(page, message, kind)

    def on_registration_file_picked(e: ft.FilePickerResultEvent):
        if not e.files or not selected_ticket_state["ticket"]:
            return

        ticket = selected_ticket_state["ticket"]
        job_num = str(ticket.get("tbc_job_number", "UNKNOWN"))
        target_drive_id = str(ticket.get("drive_id") or f"FLD-DRIVE-{job_num}")

        for uploaded_file in e.files:
            file_name_upper = uploaded_file.name.upper()
            if "REGISTRATION" in file_name_upper or file_name_upper.endswith(".PDF"):
                file_path = getattr(uploaded_file, "path", None)
                if file_path and os.path.exists(file_path):
                    upload_files_to_drive_folder(target_drive_id, [file_path])

                success = mark_warranty_registration_complete(job_num, uploaded_file.name)
                if success:
                    show_toast_local(f"🎉 REGISTRATION PDF Uploaded to Drive & Ticket #{job_num} Completed!", kind="success")
                    selected_ticket_state["ticket"] = None
                    refresh_desktop_portal_view()
                else:
                    show_toast_local("Failed to update ticket status in database.", kind="error")
            else:
                show_toast_local("⚠️ File must be a REGISTRATION document (e.g. REGISTRATION_CONFIRM.PDF).", kind="warning")

    registration_file_picker = ft.FilePicker(on_result=on_registration_file_picked)
    page.overlay.append(registration_file_picker)

    left_tickets_column = ft.Column(spacing=10, scroll=ft.ScrollMode.ALWAYS)
    right_details_container = ft.Container(expand=True)

    def build_field_copy_desk(ticket):
        selected_ticket_state["ticket"] = ticket
        
        job_num = str(ticket.get("tbc_job_number") or "N/A")
        client = str(ticket.get("contractor_company_name") or "Valued Client")
        address = str(ticket.get("site_address") or "Address Unspecified")
        model = str(ticket.get("model_number") or "N/A")
        serial = str(ticket.get("serial_number") or "N/A")
        site_contact = f"{ticket.get('project_site_contact_first_name', '')} {ticket.get('project_site_contact_last_name', '')} ({ticket.get('project_site_contact_phone', 'N/A')})".strip()
        tech_email = str(ticket.get("technician_email") or "tech1@tbcotampaservice.com")
        sched_date = str(ticket.get("scheduled_time") or datetime.now().strftime("%Y-%m-%d"))

        vfd = ticket.get("vfd_data") or {}

        vitals_rows = [
            ft.Row([
                build_field_copy_card("Accounting Job Number", job_num, page, show_toast_local, ft.icons.NUMBERS),
                build_field_copy_card("Service / Startup Date", sched_date, page, show_toast_local, ft.icons.CALENDAR_MONTH)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("Asset Serial Number", serial, page, show_toast_local, ft.icons.QR_CODE),
                build_field_copy_card("Asset Model Number", model, page, show_toast_local, ft.icons.SETTINGS_SUGGEST)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("Contractor / Client Name", client, page, show_toast_local, ft.icons.BUSINESS),
                build_field_copy_card("Project Site Address", address, page, show_toast_local, ft.icons.LOCATION_ON)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("Site Contact Person", site_contact, page, show_toast_local, ft.icons.PERSON),
                build_field_copy_card("Technician Email", tech_email, page, show_toast_local, ft.icons.EMAIL)
            ], spacing=10),
        ]

        unit_motor_rows = [
            ft.Row([
                build_field_copy_card("Unit Type", vfd.get("unit_type"), page, show_toast_local, ft.icons.HVAC),
                build_field_copy_card("Unit Tag / Mark", vfd.get("unit_tag_mark"), page, show_toast_local, ft.icons.LABEL)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("Wiring Distance Motor-Drive (Ft)", vfd.get("wiring_distance_ft"), page, show_toast_local, ft.icons.STRAIGHTEN),
                build_field_copy_card("Is There a Reactor Present?", vfd.get("is_reactor_present"), page, show_toast_local, ft.icons.ELECTRIC_BOLT)
            ], spacing=10)
        ]

        drive_electrical_rows = [
            ft.Row([
                build_field_copy_card("Drive Tag", vfd.get("drive_tag"), page, show_toast_local, ft.icons.MEMORY),
                build_field_copy_card("L1 to L2 Voltage", vfd.get("l1_l2"), page, show_toast_local, ft.icons.FLASH_ON)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("L2 to L3 Voltage", vfd.get("l2_l3"), page, show_toast_local, ft.icons.FLASH_ON),
                build_field_copy_card("L3 to L1 Voltage", vfd.get("l3_l1"), page, show_toast_local, ft.icons.FLASH_ON)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("L1 to Gnd Voltage", vfd.get("l1_gnd"), page, show_toast_local, ft.icons.POWER),
                build_field_copy_card("L2 to Gnd Voltage", vfd.get("l2_gnd"), page, show_toast_local, ft.icons.POWER)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("L3 to Gnd Voltage", vfd.get("l3_gnd"), page, show_toast_local, ft.icons.POWER),
                build_field_copy_card("T1 to T2 Voltage", vfd.get("t1_t2"), page, show_toast_local, ft.icons.OFFLINE_BOLT)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("T2 to T3 Voltage", vfd.get("t2_t3"), page, show_toast_local, ft.icons.OFFLINE_BOLT),
                build_field_copy_card("T3 to T1 Voltage", vfd.get("t3_t1"), page, show_toast_local, ft.icons.OFFLINE_BOLT)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("T1 Output Amps", vfd.get("t1"), page, show_toast_local, ft.icons.SPEED),
                build_field_copy_card("T2 Output Amps", vfd.get("t2"), page, show_toast_local, ft.icons.SPEED)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("T3 Output Amps", vfd.get("t3"), page, show_toast_local, ft.icons.SPEED),
                build_field_copy_card("Verified Drive Params Programmed", vfd.get("verified_yaskawa_params"), page, show_toast_local, ft.icons.VERIFIED)
            ], spacing=10)
        ]

        software_notes_rows = [
            ft.Row([
                build_field_copy_card("Software Version (U1-14/U1-25)", vfd.get("software_version"), page, show_toast_local, ft.icons.TERMINAL),
                build_field_copy_card("Serial Comm Methods Used", vfd.get("serial_comm_method"), page, show_toast_local, ft.icons.SETTINGS_ETHERNET)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("Bypass Software Number (UB-18)", vfd.get("bypass_software_num"), page, show_toast_local, ft.icons.CODE),
                build_field_copy_card("Describe Type of Application", vfd.get("application_type"), page, show_toast_local, ft.icons.CATEGORY)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("Field Notes", vfd.get("field_notes"), page, show_toast_local, ft.icons.NOTES),
                build_field_copy_card("Status of Startup", vfd.get("status"), page, show_toast_local, ft.icons.TASK_ALT)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("Resolution, Next Steps", vfd.get("resolution_next_steps"), page, show_toast_local, ft.icons.NEXT_PLAN),
                build_field_copy_card("Travel Hours", vfd.get("travel_hours"), page, show_toast_local, ft.icons.SCHEDULE)
            ], spacing=10),
            ft.Row([
                build_field_copy_card("Work Hours", vfd.get("work_hours"), page, show_toast_local, ft.icons.TIMELAPSE)
            ], spacing=10)
        ]

        yaskawa_launch_btn = ft.ElevatedButton(
            "Launch Yaskawa Portal 🔗",
            icon=ft.icons.LAUNCH,
            style=FieldFlowLightTheme.get_primary_button_style(),
            on_click=lambda e: page.launch_url("https://www.yaskawa.com")
        )

        upload_doc_btn = ft.ElevatedButton(
            "Move REGISTRATION Doc Here 📄",
            icon=ft.icons.UPLOAD_FILE,
            style=FieldFlowLightTheme.get_primary_button_style(),
            on_click=lambda _: registration_file_picker.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["pdf"]
            )
        )

        quick_actions_bar = ft.Container(
            content=ft.Row([
                yaskawa_launch_btn,
                upload_doc_btn,
                ft.Text("Uploading PDF completes ticket and clears queue.", size=12, color=FieldFlowLightTheme.TEXT_MUTED)
            ], spacing=15, alignment=ft.MainAxisAlignment.START, wrap=True),
            bgcolor=FieldFlowLightTheme.SURFACE_HOVER, padding=14, border_radius=8, border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE)
        )

        status_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.PENDING_ACTIONS, color=FieldFlowLightTheme.SUN_AMBER, size=20),
                ft.Text(
                    "PENDING TICKET: Copy field data to Yaskawa portal, then upload REGISTRATION PDF to clear ticket.",
                    size=12, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.SUN_AMBER
                )
            ], spacing=8),
            bgcolor=FieldFlowLightTheme.BG_AMBER_TINT, padding=10, border_radius=6, border=ft.border.all(1, FieldFlowLightTheme.SUN_AMBER)
        )

        return ft.Container(
            content=ft.Column([
                status_banner,
                ft.Row([
                    ft.Text(f"MANUFACTURER REGISTRATION DESK — JOB #{job_num}", size=18, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
                    ft.Text("Status: PENDING", size=12, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.SUN_AMBER)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),

                ft.Text("Quick Actions", size=14, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.SUN_AMBER),
                quick_actions_bar,
                ft.Divider(height=10, color=FieldFlowLightTheme.BORDER_SUBTLE),

                ft.Text("General Project Vitals", size=14, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.SUN_AMBER),
                ft.Column(controls=vitals_rows, spacing=10),
                ft.Divider(height=10, color=FieldFlowLightTheme.BORDER_SUBTLE),

                ft.Text("Unit & Motor Identification", size=14, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.SUN_AMBER),
                ft.Column(controls=unit_motor_rows, spacing=10),
                ft.Divider(height=10, color=FieldFlowLightTheme.BORDER_SUBTLE),

                ft.Text("Drive & Electrical Measurements", size=14, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.SUN_AMBER),
                ft.Column(controls=drive_electrical_rows, spacing=10),
                ft.Divider(height=10, color=FieldFlowLightTheme.BORDER_SUBTLE),

                ft.Text("Software, Notes & Hours", size=14, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.SUN_AMBER),
                ft.Column(controls=software_notes_rows, spacing=10)
            ], spacing=12, scroll=ft.ScrollMode.ALWAYS),
            bgcolor=FieldFlowLightTheme.SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE), expand=True
        )

    def refresh_desktop_portal_view():
        left_tickets_column.controls.clear()
        tickets = fetch_pending_tickets()

        if not tickets:
            selected_ticket_state["ticket"] = None
            left_tickets_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.CHECK_CIRCLE, color=FieldFlowLightTheme.PRIMARY_GREEN, size=32),
                        ft.Text("Queue Clear! No pending tickets waiting for registration.", size=13, color=FieldFlowLightTheme.PRIMARY_GREEN, text_align=ft.TextAlign.CENTER)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                    bgcolor=FieldFlowLightTheme.BG_GREEN_TINT, padding=24, border_radius=8, border=ft.border.all(1, FieldFlowLightTheme.PRIMARY_GREEN)
                )
            )
            right_details_container.content = ft.Container(
                content=ft.Text("No pending tickets requiring action.", size=14, color=FieldFlowLightTheme.TEXT_MUTED),
                alignment=ft.alignment.center, expand=True
            )
            page.update()
            return

        ticket_ids = [str(t.get("job_id")) for t in tickets]
        if selected_ticket_state["ticket"] is None or str(selected_ticket_state["ticket"].get("job_id")) not in ticket_ids:
            selected_ticket_state["ticket"] = tickets[0]

        for index, ticket in enumerate(tickets):
            card = build_standard_ticket_card(
                record_data=ticket,
                card_context="sidecar",
                on_details_action=lambda e, t=ticket: select_ticket_for_desk(t),
                page=page
            )
            left_tickets_column.controls.append(card)

        if selected_ticket_state["ticket"]:
            right_details_container.content = build_field_copy_desk(selected_ticket_state["ticket"])

        page.update()

    def select_ticket_for_desk(ticket):
        right_details_container.content = build_field_copy_desk(ticket)
        page.update()

    left_panel = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.MONITOR, color=FieldFlowLightTheme.ACCENT_BLUE, size=22),
                ft.Text("PENDING QUEUE", size=15, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY)
            ]),
            ft.Text("Shows Pending Tickets Requiring Registration", size=11, color=FieldFlowLightTheme.TEXT_MUTED),
            ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),
            left_tickets_column
        ], spacing=10),
        width=380, bgcolor=FieldFlowLightTheme.SURFACE_CARD, padding=15, border_radius=10, border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE)
    )

    header_bar = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Text("FIELDFLOW TECHNICIAN DESKTOP PORTAL", size=18, weight=ft.FontWeight.BOLD, font_family="monospace", color=FieldFlowLightTheme.PRIMARY_GREEN),
                ft.Text("Manufacturer Warranty & Registration Review Desk", size=13, color=FieldFlowLightTheme.TEXT_MUTED)
            ], spacing=10),
            ft.IconButton(
                icon=ft.icons.REFRESH,
                icon_color=FieldFlowLightTheme.ACCENT_BLUE,
                tooltip="Refresh Pending Queue",
                on_click=lambda e: refresh_desktop_portal_view()
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=FieldFlowLightTheme.SURFACE_CARD, padding=12, border_radius=8, border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE)
    )

    page.add(
        ft.Column([
            header_bar,
            ft.Row([left_panel, right_details_container], expand=True, spacing=15)
        ], expand=True, spacing=12)
    )

    refresh_desktop_portal_view()