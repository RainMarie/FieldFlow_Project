import flet as ft
import sqlite3
import os
import uuid
from datetime import datetime

# Automatically locate our local database file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(CURRENT_DIR), "backend", "tbc_local.db")

def create_context_locked_scheduler(project_data: dict, on_scheduled_callback=None):
    """
    ELI5: Creates a context-locked dispatch card.
    The project job number and address are locked to prevent human entry errors.
    """
    # 1. Extract auto-locked project parameters
    job_number = project_data.get("tbc_job_number", "123456XX")
    site_address = project_data.get("site_address", "123 Main St, Tampa, FL")
    contractor_name = project_data.get("contractor_name", "Acme Mechanical Solutions")

    # 2. Form Input Controls
    # SECURITY RULE: Technician selection is LEFT BLANK BY DEFAULT
    tech_dropdown = ft.Dropdown(
        label="Select Assigned Technician (Required)",
        hint_text="-- Choose an available field technician --",
        options=[
            ft.dropdown.Option("tech1@tbcotampaservice.com", "Bob (Senior Field Tech)"),
            ft.dropdown.Option("tech2@tbcotampaservice.com", "Alex (Field Tech)"),
            ft.dropdown.Option("tech3@tombarrow.com", "Charlie (HVAC Specialist)"),
        ],
        value=None,  # Enforces explicit selection
        border_color="#0B5FFF",
        focused_border_color="#00A86B",
        text_size=14,
    )

    issue_input = ft.TextField(
        label="Scope / Issue Description",
        hint_text="Enter required service details or maintenance checklist notes...",
        multiline=True,
        min_lines=2,
        max_lines=4,
        border_color="#333333",
        focused_border_color="#0B5FFF",
        text_size=14,
    )

    date_input = ft.TextField(
        label="Scheduled Date & Time",
        value=datetime.now().strftime("%Y-%m-%d 08:00 AM"),
        border_color="#333333",
        focused_border_color="#0B5FFF",
        text_size=14,
    )

    error_banner = ft.Text("", size=12, color=ft.colors.RED_400, visible=False)

    def handle_confirm_schedule(e):
        # Validation Guard: Block submission if dispatcher forgot to choose a technician
        if not tech_dropdown.value:
            error_banner.value = "⚠️ Guard Block: You must manually select an available technician."
            error_banner.visible = True
            e.page.update()
            return

        if not issue_input.value.strip():
            error_banner.value = "⚠️ Guard Block: Please enter a brief service description."
            error_banner.visible = True
            e.page.update()
            return

        error_banner.visible = False
        new_job_id = f"JOB-{uuid.uuid4().hex[:4].upper()}"

        # Direct, injection-proof database write to local dispatches table
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dispatches (
                    job_id, tbc_job_number, tech_email, technician_email, 
                    scheduled_time, completion_status, job_type, report_metrics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_job_id,
                job_number,
                tech_dropdown.value,
                tech_dropdown.value,
                date_input.value,
                "Scheduled",
                "SERVICE_VISIT",
                f'{{"issue_description": "{issue_input.value.strip()}"}}'
            ))
            conn.commit()
            conn.close()

            # Visual confirmation feedback
            e.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"🎉 Dispatch {new_job_id} context-locked to Project #{job_number}!"),
                bgcolor="#064E3B",
                duration=3000
            )
            e.page.snack_bar.open = True

            if on_scheduled_callback:
                on_scheduled_callback(new_job_id)

        except Exception as err:
            error_banner.value = f"Database write error: {str(err)}"
            error_banner.visible = True
            e.page.update()

    # 3. Assemble UI Container Architecture
    scheduler_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.LOCK_CLOCK, color="#0B5FFF", size=24),
                ft.Text("CONTEXT-LOCKED DISPATCH CREATOR", size=15, weight=ft.FontWeight.BOLD, color="#0B5FFF")
            ]),
            ft.Divider(color="#2D2D2D", height=10),

            # Locked Metadata Header Box
            ft.Container(
                content=ft.Column([
                    ft.Text("🔒 LOCKED PROJECT PARAMETERS", size=10, weight=ft.FontWeight.BOLD, color=ft.colors.GREY_500, font_family="monospace"),
                    ft.Row([
                        ft.Text(f"Project Job #: {job_number}", size=13, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                        ft.Container(ft.Text(contractor_name, size=10, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD), bgcolor=ft.colors.BLUE_GREY_700, padding=4, border_radius=4)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"📍 Location: {site_address}", size=12, color=ft.colors.GREY_300)
                ], spacing=4),
                bgcolor="#16181E",
                padding=12,
                border_radius=6,
                border=ft.border.all(1, "#0B5FFF")
            ),

            ft.Divider(color="#2D2D2D", height=10),

            # Dispatch Form Options
            tech_dropdown,
            date_input,
            issue_input,
            error_banner,

            ft.Row([
                ft.ElevatedButton(
                    text="Confirm & Dispatch Appointment",
                    icon=ft.icons.CALENDAR_MONTH,
                    style=ft.ButtonStyle(
                        bgcolor="#0B5FFF",
                        color=ft.colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=6)
                    ),
                    height=48,
                    expand=True,
                    on_click=handle_confirm_schedule
                )
            ])
        ], spacing=14),
        bgcolor="#1E1E1E",
        padding=20,
        border_radius=10,
        border=ft.border.all(1, "#333333"),
        width=480
    )

    return scheduler_card


# Standalone Test Execution Launcher
def main(page: ft.Page):
    page.title = "FieldFlow - Context-Locked Scheduler Test"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"
    page.alignment = ft.alignment.center

    # Sample Project context pulled from project tab selection
    sample_project = {
        "tbc_job_number": "123456XX",
        "site_address": "1 Hospital Segment Way, Tampa, FL",
        "contractor_name": "Acme Mechanical Solutions"
    }

    scheduler_widget = create_context_locked_scheduler(sample_project)
    page.add(scheduler_widget)

if __name__ == "__main__":
    ft.app(target=main)