"""
src/frontend/cards_component.py
Consolidated card rendering module for FieldFlow using standardized key names,
project photo rendering with Google Drive direct link support, Company Project Manager integration,
uniform FieldFlowLightTheme styling, and card-level click interactions.
"""

import os
import sys
import glob
import re
import flet as ft

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.frontend.theme import FieldFlowLightTheme
from src.frontend.shared_utils import find_any_local_logo, get_base64_from_file


# =========================================================================
# 1. SHARED VISUAL & FORMATTING UTILITY HELPERS
# =========================================================================

def build_truncating_text(text_val: str, size: int = 11, bold: bool = False, color_token=None) -> ft.Text:
    """Helper to cleanly truncate long text fields with an ellipsis."""
    return ft.Text(
        value=text_val,
        size=size,
        weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
        color=color_token,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        expand=True
    )


def build_clickable_email_link(page: ft.Page, email_addr: str, display_name: str = "") -> ft.Text:
    """Helper to generate a clickable mailto: link that truncates on small screens."""
    if not email_addr or email_addr == "N/A":
        return build_truncating_text("No Email", size=11, color_token=FieldFlowLightTheme.TEXT_MUTED)
        
    label = f"{display_name} ({email_addr})" if display_name else email_addr
    return ft.Text(
        spans=[
            ft.TextSpan(
                label,
                ft.TextStyle(
                    color=FieldFlowLightTheme.ACCENT_BLUE, 
                    decoration=ft.TextDecoration.UNDERLINE
                ),
                on_click=lambda e: page.launch_url(f"mailto:{email_addr}")
            )
        ],
        size=11,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        expand=True
    )


def calculate_ticket_progress(status_string: str) -> tuple[str, str]:
    """Translates a dispatch completion status into a theme color token and clean status text."""
    status = str(status_string or "Scheduled").strip()

    if status == "Scheduled":
        return FieldFlowLightTheme.ACCENT_BLUE, "Scheduled"
    elif status == "Traveling":
        return FieldFlowLightTheme.ACCENT_BLUE, "En Route to Site"
    elif status == "In Progress":
        return FieldFlowLightTheme.SUN_AMBER, "Work In Progress"
    elif status == "Traveling (Return)":
        return FieldFlowLightTheme.ACCENT_BLUE, "Return Travel"
    elif status == "Pending":
        return FieldFlowLightTheme.SUN_AMBER, "Pending Review"
    elif status == "Completed":
        return FieldFlowLightTheme.PRIMARY_GREEN, "Completed"
    else:
        return FieldFlowLightTheme.TEXT_MUTED, "Unassigned"


def extract_drive_direct_url(input_path: str) -> str:
    """
    Parses Google Drive web URLs or File IDs and converts them into direct thumbnail/image links.
    Converts links like 'drive.google.com/file/d/FILE_ID/view' into 'https://lh3.googleusercontent.com/d/FILE_ID'.
    """
    if not input_path or not isinstance(input_path, str):
        return ""

    val = input_path.strip()

    # Pattern 1: URL containing /file/d/FILE_ID/
    file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', val)
    if file_id_match:
        file_id = file_id_match.group(1)
        return f"https://lh3.googleusercontent.com/d/{file_id}"

    # Pattern 2: URL containing id=FILE_ID
    id_param_match = re.search(r'id=([a-zA-Z0-9_-]+)', val)
    if id_param_match:
        file_id = id_param_match.group(1)
        return f"https://lh3.googleusercontent.com/d/{file_id}"

    # Pattern 3: Raw Google Drive File ID (alphanumeric, length >= 25)
    if re.match(r'^[a-zA-Z0-9_-]{25,}$', val):
        return f"https://lh3.googleusercontent.com/d/{val}"

    return val


