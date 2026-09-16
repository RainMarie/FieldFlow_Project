"""
src/frontend/mobile_suite.py
Mobile interface for technicians using normalized assets queries and joined sales details.
"""

import flet as ft
import threading
import time
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from google.cloud.firestore_v1.base_query import FieldFilter
from src.backend.db_manager import db, local_db, record_job_part_used
from src.frontend.theme import FieldFlowLightTheme

from src.frontend.shared_utils import show_toast, open_drive_link, open_navigation_map
from src.frontend.cards_component import build_standard_ticket_card, build_site_asset_card, build_visit_history_card
from src.frontend.vfd_form_component import build_vfd_service_form
from src.frontend.forms_component import build_asset_registration_tool
from src.frontend.technician_clock_component import build_technician_clock, update_dispatch_status


def update_project_asset_details(tbc_job_number: str, old_serial: str, new_name: str, new_serial: str, new_model: str) -> bool:
    clean_job_num = str(tbc_job_number or "").strip()
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE assets
                SET equipment_tag = ?, serial_number = ?, model_number = ?
                WHERE (tbc_job_number = ? OR site_name = ?) AND serial_number = ?
            """, (str(new_name), str(new_serial), str(new_model), clean_job_num, clean_job_num, str(old_serial)))
            conn.commit()
    except Exception as e:
        print(f"Error updating local asset details: {e}")

    if db is None:
        return False
    try:
        query = db.collection("assets").where(filter=FieldFilter("tbc_job_number", "==", clean_job_num)).stream()
        for doc in query:
            data = doc.to_dict()
            if str(data.get("serial_number")) == str(old_serial):
                doc.reference.update({
                    "equipment_tag": str(new_name),
                    "serial_number": str(new_serial),
                    "model_number": str(new_model)
                })
        return True
    except Exception as e:
        print(f"Error updating cloud asset details: {e}")
        return False


def log_part_usage_submission(job_id: str, sku: str, qty: float, is_unlisted: bool, description: str, cost: float) -> str:
    actual_sku = None if is_unlisted else sku
    return record_job_part_used(
        job_id=job_id,
        sku=actual_sku,
        qty_used=qty,
        is_unlisted=is_unlisted,
        unlisted_description=description,
        manual_cost=cost
    )


def main(page: ft.Page):
    page.title = "FieldFlow Mobile Suite"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = FieldFlowLightTheme.BG_LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    bottom_sheet = ft.BottomSheet(open=False)
    page.bottom_sheet = bottom_sheet

    tech_identity = {"email": "tech1@tbcotampaservice.com"}
    active_job_context = {}
    serviced_assets_cache = {}

    def show_toast_local(message: str, kind: str = "success"):
        show_toast(page, message, kind)

    def open_drive_local(folder_id: str):
        open_drive_link(page, folder_id, show_toast_local)

    def open_map_local(address: str):
        open_navigation_map(page, address)

    def render_viewport(content_item):
        mobile_chassis_frame = ft.Container(
            content=content_item,
            alignment=ft.alignment.top_center,
            width=430
        )
        page.controls.clear()
        page.add(mobile_chassis_frame)
        page.update()

    def load_service_form_view(asset_data, job_data):
        page.floating_action_button = None
        job_id = str(job_data.get("job_id", "JOB-UNKNOWN"))
        job_type = str(job_data.get("job_type", "VFD_STARTUP")).upper()
        is_vfd = "VFD" in job_type

        def handle_service_form_submit(asset_serial, target_status, metrics_payload):
            update_dispatch_status(job_id, target_status)
            serviced_assets_cache[str(asset_serial)] = {"status": "Serviced", "metrics": metrics_payload}
            job_data["status"] = target_status

            if is_vfd:
                show_toast_local("📌 Report Saved! Held as PENDING for Sidecar Portal.", kind="warning")
            else:
                show_toast_local("🎉 Saved Inspection Report!", kind="success")

            load_job_briefing_view(job_data)

        form_component = build_vfd_service_form(
            asset_data=asset_data,
            job_data=job_data,
            on_submit_callback=handle_service_form_submit,
            on_back_callback=lambda e: load_asset_info_detail_view(asset_data, job_data),
            show_toast_fn=show_toast_local
        )

        render_viewport(form_component)

    def load_asset_info_detail_view(asset_data, job_data):
        page.floating_action_button = None
        tbc_job_num = str(job_data.get("tbc_job_number", "889900XX"))
        asset_id = str(asset_data.get("asset_id") or "")
        
        asset_name = str(asset_data.get("equipment_tag") or asset_data.get("asset_name", "Site Equipment"))
        asset_model = str(asset_data.get("model_number", "N/A"))
        asset_serial = str(asset_data.get("serial_number", "N/A"))
        installed_date = str(asset_data.get("installation_date", "Recently Installed"))

        is_serviced = serviced_assets_cache.get(asset_serial, {}).get("status") == "Serviced"

        inspection_history = []
        if asset_id:
            try:
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ai.report_id, ai.job_id, ai.registration_status, ai.inspection_metrics,
                               d.scheduled_time, d.technician_email, d.job_type
                        FROM asset_inspections ai
                        JOIN dispatches d ON ai.job_id = d.job_id
                        WHERE ai.asset_id = ?
                        ORDER BY d.scheduled_time DESC
                    """, (asset_id,))
                    inspection_history = [dict(r) for r in cursor.fetchall()]
            except Exception as err:
                print(f"Inspection history lookup note: {err}")

        tag_photo_preview = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.IMAGE, color=FieldFlowLightTheme.ACCENT_BLUE, size=36),
                ft.Text("Data Plate Photo Verified on File 📷", size=12, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
                ft.Text(f"Tag ID: {asset_serial}", size=10, color=FieldFlowLightTheme.TEXT_MUTED)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            bgcolor=FieldFlowLightTheme.SURFACE_HOVER,
            height=120,
            border_radius=8,
            border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE),
            alignment=ft.alignment.center
        )

        def open_edit_asset_modal(e):
            edit_name_field = ft.TextField(label="Equipment Name / Tag", value=asset_name, border_color=FieldFlowLightTheme.ACCENT_BLUE)
            edit_serial_field = ft.TextField(label="Serial Number", value=asset_serial, border_color=FieldFlowLightTheme.ACCENT_BLUE)
            edit_model_field = ft.TextField(label="Model Number", value=asset_model, border_color=FieldFlowLightTheme.ACCENT_BLUE)

            def save_asset_edits(ev):
                new_n = edit_name_field.value.strip()
                new_s = edit_serial_field.value.strip().upper()
                new_m = edit_model_field.value.strip()
                
                if not new_s or not new_n:
                    show_toast_local("Serial and Name are required!", kind="error")
                    return

                success = update_project_asset_details(tbc_job_num, asset_serial, new_n, new_s, new_m)
                bottom_sheet.open = False
                
                if success:
                    show_toast_local(f"✅ Updated details for '{new_n}'!", kind="success")
                    asset_data.update({"equipment_tag": new_n, "serial_number": new_s, "model_number": new_m})
                    load_asset_info_detail_view(asset_data, job_data)
                else:
                    show_toast_local("Failed to update asset details in database.", kind="error")

            bottom_sheet.content = ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(ft.icons.EDIT, color=FieldFlowLightTheme.ACCENT_BLUE), ft.Text("Edit Asset Details", size=16, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY)]),
                    ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),
                    edit_name_field, edit_serial_field, edit_model_field,
                    ft.ElevatedButton("Save Changes", style=FieldFlowLightTheme.get_primary_button_style(), on_click=save_asset_edits)
                ], spacing=10, tight=True),
                bgcolor=FieldFlowLightTheme.SURFACE_CARD, padding=20, border_radius=ft.border_radius.only(top_left=14, top_right=14)
            )
            bottom_sheet.open = True
            page.update()

        badge_bg, badge_color = FieldFlowLightTheme.resolve_status_badge_colors("Completed" if is_serviced else "Unassigned")

        history_controls = []
        if not inspection_history:
            history_controls.append(ft.Text("No prior inspection reports on record.", size=11, italic=True, color=FieldFlowLightTheme.TEXT_MUTED))
        else:
            for item in inspection_history:
                history_controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Date: {item.get('scheduled_time', 'N/A')} | Tech: {item.get('technician_email', 'Tech')}", size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
                            ft.Text(f"Status: {item.get('registration_status', 'Complete')}", size=11, color=FieldFlowLightTheme.PRIMARY_GREEN)
                        ], spacing=2),
                        bgcolor=FieldFlowLightTheme.SURFACE_HOVER, padding=8, border_radius=4
                    )
                )

        asset_detail_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"⚙️ {asset_name}", size=18, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
                    ft.Container(
                        content=ft.Text("SERVICED ✅" if is_serviced else "PENDING", size=10, weight=ft.FontWeight.BOLD, color=badge_color),
                        bgcolor=badge_bg,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=4
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),
                ft.Text(f"Model Number: {asset_model}", size=13, color=FieldFlowLightTheme.TEXT_MUTED),
                ft.Text(f"Serial Number: {asset_serial}", size=13, font_family="monospace", color=FieldFlowLightTheme.ACCENT_BLUE, weight=ft.FontWeight.BOLD),
                ft.Text(f"Installation Date: {installed_date}", size=12, color=FieldFlowLightTheme.TEXT_MUTED),
                
                ft.Divider(height=8, color=FieldFlowLightTheme.BORDER_SUBTLE),
                tag_photo_preview,
                
                ft.Divider(height=8, color=FieldFlowLightTheme.BORDER_SUBTLE),
                ft.Text("Historical Asset Inspections Across Dispatches", size=12, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
                ft.Column(controls=history_controls, spacing=4),

                ft.Divider(height=12, color=FieldFlowLightTheme.BORDER_SUBTLE),
                ft.Row([
                    ft.OutlinedButton(
                        "Edit Details ✏️",
                        style=FieldFlowLightTheme.get_secondary_button_style(),
                        on_click=open_edit_asset_modal
                    ),
                    ft.ElevatedButton(
                        "Service Asset ⚙️",
                        style=FieldFlowLightTheme.get_primary_button_style(),
                        on_click=lambda e: load_service_form_view(asset_data, job_data)
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            ], spacing=8),
            bgcolor=FieldFlowLightTheme.SURFACE_CARD,
            padding=16,
            border_radius=12,
            border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE)
        )

        detail_layout = ft.Column([
            ft.Row([
                ft.TextButton("<- Back to Dispatch Briefing", style=FieldFlowLightTheme.get_secondary_button_style(), on_click=lambda e: load_job_briefing_view(job_data))
            ]),
            ft.Text("Asset Vitals & Service Link", size=22, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
            ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),
            asset_detail_card
        ], spacing=12, scroll=ft.ScrollMode.ALWAYS)

        render_viewport(detail_layout)

    def load_search_first_asset_view(job_data):
        page.floating_action_button = None
        nonlocal active_job_context
        active_job_context = job_data

        asset_tool_component = build_asset_registration_tool(
            job_data=job_data,
            on_proceed_callback=lambda e: load_job_briefing_view(job_data),
            on_back_callback=lambda e: load_job_briefing_view(job_data),
            show_toast_fn=show_toast_local,
            page=page
        )

        render_viewport(asset_tool_component)

    def load_job_briefing_view(job_data):
        page.floating_action_button = None
        job_id = str(job_data.get("job_id", "JOB-5005"))
        tbc_job_num = str(job_data.get("tbc_job_number", "889900XX"))
        job_type = str(job_data.get("job_type", "VFD_STARTUP"))
        address = str(job_data.get('site_address', '100 Cyberdyne Way, Tampa, FL'))
        drive_id = str(job_data.get('drive_id') or f"FLD-DRIVE-{tbc_job_num}")

        sales_team_name = "Tampa HVAC Sales Team"
        sales_rep_contact = "sales1@tombarrow.com"
        site_contact_info = "Mike Smith (813-555-0199)"
        request_scope_info = str(job_data.get("issue_description") or "Annual Preventative Maintenance & Firmware Flash")

        project_assets_list = []
        previous_visits_list = []

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT asset_id, equipment_tag, model_number, serial_number, installation_date, operational_status
                    FROM assets
                    WHERE tbc_job_number = ? OR site_name = ?
                """, (tbc_job_num, tbc_job_num))
                project_assets_list = [dict(r) for r in cursor.fetchall()]

                cursor.execute("SELECT * FROM dispatches WHERE tbc_job_number = ? AND job_id != ?", (tbc_job_num, job_id))
                previous_visits_list = [dict(r) for r in cursor.fetchall()]

                cursor.execute("""
                    SELECT i.issue_description, i.sales_rep_email, (u.first_name || ' ' || u.last_name) AS sales_full_name
                    FROM intake_requests i
                    LEFT JOIN users u ON i.sales_rep_email = u.user_email
                    WHERE i.tbc_job_number = ? LIMIT 1
                """, (tbc_job_num,))
                i_row = cursor.fetchone()
                if i_row:
                    i_dict = dict(i_row)
                    if i_dict.get("sales_full_name") and i_dict["sales_full_name"].strip(): 
                        sales_team_name = str(i_dict["sales_full_name"])
                    if i_dict.get("sales_rep_email"): 
                        sales_rep_contact = str(i_dict["sales_rep_email"])
                    if i_dict.get("issue_description"): 
                        request_scope_info = str(i_dict["issue_description"])
        except Exception as err:
            print(f"Local briefing query note: {err}")

        if db is not None and not project_assets_list:
            try:
                disp_doc = db.collection("dispatches").document(job_id).get()
                if disp_doc.exists:
                    disp_data = disp_doc.to_dict()
                    job_data["status"] = str(disp_data.get("status", job_data.get("status")))
                    job_type = str(disp_data.get("job_type", job_type))

                assets_query = db.collection("assets").where(filter=FieldFilter("tbc_job_number", "==", tbc_job_num)).stream()
                project_assets_list = [a.to_dict() for a in assets_query]
            except Exception as err:
                print(f"Cloud briefing fetch note: {err}")

        clock_component = build_technician_clock(
            job_data=job_data,
            tech_email=tech_identity["email"],
            on_status_change_callback=lambda: load_job_briefing_view(job_data),
            show_toast_fn=show_toast_local
        )

        asset_cards_controls = []
        if not project_assets_list:
            asset_cards_controls.append(
                ft.Container(content=ft.Text("No equipment currently registered for this site.", size=12, color=FieldFlowLightTheme.TEXT_MUTED, italic=True), padding=6)
            )
        else:
            for asset in project_assets_list:
                a_serial = str(asset.get("serial_number", "N/A"))
                is_serviced = serviced_assets_cache.get(a_serial, {}).get("status") == "Serviced"

                asset_card = build_site_asset_card(
                    asset_data=asset,
                    is_serviced=is_serviced,
                    on_click_action=lambda e, a=asset: load_asset_info_detail_view(a, job_data)
                )
                asset_cards_controls.append(asset_card)

        visit_cards_controls = []
        if not previous_visits_list:
            visit_cards_controls.append(
                ft.Container(content=ft.Text("No previous service visits recorded for this project.", size=12, color=FieldFlowLightTheme.TEXT_MUTED, italic=True), padding=6)
            )
        else:
            for visit in previous_visits_list:
                def open_visit_detail_modal(e, v=visit):
                    bottom_sheet.content = ft.Container(
                        content=ft.Column([
                            ft.Row([ft.Icon(ft.icons.HISTORY, color=FieldFlowLightTheme.ACCENT_BLUE), ft.Text(f"Visit Detail: {v.get('scheduled_time')}", size=16, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY)]),
                            ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),
                            ft.Text(f"Technician: {v.get('technician_email')}", size=13, color=FieldFlowLightTheme.TEXT_PRIMARY),
                            ft.Text(f"Service Type: {v.get('job_type')}", size=13, color=FieldFlowLightTheme.ACCENT_BLUE),
                            ft.Text(f"Status: {v.get('status')}", size=13, color=FieldFlowLightTheme.PRIMARY_GREEN),
                            ft.Text(f"Metrics / Notes: {v.get('report_metrics') or 'Standard Service Completed'}", size=12, italic=True, color=FieldFlowLightTheme.TEXT_MUTED),
                            ft.ElevatedButton("Close", on_click=lambda _: [setattr(bottom_sheet, 'open', False), page.update()])
                        ], spacing=10, tight=True),
                        bgcolor=FieldFlowLightTheme.SURFACE_CARD, padding=20, border_radius=ft.border_radius.only(top_left=14, top_right=14)
                    )
                    bottom_sheet.open = True
                    page.update()

                visit_card = build_visit_history_card(
                    visit_data=visit,
                    on_click_action=open_visit_detail_modal
                )
                visit_cards_controls.append(visit_card)

        master_briefing_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"JOB #: {tbc_job_num}", font_family="monospace", color=FieldFlowLightTheme.ACCENT_BLUE, weight=ft.FontWeight.BOLD, size=13),
                    clock_component
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Text(str(job_data.get("contractor_company_name", "Tampa Chiller Services Inc")), size=18, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
                ft.Text(f"📍 Address: {address}", size=12, color=FieldFlowLightTheme.TEXT_MUTED),
                ft.Text(f"👤 Site Contact: {site_contact_info}", size=12, color=FieldFlowLightTheme.TEXT_MUTED),
                ft.Text(f"💼 Sales Rep: {sales_team_name} ({sales_rep_contact})", size=12, color=FieldFlowLightTheme.ACCENT_BLUE, weight=ft.FontWeight.W_500),
                ft.Text(f"🔧 Request Scope: {request_scope_info}", size=12, italic=True, color=FieldFlowLightTheme.ACCENT_BLUE),
                
                ft.Row([
                    ft.OutlinedButton("Nav Map", icon=ft.icons.MAP, style=FieldFlowLightTheme.get_secondary_button_style(), on_click=lambda e: open_map_local(address)),
                    ft.OutlinedButton("Drive Folder", icon=ft.icons.FOLDER, style=FieldFlowLightTheme.get_secondary_button_style(), on_click=lambda e: open_drive_local(drive_id)),
                    ft.ElevatedButton(
                        "➕ Add / Search Asset Tool", 
                        style=FieldFlowLightTheme.get_primary_button_style(), 
                        on_click=lambda e: load_search_first_asset_view(job_data)
                    )
                ], spacing=6, wrap=True),

                ft.Divider(height=12, color=FieldFlowLightTheme.BORDER_SUBTLE),

                ft.Text("Project Assets (Selectable)", size=14, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
                ft.Column(controls=asset_cards_controls, spacing=6),

                ft.Divider(height=12, color=FieldFlowLightTheme.BORDER_SUBTLE),

                ft.Text("Previous Visit History (Selectable)", size=14, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.SUN_AMBER),
                ft.Column(controls=visit_cards_controls, spacing=6)

            ], spacing=8),
            bgcolor=FieldFlowLightTheme.SURFACE_CARD,
            padding=16,
            border_radius=12,
            border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE)
        )

        briefing_layout = ft.Column([
            ft.Row([
                ft.TextButton("<- Back to Assigned Feed", style=FieldFlowLightTheme.get_secondary_button_style(), on_click=lambda e: load_chronological_feed_view())
            ]),
            ft.Text("Dispatch Briefing", size=22, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
            ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),
            master_briefing_card
        ], spacing=12, scroll=ft.ScrollMode.ALWAYS)

        render_viewport(briefing_layout)

    def on_tech_identity_change(e):
        tech_identity["email"] = str(e.control.value)
        show_toast_local(f"Switched Technician View: {tech_identity['email']}", kind="info")
        load_chronological_feed_view()

    tech_identity_dropdown = ft.Dropdown(
        value=tech_identity["email"],
        options=[
            ft.dropdown.Option("tech1@tbcotampaservice.com", "Tech One (Bob)"),
            ft.dropdown.Option("tech2@tbcotampaservice.com", "Alex Tech (tech2@tbcotampaservice.com)"),
            ft.dropdown.Option("admin@tombarrow.com", "Office Admin (Alice)")
        ],
        border_color=FieldFlowLightTheme.ACCENT_BLUE,
        text_size=12,
        height=38,
        dense=True,
        on_change=on_tech_identity_change
    )

    def load_chronological_feed_view():
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.icons.REFRESH,
            tooltip="Refresh Assigned Feed",
            bgcolor=FieldFlowLightTheme.PRIMARY_GREEN,
            on_click=lambda e: load_chronological_feed_view()
        )
        
        dispatch_cards_list = []
        raw_jobs_map = {}

        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT d.*, 
                           l.street_address_1 || ', ' || l.city || ', ' || l.state AS site_address,
                           i.issue_description, i.contractor_company_name, i.site_name, i.project_name,
                           u.first_name AS sales_first_name, u.last_name AS sales_last_name
                    FROM dispatches d
                    LEFT JOIN projects p ON d.tbc_job_number = p.tbc_job_number
                    LEFT JOIN locations l ON p.site_name = l.site_name
                    LEFT JOIN intake_requests i ON d.tbc_job_number = i.tbc_job_number
                    LEFT JOIN users u ON i.sales_rep_email = u.user_email
                    WHERE LOWER(d.technician_email) = LOWER(?)
                """, (tech_identity["email"],))
                rows = cursor.fetchall()
                for r in rows:
                    r_dict = dict(r)
                    j_id = str(r_dict.get("job_id"))
                    r_dict["drive_id"] = f"FLD-DRIVE-{r_dict.get('tbc_job_number', '123456XX')}"
                    if j_id:
                        raw_jobs_map[j_id] = r_dict
        except Exception as err:
            print(f"Local SQLite dispatch query note: {err}")

        if db is not None:
            try:
                dispatches_ref = db.collection("dispatches").stream()
                for doc in dispatches_ref:
                    d_data = doc.to_dict()
                    tech_e = str(d_data.get("technician_email") or "").lower()
                    if tech_e == tech_identity["email"].lower():
                        doc_str_id = str(doc.id)
                        d_data["job_id"] = doc_str_id
                        t_num = str(d_data.get("tbc_job_number") or "")
                        d_data["drive_id"] = f"FLD-DRIVE-{t_num or '123456XX'}"
                        raw_jobs_map[doc_str_id] = d_data
            except Exception as err:
                print(f"Cloud Firestore dispatch query note: {err}")

        raw_jobs = list(raw_jobs_map.values())
        today_date_str = datetime.now().strftime("%Y-%m-%d")
        assigned_jobs = []

        for job in raw_jobs:
            status = str(job.get("status", "Scheduled")).strip()
            sched_time = str(job.get("scheduled_time", ""))

            if status == "Completed":
                job_date = sched_time.split("T")[0] if "T" in sched_time else sched_time.split(" ")[0]
                if job_date and job_date < today_date_str:
                    continue

            assigned_jobs.append(job)

        def get_dispatches_priority(job):
            status = str(job.get("status", "Scheduled")).strip()
            if status == "Pending":
                return (0, str(job.get("scheduled_time", "")))
            elif status == "Completed":
                return (2, str(job.get("scheduled_time", "")))
            else:
                return (1, str(job.get("scheduled_time", "")))

        assigned_jobs.sort(key=get_dispatches_priority)

        if not assigned_jobs:
            dispatch_cards_list.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.WORK_OUTLINE, color=FieldFlowLightTheme.TEXT_MUTED, size=32),
                        ft.Text("No active service dispatches assigned to this user.", size=13, color=FieldFlowLightTheme.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                        ft.Text(f"Logged In: {tech_identity['email']}", size=11, color=FieldFlowLightTheme.ACCENT_BLUE, weight=ft.FontWeight.BOLD)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                    bgcolor=FieldFlowLightTheme.SURFACE_HOVER, padding=24, border_radius=8, border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE)
                )
            )
        else:
            for job in assigned_jobs:
                tbc_num = str(job.get("tbc_job_number", "889900XX"))
                drive_id = job.get("drive_id") or f"FLD-DRIVE-{tbc_num}"

                card = build_standard_ticket_card(
                    record_data=job,
                    card_context="mobile",
                    on_drive_action=lambda e, dr=drive_id: open_drive_local(dr),
                    on_primary_action=lambda e, j_data=job: load_job_briefing_view(j_data),
                    page=page
                )
                dispatch_cards_list.append(card)

        feed_header = ft.Column([
            ft.Row([
                ft.Text("Assigned Dispatches", size=20, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
                ft.IconButton(
                    icon=ft.icons.REFRESH,
                    icon_color=FieldFlowLightTheme.ACCENT_BLUE,
                    tooltip="Refresh Feed",
                    on_click=lambda e: load_chronological_feed_view()
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            tech_identity_dropdown
        ], spacing=6)

        feed_layout = ft.Column([
            feed_header,
            ft.Divider(height=10, color=FieldFlowLightTheme.BORDER_SUBTLE),
            ft.Column(controls=dispatch_cards_list, spacing=12)
        ], spacing=10, scroll=ft.ScrollMode.ALWAYS)
        
        render_viewport(feed_layout)

    load_chronological_feed_view()


if __name__ == "__main__":
    ft.app(target=main)