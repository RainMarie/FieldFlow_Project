import flet as ft

def main(page: ft.Page):
    # Enforce strict desktop window layout constraints
    page.title = "FieldFlow - Admin Control Tower"
    page.window_width = 1320
    page.window_height = 800
    page.window_min_width = 1200
    page.window_min_height = 700
    page.padding = 15
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"

    # --- UI STYLE CONSTANTS ---
    CARD_BG = "#1E1E1E"
    BORDER_COLOR = "#2D2D2D"
    COLOR_RESCUED = "#FFB000"  # Amber for anomalies
    COLOR_ROUTINE = "#2196F3"  # Blue for routine follow-ups
    COLOR_CALENDAR = "#00A86B" # FieldFlow Green

    # =========================================================================
    # 1. LEFT COLUMN: THE TRIAGE INBOX (30% WIDTH -> 370px)
    # =========================================================================
    triage_feed = ft.Column(spacing=10, scroll=ft.ScrollMode.ALWAYS, height=560)

    # Programmatically pinned "Rescued Field Data" container at the absolute top [cite: 202, 203]
    rescued_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Row([ft.Icon(ft.icons.SIGNAL_CELLULAR_OFF, color=COLOR_RESCUED, size=14),
                        ft.Text("RESCUED FIELD DATA", color=COLOR_RESCUED, size=10, weight=ft.FontWeight.BOLD)]),
                ft.Container(ft.Text("PINNED", size=9, color="#121212", weight=ft.FontWeight.BOLD), bgcolor=COLOR_RESCUED, padding=2, border_radius=3)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text("Job #123456XX - Typo Overwrite", weight=ft.FontWeight.BOLD, size=13),
            ft.Text("Tech Bob typed over incorrect model string on-site. Reality updated smoothly.", size=11, color="#B3B3B3"),
        ], spacing=4),
        bgcolor="#2A2115",
        padding=12,
        border_radius=6,
        border=ft.border.all(1, COLOR_RESCUED),
    )

    # Routine Field Follow-up Requests Feed derived from Table 13 [cite: 203]
    followup_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.ASSIGNMENT, color=COLOR_ROUTINE, size=14),
                ft.Text("FIELD FOLLOW-UP (TABLE 13)", color=COLOR_ROUTINE, size=10, weight=ft.FontWeight.BOLD),
            ]),
            ft.Text("Job #12345678 - VFD Child Drive", weight=ft.FontWeight.BOLD, size=13),
            ft.Text("Tech One logged: Urgency level 'Urgent'. Replacement components missing from master catalog.", size=11, color="#B3B3B3"),
        ], spacing=4),
        bgcolor="#15222E",
        padding=12,
        border_radius=6,
        border=ft.border.all(1, BORDER_COLOR),
    )

    triage_feed.controls.extend([rescued_container, followup_container])

    left_column = ft.Container(
        content=ft.Column([
            ft.Text("TRIAGE INBOX", weight=ft.FontWeight.BOLD, color="#FFFFFF", size=15),
            ft.Text("Live scrollable queue tracking unassigned items", size=11, color="#777777"),
            ft.Divider(color=BORDER_COLOR, height=10),
            triage_feed
        ]),
        bgcolor=CARD_BG, padding=15, border_radius=8, border=ft.border.all(1, BORDER_COLOR), width=370, height=680
    )

    # =========================================================================
    # 2. CENTER COLUMN: CENTRAL DISPATCH CALENDAR TIMELINE (40% WIDTH -> 490px)
    # =========================================================================
    # Day-Skipper Navigation Toolbar implementation
    calendar_nav = ft.Row([
        ft.IconButton(icon=ft.icons.CHEVRON_LEFT, icon_color=COLOR_CALENDAR, icon_size=20),
        ft.Text("WEDNESDAY: JUNE 24, 2026", weight=ft.FontWeight.BOLD, size=12, color="#FFFFFF"),
        ft.IconButton(icon=ft.icons.CHEVRON_RIGHT, icon_color=COLOR_CALENDAR, icon_size=20),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # Hourly schedule rows color-coded by technician asset operators [cite: 204]
    timeline_slots = ft.Column(spacing=8, scroll=ft.ScrollMode.ALWAYS, height=480)
    mock_hours = [
        ("08:00 AM", "TECH 1 (BOB) - JOB-5005 [Traveling to Site]", "#2196F3"),
        ("10:00 AM", "[ Unassigned Timeline Slot - Path A Target ]", "#333333"),
        ("12:00 PM", "TECH 2 (ALEX) - JOB-TEST-99 [In Progress]", "#E91E63"),
        ("02:00 PM", "[ Unassigned Timeline Slot ]", "#333333")
    ]

    for hour, task, color_hex in mock_hours:
        timeline_slots.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text(hour, size=11, color="#777777", width=60, weight=ft.FontWeight.BOLD),
                    ft.VerticalDivider(color="#2D2D2D"),
                    ft.Container(
                        content=ft.Text(task, size=11, color="#FFFFFF", weight=ft.FontWeight.W_500),
                        bgcolor=color_hex if color_hex != "#333333" else "transparent",
                        padding=ft.padding.symmetric(horizontal=10, vertical=8),
                        border_radius=4, expand=True,
                        border=ft.border.all(1, "#333333") if color_hex == "#333333" else None
                    )
                ]),
                height=45
            )
        )

    center_column = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.CALENDAR_TODAY, color=COLOR_CALENDAR, size=18),
                ft.Text("CENTRAL DISPATCH CALENDAR", weight=ft.FontWeight.BOLD, color=COLOR_CALENDAR, size=15),
            ], spacing=6),
            ft.Text("Timeline view tracking technician dispatches", size=11, color="#777777"),
            ft.Divider(color=BORDER_COLOR, height=10),
            calendar_nav,
            ft.Divider(color="#2D2D2D", height=5),
            timeline_slots
        ]),
        bgcolor=CARD_BG, padding=15, border_radius=8, border=ft.border.all(1, BORDER_COLOR), width=490, height=680
    )

    # =========================================================================
    # 3. RIGHT COLUMN: PULSE FEED SIDEBAR (30% WIDTH -> 370px)
    # =========================================================================
    # Inventory Actions Needed panel matching Table 11 quotas [cite: 206]
    inventory_alert_box = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.WARNING, color=COLOR_RESCUED, size=16),
                ft.Text("INVENTORY ACTIONS NEEDED", color=COLOR_RESCUED, size=11, weight=ft.FontWeight.BOLD),
            ], spacing=6),
            ft.Text("Unlisted Part Override Triggered:\nAsset ASSET-88092 needs manual unit cost resolution.", size=11, color="#B3B3B3"),
            ft.Row([
                ft.TextField(label="One-Time Manual Cost ($)", value="180.00", text_size=11, height=32, width=160, border_color="#444444"),
                ft.ElevatedButton("ENTER", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4)), height=32)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=5)
        ], spacing=8),
        bgcolor="#2A2115", padding=12, border_radius=6, border=ft.border.all(1, COLOR_RESCUED)
    )

    right_column = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.DASHBOARD, color="#FFFFFF", size=18),
                ft.Text("PULSE FEED SIDEBAR", weight=ft.FontWeight.BOLD, color="#FFFFFF", size=15),
            ], spacing=6),
            ft.Text("Real-time operational summaries & logs", size=11, color="#777777"),
            ft.Divider(color=BORDER_COLOR, height=10),
            
            # High-visibility streaming panel grouping a Daily Activity Summary [cite: 206]
            ft.Text("DAILY SUMMARY", size=11, color="#777777", weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Container(ft.Text("1 Traveling", size=10), bgcolor="#15222E", padding=5, border_radius=4),
                ft.Container(ft.Text("1 In Progress", size=10), bgcolor="#2E1C24", padding=5, border_radius=4),
                ft.Container(ft.Text("0 Restocked", size=10), bgcolor="#1C2E24", padding=5, border_radius=4),
            ], spacing=5),
            ft.Divider(color="#2D2D2D", height=15),
            
            # Real-time active technician site trackers [cite: 206]
            ft.Text("REAL-TIME VEHICLE TRACKING", size=11, color="#777777", weight=ft.FontWeight.BOLD),
            ft.Row([ft.Container(width=6, height=6, bgcolor="#2196F3", border_radius=3), ft.Text("Tech 1: Traveling to [Site: 123 Main St]", size=11)], spacing=8),
            ft.Row([ft.Container(width=6, height=6, bgcolor="#E91E63", border_radius=3), ft.Text("Tech 2: Active inside [Site: Automation Way]", size=11)], spacing=8),
            ft.Divider(color="#2D2D2D", height=15),
            
            inventory_alert_box
        ], spacing=8),
        bgcolor=CARD_BG, padding=15, border_radius=8, border=ft.border.all(1, BORDER_COLOR), width=370, height=680
    )

    # --- MASTER HORIZONTAL DIRECT GRID ASSIGNMENT ---
    master_workspace = ft.Row(
        controls=[left_column, center_column, right_column],
        spacing=15,
        alignment=ft.MainAxisAlignment.CENTER
    )

    page.add(master_workspace)

if __name__ == "__main__":
    ft.app(target=main)