def build_project_image_control(photo_url_or_path: str, height: int = 120) -> ft.Control:
    """
    Renders Google Drive images, network images, local disk images, 
    or styled fallback brand containers.
    """
    processed_val = extract_drive_direct_url(photo_url_or_path)

    # Handle Direct HTTP/HTTPS Web URLs (including converted Google Drive thumbnail links)
    if processed_val.startswith("http://") or processed_val.startswith("https://"):
        return ft.Image(
            src=processed_val,
            height=height,
            fit=ft.ImageFit.COVER,
            border_radius=6,
            error_content=ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.icons.BROKEN_IMAGE_OUTLINED, color=FieldFlowLightTheme.TEXT_MUTED, size=20),
                        ft.Text("Image Unavailable", size=11, color=FieldFlowLightTheme.TEXT_MUTED)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                alignment=ft.alignment.center,
                height=height,
                bgcolor=FieldFlowLightTheme.SURFACE_CARD,
                border_radius=6
            )
        )

    # Handle Local Disk Files
    target_file = None
    if processed_val and os.path.exists(processed_val):
        if os.path.isfile(processed_val):
            target_file = processed_val
        elif os.path.isdir(processed_val):
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.PNG"]:
                found = glob.glob(os.path.join(processed_val, ext))
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
                bgcolor=FieldFlowLightTheme.SURFACE_CARD,
                padding=6,
                border_radius=6,
                alignment=ft.alignment.center
            )

    # Fallback TBCo Brand Logo Container
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.icons.BUSINESS, color=FieldFlowLightTheme.PINK_PRIMARY, size=24),
                ft.Text("TBCo PROJECT SITE", weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.PINK_PRIMARY, size=13)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8
        ),
        bgcolor=FieldFlowLightTheme.BG_PINK_TINT,
        height=height,
        border_radius=6,
        border=ft.border.all(1, FieldFlowLightTheme.BORDER_PINK_EDGE),
        alignment=ft.alignment.center
    )


# =========================================================================
# 2. PROJECT CARD BUILDER
# =========================================================================

