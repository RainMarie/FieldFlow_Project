"""
src/frontend/calendar_component.py
Modular interactive calendar component supporting Month, Agenda, and Technician views.
Integrates local SQLite, cloud Firestore, and live Google Calendar API events.
"""

import calendar
from datetime import datetime, timezone
import flet as ft

from src.backend.db_manager import db, local_db
from src.backend.calendar_service import GoogleCalendarService
from src.frontend.theme import FieldFlowLightTheme


def build_calendar_widget(page: ft.Page, on_ticket_select_callback):
    """Builds a multi-view interactive calendar component with bounded layout height."""
    active_date = {"value": datetime.now()}
    active_view = {"value": "Month"}  # Options: "Month", "Agenda", "Technician"

    calendar_body_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    month_label_text = ft.Text(
        active_date["value"].strftime("%B %Y").upper(),
        size=15,
        weight=ft.FontWeight.BOLD,
        color=FieldFlowLightTheme.TEXT_PRIMARY
    )

    def fetch_google_calendar_events(year: int, month: int):
        """Fetches live events directly from Google Calendar API for active month range."""
        google_events = []
        try:
            cal_service_builder = GoogleCalendarService()
            service = cal_service_builder.build_service()
            if not service:
                return google_events

            first_day = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
            last_day_num = calendar.monthrange(year, month)[1]
            last_day = datetime(year, month, last_day_num, 23, 59, 59, tzinfo=timezone.utc)

            events_result = service.events().list(
                calendarId='primary',
                timeMin=first_day.isoformat(),
                timeMax=last_day.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            items = events_result.get('items', [])
            for item in items:
                start_raw = item.get('start', {}).get('dateTime') or item.get('start', {}).get('date', '')
                sched_time = start_raw[:10] if start_raw else datetime.now().strftime("%Y-%m-%d")

                summary = item.get('summary', 'Google Calendar Event')
                ext_props = item.get('extendedProperties', {}).get('private', {})
                job_id = ext_props.get('Job_ID') or item.get('id')

                google_events.append({
                    "job_id": str(job_id),
                    "tbc_job_number": summary.split()[0] if summary else "GCAL",
                    "technician_email": item.get('organizer', {}).get('email', 'Google Calendar'),
                    "scheduled_time": sched_time,
                    "status": "Scheduled",
                    "job_type": summary,
                    "site_name": item.get('location') or summary,
                    "drive_id": "FLD-DRIVE-GCAL",
                    "source": "google_calendar"
                })
        except Exception as err:
            print(f"Google Calendar API fetch error: {err}")

        return google_events

    def fetch_dispatches(fetch_gcal: bool = False):
        """Fetches dispatches from local SQLite, Cloud Firestore, and optionally live Google Calendar API."""
        rows = []
        seen_job_ids = set()

        # Fetch SQLite dispatches (Instant local memory read)
        try:
            with local_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT d.job_id, d.tbc_job_number, d.technician_email, d.scheduled_time, d.status, d.job_type, p.site_name
                    FROM dispatches d
                    LEFT JOIN projects p ON d.tbc_job_number = p.tbc_job_number
                    WHERE d.status IN ('Scheduled', 'Traveling', 'Traveling (Return)', 'In Progress', 'Pending')
                    ORDER BY d.scheduled_time ASC
                """)
                for row in cursor.fetchall():
                    r_dict = dict(row)
                    r_dict["drive_id"] = f"FLD-DRIVE-{r_dict.get('tbc_job_number', '123456XX')}"
                    rows.append(r_dict)
                    if r_dict.get("job_id"):
                        seen_job_ids.add(r_dict["job_id"])
        except Exception as err:
            print(f"Calendar SQLite fetch error: {err}")

        # Fetch Firestore dispatches
        if db is not None:
            try:
                query = db.collection("dispatches").stream()
                for doc in query:
                    data = doc.to_dict()
                    data["job_id"] = doc.id
                    if data["job_id"] not in seen_job_ids:
                        data["drive_id"] = f"FLD-DRIVE-{data.get('tbc_job_number', '123456XX')}"
                        rows.append(data)
                        seen_job_ids.add(data["job_id"])
            except Exception as err:
                print(f"Calendar Firestore fetch error: {err}")

        # Live Google Calendar API HTTP fetch triggers ONLY on explicit demand
        if fetch_gcal:
            gcal_events = fetch_google_calendar_events(
                active_date["value"].year,
                active_date["value"].month
            )
            for g_event in gcal_events:
                if g_event["job_id"] not in seen_job_ids:
                    rows.append(g_event)
                    seen_job_ids.add(g_event["job_id"])

        return rows

    def get_status_color(status_str: str):
        st = str(status_str or "").lower()
        if "in progress" in st:
            return FieldFlowLightTheme.PRIMARY_GREEN
        if "traveling" in st:
            return FieldFlowLightTheme.SUN_AMBER
        if "pending" in st:
            return FieldFlowLightTheme.PINK_PRIMARY
        return FieldFlowLightTheme.TEXT_MUTED

    def build_tag_chip(dispatch_data):
        job_num = dispatch_data.get("tbc_job_number", "NEW")
        site = dispatch_data.get("site_name") or dispatch_data.get("job_type") or "Site"
        bg_color = get_status_color(dispatch_data.get("status"))

        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.ASSIGNMENT_IND, size=12, color="white"),
                ft.Text(f"#{job_num} - {site}", size=11, weight=ft.FontWeight.BOLD, color="white", no_wrap=True)
            ], spacing=4, tight=True),
            bgcolor=bg_color,
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
            border_radius=12,
            tooltip=f"Click to edit Ticket #{job_num} ({dispatch_data.get('technician_email')})",
            on_click=lambda e, d=dispatch_data: on_ticket_select_callback(d)
        )

    def build_month_grid_view(dispatches):
        year = active_date["value"].year
        month = active_date["value"].month
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(year, month)

        grid_column = ft.Column(spacing=6)
        day_headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        header_row = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(day, weight=ft.FontWeight.BOLD, size=12, color=FieldFlowLightTheme.PINK_PRIMARY, text_align=ft.TextAlign.CENTER),
                    expand=True,
                    padding=4
                ) for day in day_headers
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        grid_column.controls.append(header_row)

        for week in month_days:
            week_row = ft.Row(spacing=6)
            for day in week:
                if day == 0:
                    week_row.controls.append(
                        ft.Container(
                            bgcolor=FieldFlowLightTheme.SURFACE_HOVER,
                            border_radius=6,
                            padding=4,
                            height=95,
                            expand=True
                        )
                    )
                else:
                    date_str = f"{year:04d}-{month:02d}-{day:02d}"
                    day_tickets = [
                        d for d in dispatches 
                        if str(d.get("scheduled_time", "")).startswith(date_str)
                    ]

                    cell_content = ft.Column([
                        ft.Text(str(day), size=11, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY),
                        ft.Column(
                            controls=[build_tag_chip(t) for t in day_tickets],
                            spacing=3,
                            scroll=ft.ScrollMode.AUTO,
                            expand=True
                        )
                    ], spacing=2, expand=True)

                    is_today = (
                        day == datetime.now().day and 
                        month == datetime.now().month and 
                        year == datetime.now().year
                    )

                    cell_border = ft.border.all(2, FieldFlowLightTheme.PINK_PRIMARY) if is_today else ft.border.all(1, FieldFlowLightTheme.BORDER_PINK_EDGE)
                    cell_bg = FieldFlowLightTheme.BG_PINK_TINT if is_today else FieldFlowLightTheme.SURFACE_CARD

                    week_row.controls.append(
                        ft.Container(
                            content=cell_content,
                            bgcolor=cell_bg,
                            border=cell_border,
                            border_radius=6,
                            padding=6,
                            height=95,
                            expand=True
                        )
                    )
            grid_column.controls.append(week_row)

        return grid_column

    def build_agenda_list_view(dispatches):
        if not dispatches:
            return ft.Container(
                content=ft.Text("No dispatches scheduled.", size=12, color=FieldFlowLightTheme.TEXT_MUTED),
                padding=16
            )

        agenda_column = ft.Column(spacing=8, scroll=ft.ScrollMode.ALWAYS)
        for ticket in dispatches:
            sched = ticket.get("scheduled_time", "Unscheduled")
            tech = ticket.get("technician_email", "Unassigned")
            
            row_card = ft.Container(
                content=ft.Row([
                    ft.Text(sched, size=12, weight=ft.FontWeight.BOLD, color=FieldFlowLightTheme.TEXT_PRIMARY, width=110),
                    build_tag_chip(ticket),
                    ft.Text(f"Assigned: {tech}", size=12, color=FieldFlowLightTheme.TEXT_MUTED, expand=True),
                    ft.Icon(ft.icons.CHEVRON_RIGHT, color=FieldFlowLightTheme.PINK_PRIMARY, size=18)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=10,
                bgcolor=FieldFlowLightTheme.SURFACE_CARD,
                border_radius=6,
                border=ft.border.all(1, FieldFlowLightTheme.BORDER_PINK_EDGE),
                on_click=lambda e, t=ticket: on_ticket_select_callback(t)
            )
            agenda_column.controls.append(row_card)

        return agenda_column

    def build_technician_group_view(dispatches):
        if not dispatches:
            return ft.Container(
                content=ft.Text("No active technician dispatches.", size=12, color=FieldFlowLightTheme.TEXT_MUTED),
                padding=16
            )

        grouped = {}
        for d in dispatches:
            tech = d.get("technician_email") or "Unassigned"
            grouped.setdefault(tech, []).append(d)

        tech_row = ft.Row(spacing=12, scroll=ft.ScrollMode.ALWAYS, vertical_alignment=ft.CrossAxisAlignment.START)
        for tech_email, tickets in grouped.items():
            column_cards = ft.Column([
                ft.Text(tech_email, weight=ft.FontWeight.BOLD, size=13, color=FieldFlowLightTheme.PINK_PRIMARY),
                ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE),
                ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Date: {t.get('scheduled_time')}", size=11, color=FieldFlowLightTheme.TEXT_MUTED),
                            build_tag_chip(t)
                        ], spacing=4),
                        padding=8,
                        bgcolor=FieldFlowLightTheme.SURFACE_HOVER,
                        border_radius=6,
                        border=ft.border.all(1, FieldFlowLightTheme.BORDER_PINK_EDGE)
                    ) for t in tickets
                ], spacing=8)
            ], spacing=6)

            tech_row.controls.append(
                ft.Container(
                    content=column_cards,
                    width=250,
                    padding=12,
                    bgcolor=FieldFlowLightTheme.SURFACE_CARD,
                    border_radius=8,
                    border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE)
                )
            )

        return tech_row

    def refresh_calendar(fetch_gcal: bool = False):
        calendar_body_container.controls.clear()
        dispatches = fetch_dispatches(fetch_gcal=fetch_gcal)

        if active_view["value"] == "Month":
            calendar_body_container.controls.append(build_month_grid_view(dispatches))
        elif active_view["value"] == "Agenda":
            calendar_body_container.controls.append(build_agenda_list_view(dispatches))
        elif active_view["value"] == "Technician":
            calendar_body_container.controls.append(build_technician_group_view(dispatches))

        month_label_text.value = active_date["value"].strftime("%B %Y").upper()
        page.update()

    def change_month(delta_months: int):
        month = active_date["value"].month - 1 + delta_months
        year = active_date["value"].year + month // 12
        month = month % 12 + 1
        active_date["value"] = datetime(year, month, 1)
        refresh_calendar(fetch_gcal=True)

    def set_view_mode(mode_name: str):
        active_view["value"] = mode_name
        refresh_calendar()

    # Define navigation controls
    prev_month_btn = ft.IconButton(
        icon=ft.icons.CHEVRON_LEFT,
        icon_color=FieldFlowLightTheme.PINK_PRIMARY,
        on_click=lambda _: change_month(-1)
    )
    next_month_btn = ft.IconButton(
        icon=ft.icons.CHEVRON_RIGHT,
        icon_color=FieldFlowLightTheme.PINK_PRIMARY,
        on_click=lambda _: change_month(1)
    )

    btn_month = ft.ElevatedButton(
        "Month View",
        on_click=lambda _: set_view_mode("Month"),
        style=FieldFlowLightTheme.get_primary_button_style()
    )
    btn_agenda = ft.OutlinedButton(
        "Agenda View",
        on_click=lambda _: set_view_mode("Agenda")
    )
    btn_tech = ft.OutlinedButton(
        "Technician View",
        on_click=lambda _: set_view_mode("Technician")
    )

    header_controls = ft.Row(
        [
            ft.Row([prev_month_btn, next_month_btn, month_label_text], spacing=4),
            ft.Row([btn_month, btn_agenda, btn_tech], spacing=8)
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
    )

    # Instantiate the layout container
    main_calendar_layout = ft.Container(
        content=ft.Column(
            [
                header_controls,
                ft.Divider(color=FieldFlowLightTheme.BORDER_PINK_EDGE, height=12),
                calendar_body_container
            ],
            expand=True,
            spacing=10
        ),
        expand=True
    )

    # Initial load populates live Google Calendar events once on boot
    refresh_calendar(fetch_gcal=True)

    # Return the UI widget layout and refresh function handle
    return main_calendar_layout, refresh_calendar
