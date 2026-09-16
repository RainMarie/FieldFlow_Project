import flet as ft
import time
import os
import sys

# Dynamic path resolution to connect with local backend engines safely
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.frontend.theme import FieldFlowLightTheme
from src.backend.db_manager import db, local_db


def build_vfd_service_form(
    asset_data: dict,
    job_data: dict,
    on_submit_callback,
    on_back_callback,
    show_toast_fn
) -> ft.Column:
    """
    Modular Component: Multi-Step Inspection Wizard
    Supports both VFD Startup reports (3 steps) and General Service reports (2 steps).
    """
    asset_serial = str(asset_data.get("serial_number", "SN-UNKNOWN"))
    asset_id = str(asset_data.get("asset_id") or f"AST-{asset_serial}")
    asset_name = str(asset_data.get("asset_name", "Site Asset"))
    job_id = str(job_data.get("job_id", "JOB-UNKNOWN"))
    tbc_job_num = str(job_data.get("tbc_job_number", "889900XX"))
    job_type = str(job_data.get("job_type", "VFD_STARTUP")).upper()

    current_step = {"page": 1}

    badge_bg, badge_color = FieldFlowLightTheme.resolve_status_badge_colors("PENDING_TRIAGE")
    status_text = ft.Text("FORM STATUS: LOCAL DRAFT", size=11, weight=ft.FontWeight.BOLD, color=badge_color)
    status_container = ft.Container(
        content=status_text, 
        bgcolor=badge_bg, 
        padding=ft.padding.symmetric(horizontal=12, vertical=6), 
        border_radius=4
    )

    def on_field_change(e):
        update_wizard_ui()

    def make_compact_tf(label, value="", multiline=False, expand=False):
        return ft.TextField(
            label=label,
            value=str(value),
            multiline=multiline,
            min_lines=2 if multiline else 1,
            max_lines=3 if multiline else 1,
            border_color=FieldFlowLightTheme.ACCENT_BLUE,
            focused_border_color=FieldFlowLightTheme.PRIMARY_GREEN,
            text_size=13,
            height=72 if multiline else 42,
            content_padding=8,
            dense=True,
            expand=expand,
            on_change=on_field_change
        )

    def make_compact_dd(label, value, options, expand=False):
        return ft.Dropdown(
            label=label,
            value=str(value),
            options=[ft.dropdown.Option(str(opt)) for opt in options],
            border_color=FieldFlowLightTheme.ACCENT_BLUE,
            text_size=13,
            height=42,
            content_padding=8,
            dense=True,
            expand=expand,
            on_change=on_field_change
        )

    if "VFD" in job_type:
        photo_locks = {"unit_label": False, "motor_tag": False, "drive_label": False}

        unit_type_input = make_compact_dd("Type of Unit*", "AHU", ["AHU", "Fan", "Pump"])
        unit_tag_input = make_compact_tf("Unit Tag / Mark*", "AHU-1")
        wiring_dist_input = make_compact_tf("Wiring Distance Motor-Drive (Ft)*", "50")
        reactor_input = make_compact_dd("Is There a Reactor Present?*", "YES", ["YES", "NO"])

        drive_tag_input = make_compact_tf("Drive Tag*", "VFD-AHU-1")
        
        l1_l2_input = make_compact_tf("L1 to L2*", "460", expand=True)
        l2_l3_input = make_compact_tf("L2 to L3*", "460", expand=True)
        l3_l1_input = make_compact_tf("L3 to L1*", "460", expand=True)
        
        l1_gnd_input = make_compact_tf("L1 to Gnd*", "265", expand=True)
        l2_gnd_input = make_compact_tf("L2 to Gnd*", "265", expand=True)
        l3_gnd_input = make_compact_tf("L3 to Gnd*", "265", expand=True)

        t1_t2_input = make_compact_tf("T1 to T2*", "460", expand=True)
        t2_t3_input = make_compact_tf("T2 to T3*", "460", expand=True)
        t3_t1_input = make_compact_tf("T3 to T1*", "460", expand=True)

        t1_amp_input = make_compact_tf("T1 Amps*", "14.2", expand=True)
        t2_amp_input = make_compact_tf("T2 Amps*", "14.1", expand=True)
        t3_amp_input = make_compact_tf("T3 Amps*", "14.2", expand=True)

        verified_params_input = make_compact_dd("Verified Drive Params Programmed?*", "YES", ["YES", "NO"])

        sw_version_input = make_compact_tf("Software Version (U1-14/U1-25)*", "1010")
        comm_method_input = make_compact_tf("Serial Comm Methods Used*", "BACnet MSTP")
        bypass_sw_input = make_compact_tf("Bypass Software Number (UB-18)*", "N/A")
        app_type_input = make_compact_tf("Describe Type of Application*", "Supply Fan")

        field_notes_input = make_compact_tf("Field Notes*", "Startup completed smoothly without fault.", multiline=True)
        vfd_status_input = make_compact_dd(
            "Status of Startup*", "Complete", 
            ["Complete", "Not complete - weather", "Not complete - electrical", "Not complete - mechanical"]
        )
        resolution_input = make_compact_tf("Resolution, Next Steps*", "Unit turned over to site operations.")
        travel_hours_input = make_compact_tf("Travel Hours*", "1.0", expand=True)
        work_hours_input = make_compact_tf("Work Hours*", "2.5", expand=True)

        def make_photo_box(label_text):
            icon = ft.Icon(ft.icons.CAMERA_ALT, color=FieldFlowLightTheme.TEXT_MUTED, size=18)
            text = ft.Text(label_text, color=FieldFlowLightTheme.TEXT_MUTED, weight=ft.FontWeight.BOLD, size=12)
            box = ft.Container(
                content=ft.Row([icon, text], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=FieldFlowLightTheme.SURFACE_HOVER, 
                padding=8, 
                border_radius=6, 
                border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE), 
                height=40
            )
            return box, icon, text

        box_unit, icon_unit, text_unit = make_photo_box("Photo of Unit Label*")
        box_motor, icon_motor, text_motor = make_photo_box("Photo of Motor Tag*")
        box_drive, icon_drive, text_drive = make_photo_box("Photo of Drive Label*")

        def bind_photo_click(box, icon, text, key):
            def on_click(e):
                photo_locks[key] = True
                box.bgcolor = FieldFlowLightTheme.BG_GREEN_TINT
                box.border = ft.border.all(1, FieldFlowLightTheme.PRIMARY_GREEN)
                icon.name = ft.icons.CHECK_CIRCLE
                icon.color = FieldFlowLightTheme.PRIMARY_GREEN
                text.value = f"{key.replace('_', ' ').title()} Verified! ✅"
                text.color = FieldFlowLightTheme.PRIMARY_GREEN
                box.update()
                update_wizard_ui()
            box.on_click = on_click

        bind_photo_click(box_unit, icon_unit, text_unit, "unit_label")
        bind_photo_click(box_motor, icon_motor, text_motor, "motor_tag")
        bind_photo_click(box_drive, icon_drive, text_drive, "drive_label")

        step1_content = ft.Column([
            ft.Text("Step 1: Unit & Motor Identification", size=13, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            unit_type_input, unit_tag_input, box_unit, box_motor, wiring_dist_input, reactor_input
        ], spacing=8)

        step2_content = ft.Column([
            ft.Text("Step 2: Drive & Electrical Measurements", size=13, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            drive_tag_input, box_drive,
            ft.Text("Input Line Voltage (VAC)", size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_MUTED),
            ft.Row([l1_l2_input, l2_l3_input, l3_l1_input], spacing=6),
            ft.Row([l1_gnd_input, l2_gnd_input, l3_gnd_input], spacing=6),
            ft.Text("Output Voltage (VAC)", size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_MUTED),
            ft.Row([t1_t2_input, t2_t3_input, t3_t1_input], spacing=6),
            ft.Text("Output Current @ Full Speed (A)", size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_MUTED),
            ft.Row([t1_amp_input, t2_amp_input, t3_amp_input], spacing=6),
            verified_params_input
        ], spacing=8)

        step3_content = ft.Column([
            ft.Text("Step 3: Software, Notes & Hours", size=13, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            sw_version_input, comm_method_input, bypass_sw_input, app_type_input,
            field_notes_input, vfd_status_input, resolution_input,
            ft.Row([travel_hours_input, work_hours_input], spacing=6)
        ], spacing=8)

        def assemble_vfd_payload():
            return {
                "unit_type": str(unit_type_input.value),
                "unit_tag_mark": str(unit_tag_input.value),
                "photo_unit_label": "CAPTURED",
                "photo_motor_tag": "CAPTURED",
                "wiring_distance_ft": float(wiring_dist_input.value or 0),
                "is_reactor_present": str(reactor_input.value),
                "drive_tag": str(drive_tag_input.value),
                "photo_drive_label": "CAPTURED",
                "l1_l2": float(l1_l2_input.value or 0),
                "l2_l3": float(l2_l3_input.value or 0),
                "l3_l1": float(l3_l1_input.value or 0),
                "l1_gnd": float(l1_gnd_input.value or 0),
                "l2_gnd": float(l2_gnd_input.value or 0),
                "l3_gnd": float(l3_gnd_input.value or 0),
                "t1_t2": float(t1_t2_input.value or 0),
                "t2_t3": float(t2_t3_input.value or 0),
                "t3_t1": float(t3_t1_input.value or 0),
                "t1": float(t1_amp_input.value or 0),
                "t2": float(t2_amp_input.value or 0),
                "t3": float(t3_amp_input.value or 0),
                "verified_yaskawa_params": str(verified_params_input.value),
                "software_version": str(sw_version_input.value),
                "serial_comm_method": str(comm_method_input.value),
                "bypass_software_num": str(bypass_sw_input.value),
                "application_type": str(app_type_input.value),
                "field_notes": str(field_notes_input.value),
                "status": str(vfd_status_input.value),
                "resolution_next_steps": str(resolution_input.value),
                "travel_hours": float(travel_hours_input.value or 0),
                "work_hours": float(work_hours_input.value or 0)
            }

        max_steps = 3

    else:
        desc_issue_input = make_compact_tf("Description of Issue (Optional)")
        visual_insp_input = make_compact_tf("Visual Inspection Results (Optional)")
        checks_input = make_compact_tf("Electrical / Mechanical Checks (Optional)")
        root_cause_input = make_compact_tf("Root Cause Identified (Optional)")

        req_parts_input = make_compact_tf("Recommended Repairs - Parts (Optional)")
        req_labor_input = make_compact_tf("Recommended Repairs - Labor (Optional)")
        addl_recs_input = make_compact_tf("Additional Recommendations (Optional)")

        work_completed_input = make_compact_tf("Work Completed*", "Replaced control board and tested operation.", multiline=True)
        parts_replaced_input = make_compact_tf("Parts Replaced (Optional)")

        test_results_input = make_compact_tf("Operational Test Results (Optional)")
        airflow_input = make_compact_tf("Airflow / Performance Verification (Optional)")

        unit_status_input = make_compact_dd("Unit Status*", "Operational", ["Operational", "Needs follow up"])
        addl_notes_input = make_compact_tf("Additional Notes (Optional)")
        travel_hours_input = make_compact_tf("Travel Hours (Optional)", "1.0", expand=True)
        work_hours_input = make_compact_tf("Work Hours (Optional)", "1.5", expand=True)

        step1_content = ft.Column([
            ft.Text("Step 1: Diagnostics & Scope", size=13, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            desc_issue_input, visual_insp_input, checks_input, root_cause_input,
            req_parts_input, req_labor_input, addl_recs_input
        ], spacing=8)

        step2_content = ft.Column([
            ft.Text("Step 2: Repairs & Status", size=13, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
            work_completed_input, parts_replaced_input,
            test_results_input, airflow_input, unit_status_input, addl_notes_input,
            ft.Row([travel_hours_input, work_hours_input], spacing=6)
        ], spacing=8)

        step3_content = ft.Container()

        def assemble_gs_payload():
            return {
                "description_of_issue": str(desc_issue_input.value or ""),
                "visual_inspection_results": str(visual_insp_input.value or ""),
                "electrical_mechanical_checks": str(checks_input.value or ""),
                "root_cause_identified": str(root_cause_input.value or ""),
                "recommended_repairs_parts": str(req_parts_input.value or ""),
                "recommended_repairs_labor": str(req_labor_input.value or ""),
                "additional_recommendations": str(addl_recs_input.value or ""),
                "work_completed": str(work_completed_input.value),
                "parts_replaced": str(parts_replaced_input.value or ""),
                "operational_test_results": str(test_results_input.value or ""),
                "airflow_performance_verification": str(airflow_input.value or ""),
                "unit_status": str(unit_status_input.value),
                "additional_notes": str(addl_notes_input.value or ""),
                "travel_hours": float(travel_hours_input.value or 0),
                "work_hours": float(work_hours_input.value or 0)
            }

        max_steps = 2

    step_badge = ft.Text(f"Step {current_step['page']} of {max_steps}", size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE)
    progress_bar = ft.ProgressBar(value=current_step['page'] / max_steps, color=FieldFlowLightTheme.ACCENT_BLUE, bgcolor=FieldFlowLightTheme.SURFACE_HOVER, height=4)

    validation_status_msg = ft.Text("", size=11, color=FieldFlowLightTheme.SUN_AMBER, weight=ft.FontWeight.W_500)
    validation_status_banner = ft.Container(
        content=ft.Row([
            ft.Icon(ft.icons.INFO_OUTLINE, color=FieldFlowLightTheme.SUN_AMBER, size=16),
            validation_status_msg
        ], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=FieldFlowLightTheme.BG_AMBER_TINT, padding=8, border_radius=6, border=ft.border.all(1, FieldFlowLightTheme.SUN_AMBER), visible=False
    )

    prev_btn = ft.OutlinedButton("⬅️ Previous", disabled=True, style=FieldFlowLightTheme.get_secondary_button_style())
    next_btn = ft.ElevatedButton("Next ➡️", style=FieldFlowLightTheme.get_primary_button_style())
    
    submit_service_btn = ft.ElevatedButton(
        "Upload Service Report 🚀",
        disabled=True,
        visible=False,
        style=FieldFlowLightTheme.get_primary_button_style(),
        width=380
    )

    active_step_container = ft.Container(content=step1_content)

    def update_wizard_ui():
        p = current_step['page']
        step_badge.value = f"Step {p} of {max_steps}"
        progress_bar.value = p / max_steps

        if p == 1:
            active_step_container.content = step1_content
            prev_btn.disabled = True
            next_btn.visible = True
            submit_service_btn.visible = False
            validation_status_banner.visible = False
        elif p == 2:
            active_step_container.content = step2_content
            prev_btn.disabled = False
            if max_steps == 2:
                next_btn.visible = False
                submit_service_btn.visible = True
                validation_status_banner.visible = True
            else:
                next_btn.visible = True
                submit_service_btn.visible = False
                validation_status_banner.visible = False
        elif p == 3:
            active_step_container.content = step3_content
            prev_btn.disabled = False
            next_btn.visible = False
            submit_service_btn.visible = True
            validation_status_banner.visible = True

        missing_items = []
        if "VFD" in job_type:
            if not photo_locks["unit_label"]: missing_items.append("Photo: Unit Label (Step 1)")
            if not photo_locks["motor_tag"]: missing_items.append("Photo: Motor Tag (Step 1)")
            if not photo_locks["drive_label"]: missing_items.append("Photo: Drive Label (Step 2)")

            vfd_checks = [
                ("Unit Type", unit_type_input.value),
                ("Unit Tag", unit_tag_input.value),
                ("Wiring Distance", wiring_dist_input.value),
                ("Reactor Present", reactor_input.value),
                ("Drive Tag", drive_tag_input.value),
                ("L1-L2", l1_l2_input.value), ("L2-L3", l2_l3_input.value), ("L3-L1", l3_l1_input.value),
                ("L1-Gnd", l1_gnd_input.value), ("L2-Gnd", l2_gnd_input.value), ("L3-Gnd", l3_gnd_input.value),
                ("T1-T2", t1_t2_input.value), ("T2-T3", t2_t3_input.value), ("T3-T1", t3_t1_input.value),
                ("T1 Amps", t1_amp_input.value), ("T2 Amps", t2_amp_input.value), ("T3 Amps", t3_amp_input.value),
                ("Verified Params", verified_params_input.value),
                ("Software Version", sw_version_input.value),
                ("Serial Comm Method", comm_method_input.value),
                ("Bypass Software", bypass_sw_input.value),
                ("Application Type", app_type_input.value),
                ("Field Notes", field_notes_input.value),
                ("Status", vfd_status_input.value),
                ("Resolution", resolution_input.value),
                ("Travel Hours", travel_hours_input.value),
                ("Work Hours", work_hours_input.value)
            ]

            for label, val in vfd_checks:
                if not val or not str(val).strip():
                    missing_items.append(str(label))

        else:
            if not work_completed_input.value or not work_completed_input.value.strip():
                missing_items.append("Work Completed")
            if not unit_status_input.value:
                missing_items.append("Unit Status")

        if missing_items:
            submit_service_btn.disabled = True
            clean_missing = [str(x) for x in missing_items[:3]]
            validation_status_msg.value = f"Pending: {', '.join(clean_missing)}" + ("..." if len(missing_items) > 3 else "")
            validation_status_banner.bgcolor = FieldFlowLightTheme.BG_AMBER_TINT
            validation_status_banner.border = ft.border.all(1, FieldFlowLightTheme.SUN_AMBER)
            validation_status_msg.color = FieldFlowLightTheme.SUN_AMBER
        else:
            submit_service_btn.disabled = False
            validation_status_msg.value = "All Requirements Satisfied! Ready to Upload."
            validation_status_banner.bgcolor = FieldFlowLightTheme.BG_GREEN_TINT
            validation_status_banner.border = ft.border.all(1, FieldFlowLightTheme.PRIMARY_GREEN)
            validation_status_msg.color = FieldFlowLightTheme.PRIMARY_GREEN

        validation_status_banner.update()

    def go_next(e):
        if current_step['page'] < max_steps:
            current_step['page'] += 1
            update_wizard_ui()

    def go_prev(e):
        if current_step['page'] > 1:
            current_step['page'] -= 1
            update_wizard_ui()

    prev_btn.on_click = go_prev
    next_btn.on_click = go_next

    def handle_submit_service_report(e):
        metrics_payload = assemble_vfd_payload() if "VFD" in job_type else assemble_gs_payload()
        is_vfd = "VFD" in job_type
        target_status = "Pending" if is_vfd else (metrics_payload.get("unit_status") or "Completed")

        try:
            report_id = f"RPT-{int(time.time())}"
            
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO assets (asset_id, tbc_job_number, model_number, serial_number, equipment_tag)
                    VALUES (?, ?, ?, ?, ?)
                """, (str(asset_id), str(tbc_job_num), "MOD-VFD", str(asset_serial), str(asset_name)))
                conn.commit()

            if db is not None:
                db.collection("assets").document(str(asset_id)).set({
                    "asset_id": str(asset_id),
                    "tbc_job_number": str(tbc_job_num),
                    "model_number": "MOD-VFD",
                    "serial_number": str(asset_serial),
                    "equipment_tag": str(asset_name)
                }, merge=True)

                db.collection("asset_inspections").document(str(report_id)).set({
                    "report_id": str(report_id),
                    "job_id": str(job_id),
                    "asset_id": str(asset_id),
                    "registration_status": target_status,
                    "job_type": str(job_type),
                    "inspection_metrics": metrics_payload
                }, merge=True)

            on_submit_callback(asset_serial, target_status, metrics_payload)

        except Exception as err:
            show_toast_fn(f"Submission Error: {err}", kind="error")

    submit_service_btn.on_click = handle_submit_service_report

    update_wizard_ui()

    return ft.Column([
        ft.Row([
            ft.TextButton("<- Back to Asset Info", style=FieldFlowLightTheme.get_secondary_button_style(), on_click=on_back_callback)
        ]),
        ft.Row([status_container, step_badge], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        progress_bar,
        ft.Text(f"Service Form: {job_type}", size=16, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
        ft.Text(f"Asset: {asset_name} | S/N: {asset_serial}", size=11, color=FieldFlowLightTheme.TEXT_MUTED),
        ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),
        active_step_container,
        ft.Divider(height=5, color=FieldFlowLightTheme.BORDER_SUBTLE),
        validation_status_banner,
        ft.Row([prev_btn, next_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        submit_service_btn
    ], spacing=8, scroll=ft.ScrollMode.ALWAYS)