def build_project_card(
    project_data: object,
    is_grid_mode: bool = True,
    on_edit_action=None,
    on_drive_action=None,
    on_service_request_action=None
) -> ft.Card:
    """
    Renders a project card container for Projects Registry in Grid or List mode.
    Directly consumes canonical keys for Contractor, Company PM, and Sales Rep.
    """
    if isinstance(project_data, dict):
        job_num = project_data.get("tbc_job_number", "123456XX")
        name = project_data.get("project_name", "Service Project")
        st1 = project_data.get("street_address_1", "")
        c_city = project_data.get("city", "")
        c_state = project_data.get("state", "")

        address = f"{st1}, {c_city}, {c_state}".strip(", ") if st1 else project_data.get("site_name", "Pending Address")

        client = project_data.get("contractor_company_name", "Partner")
        acct_no = project_data.get("tbco_account_number", "N/A")
        site_name = project_data.get("site_name", name)
        
        raw_drive_id = project_data.get("drive_id")
        if not raw_drive_id or str(raw_drive_id).strip() in ["", "None", "FLD-0", "FLD-DRIVE-123456XX"]:
            drive_id = f"FLD-GDRV-{job_num}"
        else:
            drive_id = str(raw_drive_id).strip()

        photo_url = project_data.get("photo_url", "")

        pm_f = project_data.get("pm_first_name", "")
        pm_l = project_data.get("pm_last_name", "")
        pm_em = project_data.get("pm_email", "")
        pm_ph = project_data.get("pm_phone", "")

        sales_em = project_data.get("sales_rep_email", "")
        sales_ph = project_data.get("sales_rep_phone", "")
        team_code = project_data.get("team_code", "")
    else:
        job_num, name, address, client, acct_no, drive_id, photo_url = "123456XX", "Project", "Pending Address", "Partner", "N/A", "FLD-GDRV-123456XX", ""
        st1, c_city, c_state = "", "", ""
        site_name = name
        pm_f, pm_l, pm_em, pm_ph = "", "", "", ""
        sales_em, sales_ph, team_code = "", "", ""

    pm_full_name = f"{pm_f} {pm_l}".strip() or "Unassigned PM"

    prefill_payload = {
        "tbc_job_number": job_num,
        "project_name": name,
        "contractor_company_name": client,
        "tbco_account_number": acct_no,
        "site_name": site_name,
        "street_address_1": st1,
        "city": c_city,
        "state": c_state,
        "pm_first_name": pm_f,
        "pm_last_name": pm_l,
        "pm_email": pm_em,
        "pm_phone": pm_ph,
        "sales_rep_email": sales_em,
        "sales_rep_phone": sales_ph,
        "team_code": team_code,
        "drive_id": drive_id,
        "photo_url": photo_url
    }

    def handle_service_request_click(e):
        if on_service_request_action:
            on_service_request_action(prefill_payload)

    def handle_drive_click(e):
        if on_drive_action:
            on_drive_action(e)

    def handle_edit_click(e):
        if on_edit_action:
            on_edit_action(project_data)

    if is_grid_mode:
        img_control = build_project_image_control(photo_url, height=120)
        
        # Upper clickable body (triggers project edit dialog only)
        card_body = ft.Container(
            on_click=handle_edit_click,
            ink=True,
            border_radius=6,
            content=ft.Column(
                [
                    img_control,
                    ft.Row(
                        [
                            ft.Text(f"Job #{job_num}", size=16, weight=ft.FontWeight.BOLD, font_family="monospace", color=FieldFlowLightTheme.PINK_PRIMARY),
                            ft.Container(
                                content=ft.Text(f"Acct: {acct_no}", size=10, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.ACCENT_BLUE),
                                bgcolor=FieldFlowLightTheme.BG_BLUE_TINT,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                border_radius=4
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Text(name, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY, size=15, no_wrap=True),
                    ft.Text(f"Client: {client}", weight=ft.FontWeight.W_500, color=FieldFlowLightTheme.TEXT_PRIMARY, size=12, no_wrap=True),
                    ft.Text(f"📍 {address}", size=11, color=FieldFlowLightTheme.TEXT_MUTED, no_wrap=True),
                    ft.Row(
                        [
                            ft.Icon(ft.icons.PERSON_OUTLINE, size=14, color=FieldFlowLightTheme.ACCENT_BLUE),
                            build_truncating_text(f"PM: {pm_full_name}" + (f" ({pm_em})" if pm_em else ""), 11, False, FieldFlowLightTheme.TEXT_MUTED)
                        ],
                        spacing=4
                    ),
                    ft.Row(
                        [
                            ft.Icon(ft.icons.BADGE_OUTLINED, size=14, color=FieldFlowLightTheme.PINK_PRIMARY),
                            build_truncating_text(f"Sales: {sales_em or 'N/A'}" + (f" [{team_code}]" if team_code else ""), 11, False, FieldFlowLightTheme.TEXT_MUTED)
                        ],
                        spacing=4
                    ),
                ],
                spacing=5
            )
        )

        # Isolated action bar (prevents click propagation)
        card_actions = ft.Column(
            [
                ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=8),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Drive",
                            icon=ft.icons.LAUNCH,
                            on_click=handle_drive_click,
                            style=FieldFlowLightTheme.get_secondary_button_style()
                        ),
                        ft.OutlinedButton(
                            "Edit",
                            icon=ft.icons.EDIT,
                            on_click=handle_edit_click,
                            style=FieldFlowLightTheme.get_secondary_button_style()
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.ElevatedButton(
                    "+ Service Request",
                    icon=ft.icons.POST_ADD,
                    on_click=handle_service_request_click,
                    style=FieldFlowLightTheme.get_primary_button_style()
                )
            ],
            spacing=6
        )

        return ft.Card(
            content=ft.Container(
                padding=12,
                bgcolor=FieldFlowLightTheme.SURFACE_CARD,
                border_radius=8,
                width=350,
                border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
                shadow=FieldFlowLightTheme.get_card_shadow(),
                content=ft.Column([card_body, card_actions], spacing=2)
            )
        )
    else:
        small_img = ft.Container(
            content=build_project_image_control(photo_url, height=48),
            width=70,
            height=48,
            border_radius=4,
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )

        # Clickable info section (triggers project edit dialog only)
        list_info_section = ft.Container(
            on_click=handle_edit_click,
            ink=True,
            expand=True,
            border_radius=4,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            content=ft.Row(
                [
                    small_img,
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(f"Job #{job_num}", size=14, weight=ft.FontWeight.BOLD, font_family="monospace", color=FieldFlowLightTheme.PINK_PRIMARY),
                                    ft.Text(name or f"Service: {client}", weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY, size=13, no_wrap=True)
                                ],
                                spacing=10
                            ),
                            ft.Text(f"Client: {client} ({acct_no})   |   PM: {pm_full_name} ({pm_em or 'N/A'})   |   {address}", size=11, color=FieldFlowLightTheme.TEXT_MUTED, no_wrap=True)
                        ],
                        spacing=2,
                        expand=True
                    )
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

        # Isolated right-aligned action buttons
        list_action_section = ft.Row(
            [
                ft.ElevatedButton(
                    "+ Service Request",
                    icon=ft.icons.POST_ADD,
                    on_click=handle_service_request_click,
                    style=FieldFlowLightTheme.get_primary_button_style()
                ),
                ft.IconButton(
                    icon=ft.icons.FOLDER_OUTLINED,
                    icon_color=FieldFlowLightTheme.PINK_PRIMARY,
                    tooltip="Open Drive Folder",
                    on_click=handle_drive_click
                ),
                ft.IconButton(
                    icon=ft.icons.EDIT_OUTLINED,
                    icon_color=FieldFlowLightTheme.TEXT_PRIMARY,
                    tooltip="Edit Project Details",
                    on_click=handle_edit_click
                ),
            ],
            spacing=6
        )

        return ft.Card(
            content=ft.Container(
                padding=10,
                bgcolor=FieldFlowLightTheme.SURFACE_CARD,
                border_radius=8,
                width=1180,
                border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
                shadow=FieldFlowLightTheme.get_card_shadow(),
                content=ft.Row(
                    [list_info_section, list_action_section],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            )
        )


# =========================================================================
# 3. SERVICE TICKET CARD BUILDER
# =========================================================================

def build_standard_ticket_card(
    record_data: dict,
    card_context: str = "triage",
    card_tech_dropdown=None,
    card_date_input=None,
    card_date_btn=None,
    on_primary_action=None,
    on_details_action=None,
    on_drive_action=None,
    page: ft.Page = None
) -> ft.Container:
    """Renders ticket cards consuming canonical key names directly."""
    
    job_num = record_data.get("tbc_job_number", "123456XX")
    contractor = record_data.get("contractor_company_name", "Unspecified Client")
    site_campus = record_data.get("site_name", "Site Campus")
    project_name = record_data.get("project_name", "Service Request")

    street = record_data.get("street_address_1", "")
    city = record_data.get("city", "")
    state = record_data.get("state", "")
    
    if street and city and state:
        address_display = f"{street}, {city}, {state}"
    elif street:
        address_display = street
    elif city and state:
        address_display = f"{city}, {state}"
    else:
        address_display = "Pending Address"

    description = record_data.get("issue_description", "Service Call")
    status = record_data.get("triage_status", record_data.get("status", "Unassigned"))
    req_id = record_data.get("request_id", "REQ-NEW")

    sales_f = str(record_data.get("sales_first_name") or "").strip()
    sales_l = str(record_data.get("sales_last_name") or "").strip()
    sales_email = record_data.get("sales_rep_email", "")
    
    if sales_f or sales_l:
        sales_full_name = f"{sales_f} {sales_l}".strip()
    elif sales_email:
        sales_full_name = sales_email.split("@")[0].replace(".", " ").title()
    else:
        sales_full_name = "Unassigned Sales Rep"

    cnt_f = str(record_data.get("project_site_contact_first_name") or "").strip()
    cnt_l = str(record_data.get("project_site_contact_last_name") or "").strip()
    cnt_phone = record_data.get("project_site_contact_phone", "N/A")
    
    if cnt_f or cnt_l:
        cnt_full_name = f"{cnt_f} {cnt_l}".strip()
    else:
        cnt_full_name = "Site Contact (N/A)"

    badge_bg, badge_color = FieldFlowLightTheme.resolve_status_badge_colors(status)

    status_badge = ft.Container(
        content=ft.Text(status, size=10, weight=ft.FontWeight.BOLD, color=badge_color),
        bgcolor=badge_bg, padding=ft.padding.symmetric(horizontal=8, vertical=3), border_radius=4
    )

    line_1 = ft.Row([build_truncating_text(f"Job #{job_num} • {contractor}", 12, True, FieldFlowLightTheme.ACCENT_BLUE), status_badge], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    line_2 = ft.Row([build_truncating_text(f"{project_name} ({site_campus})", 13, True, FieldFlowLightTheme.TEXT_PRIMARY)])
    line_3 = ft.Row([build_truncating_text(f"📍 {address_display} • 🔧 {description}", 11, False, FieldFlowLightTheme.TEXT_MUTED)])
    line_4a = ft.Row([ft.Icon(ft.icons.PERSON_OUTLINE, 14, FieldFlowLightTheme.ACCENT_BLUE), build_truncating_text(f"Sales Rep: {sales_full_name} ({sales_email})" if sales_email else f"Sales Rep: {sales_full_name}", 11, False, FieldFlowLightTheme.TEXT_MUTED)], spacing=4)
    line_4b = ft.Row([ft.Icon(ft.icons.PHONE, 14, FieldFlowLightTheme.PRIMARY_GREEN), build_truncating_text(f"Site Contact: {cnt_full_name} ({cnt_phone})", 11, False, FieldFlowLightTheme.TEXT_MUTED)], spacing=4)

    footer_ref = ft.Text(f"Tracking Ref: {req_id}", size=10, italic=True, color=FieldFlowLightTheme.TEXT_MUTED)

    action_controls = []
    if card_context == "triage" and card_tech_dropdown and card_date_input and card_date_btn:
        tech_wrapper = ft.Container(content=card_tech_dropdown, padding=ft.padding.only(top=4, bottom=4))
        date_wrapper = ft.Container(content=ft.Row([card_date_input, card_date_btn], spacing=6), padding=ft.padding.only(top=2, bottom=6))
        
        secondary_actions = ft.Row(
            [
                ft.OutlinedButton(
                    "📂 Drive",
                    icon=ft.icons.LAUNCH,
                    style=FieldFlowLightTheme.get_secondary_button_style(),
                    on_click=on_drive_action,
                    expand=True
                ),
                ft.OutlinedButton(
                    "✏️ Edit",
                    icon=ft.icons.EDIT_NOTE,
                    style=FieldFlowLightTheme.get_secondary_button_style(),
                    on_click=on_details_action,
                    expand=True
                )
            ],
            spacing=8
        )

        dispatch_btn = ft.ElevatedButton("⚡ Assign & Dispatch", style=FieldFlowLightTheme.get_primary_button_style(), on_click=on_primary_action)
        action_controls.extend([tech_wrapper, date_wrapper, secondary_actions, dispatch_btn])

    card_click_handler = on_details_action or on_primary_action

    return ft.Container(
        on_click=card_click_handler,
        ink=True if card_click_handler else False,
        content=ft.Column(
            [line_1, line_2, line_3, line_4a, line_4b, ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=8)] + action_controls + [footer_ref],
            spacing=8
        ),
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        padding=14,
        border_radius=8,
        border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
        shadow=FieldFlowLightTheme.get_card_shadow()
    )


# =========================================================================
# 4. SITE ASSET, VISIT HISTORY, & USER CARD BUILDERS
# =========================================================================

def build_site_asset_card(asset_data: dict, is_serviced: bool = False, on_click_action=None) -> ft.Container:
    name = str(asset_data.get("equipment_tag") or asset_data.get("asset_name", "Site Equipment"))
    model = str(asset_data.get("model_number", "N/A"))
    serial = str(asset_data.get("serial_number", "N/A"))

    badge_bg, badge_color = FieldFlowLightTheme.resolve_status_badge_colors("Completed" if is_serviced else "Unassigned")

    return ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Text(f"⚙️ {name}", weight=ft.FontWeight.BOLD, size=13, color=FieldFlowLightTheme.TEXT_PRIMARY),
                ft.Text(f"Model: {model} | S/N: {serial}", size=11, color=FieldFlowLightTheme.ACCENT_BLUE),
            ], spacing=2, expand=True),
            ft.Container(
                content=ft.Text("SERVICED ✅" if is_serviced else "PENDING", size=10, weight=ft.FontWeight.BOLD, color=badge_color),
                bgcolor=badge_bg,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=4
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=FieldFlowLightTheme.SURFACE_HOVER, padding=10, border_radius=6,
        border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE), on_click=on_click_action,
        ink=True if on_click_action else False
    )


def build_visit_history_card(visit_data: dict, on_click_action=None) -> ft.Container:
    v_date = str(visit_data.get("scheduled_time", "Past Date"))
    v_tech = str(visit_data.get("technician_email", "Tech Unassigned"))
    v_status = str(visit_data.get("status", "Completed"))

    v_badge_bg, v_badge_color = FieldFlowLightTheme.resolve_status_badge_colors(v_status)

    return ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Text(f"📅 Visit Date: {v_date}", weight=ft.FontWeight.BOLD, size=12, color=FieldFlowLightTheme.TEXT_PRIMARY),
                ft.Text(f"👨‍🔧 Tech: {v_tech}", size=11, color=FieldFlowLightTheme.TEXT_MUTED),
            ], spacing=2, expand=True),
            ft.Container(
                content=ft.Text(v_status, size=10, color=v_badge_color, weight=ft.FontWeight.BOLD),
                bgcolor=v_badge_bg, padding=ft.padding.symmetric(horizontal=8, vertical=3), border_radius=10
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=FieldFlowLightTheme.SURFACE_HOVER, padding=10, border_radius=6,
        border=ft.border.all(1, FieldFlowLightTheme.BORDER_SUBTLE), on_click=on_click_action,
        ink=True if on_click_action else False
    )


def build_user_card(user_data: dict, on_edit_action=None) -> ft.Card:
    email = user_data.get("user_email", "N/A")
    first_name = user_data.get("first_name", "")
    last_name = user_data.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip() or email
    role = user_data.get("role", "Sales")
    status = user_data.get("active_status", "Active")

    if role == "Admin":
        role_bg = FieldFlowLightTheme.BG_PINK_TINT
        role_color = FieldFlowLightTheme.PINK_PRIMARY
    elif role == "Technician":
        role_bg = FieldFlowLightTheme.BG_GREEN_TINT
        role_color = FieldFlowLightTheme.PRIMARY_GREEN
    else:
        role_bg = FieldFlowLightTheme.BG_BLUE_TINT
        role_color = FieldFlowLightTheme.ACCENT_BLUE

    status_bg, status_color = FieldFlowLightTheme.resolve_status_badge_colors(
        "Completed" if status == "Active" else ("Pending" if status == "Inactive" else "Cancelled")
    )

    return ft.Card(
        content=ft.Container(
            padding=14,
            bgcolor=FieldFlowLightTheme.SURFACE_CARD,
            border_radius=8,
            width=350,
            border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
            shadow=FieldFlowLightTheme.get_card_shadow(),
            on_click=on_edit_action,
            ink=True if on_edit_action else False,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(full_name, size=15, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY, expand=True),
                            ft.Container(
                                content=ft.Text(status, size=10, weight=ft.FontWeight.BOLD, color=status_color),
                                bgcolor=status_bg,
                                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                                border_radius=4
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Text(f"✉️ {email}", size=12, color=FieldFlowLightTheme.TEXT_MUTED, no_wrap=True),
                    ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=8),
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(f"Role: {role}", size=11, weight=ft.FontWeight.BOLD, color=role_color),
                                bgcolor=role_bg,
                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                border_radius=12
                            ),
                            ft.Icon(
                                name=ft.icons.EDIT_OUTLINED,
                                color=FieldFlowLightTheme.PINK_PRIMARY,
                                tooltip="Edit User Account"
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                ],
                spacing=6
            )
        )
    )