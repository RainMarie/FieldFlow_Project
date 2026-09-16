import flet as ft
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

def main(page: ft.Page):
    page.title = "FieldFlow Governance Shell"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    
    # -----------------------------------------------------------------
    # ACCESS GOVERNANCE SETTINGS (Table 4 Simulation)
    # -----------------------------------------------------------------
    CURRENT_USER_NAME = "Tech Bob"
    USER_HAS_ADMIN_FLAG = False  # Grants access to Office Control Tower
    USER_HAS_TECH_FLAG = True   # Grants access to Mobile Field Suite
    
    # 1. HEAVY DESKTOP VIEWPORT (Admin Control Tower Dashboard)
    desktop_view = ft.Container(
        content=ft.Text(f"🖥️ Admin Control Tower | Workspace: {CURRENT_USER_NAME}", size=20, weight=ft.FontWeight.BOLD),
        bgcolor="#1E1E26",
        padding=40,
        alignment=ft.alignment.center,
        expand=True
    )
    
    # 2. CRISP MOBILE VIEWPORT (Simulated Phone Body Container)
    # The UX Fix: We clip its width to 450px max and center it so it looks like a real smartphone layout!
    mobile_phone_chassis = ft.Container(
        content=ft.Column([
            ft.Text(f"📱 Mobile Field Suite", size=18, weight=ft.FontWeight.BOLD, color="#00A86B"),
            ft.Text(f"Active Operator: {CURRENT_USER_NAME}", size=14, color="#A0A0A0"),
            ft.Divider(color="#222222"),
            ft.Text("Chronological Navigation Feed (Ready for Sprints)", size=14)
        ], spacing=10),
        bgcolor="#0A0A0C",
        padding=25,
        width=450, # Absolute maximum smartphone width boundary
        border_radius=24,
        border=ft.border.all(1, "#222222")
    )
    
    # Centers the smartphone chassis perfectly inside a pitch-black holding bay
    mobile_view_centered = ft.Container(
        content=mobile_phone_chassis,
        bgcolor="#020203",
        alignment=ft.alignment.center,
        expand=True
    )
    
    # 3. HARD LOCKOUT SECURITY INTERCEPT CARD 
    # Displays the exact corporate text mandated by our technical project baseline [cite: 310, 311]
    hard_error_card = ft.Container(
        content=ft.Column([
            ft.Text("🛑 Access Restricted", size=22, weight=ft.FontWeight.BOLD, color="#FF3333"),
            ft.Text(
                "The Admin Control Tower is optimized for desktop environments. "
                "Please utilize a desktop executable or workstation browser to review administrative dashboards.",
                size=14,
                color="#E0E0E0",
                text_align=ft.TextAlign.CENTER
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
        bgcolor="#1A0D0D", # Subtle warning dark red tint
        padding=40,
        alignment=ft.alignment.center,
        expand=True
    )

    # THE CORE INTERACTION ENGINE
    def evaluate_viewport_governance(e=None):
        # DETECT SMARTPHONE HARDWARE LAYER RUNTIME (Small Screen)
        if page.width < 768:
            if USER_HAS_ADMIN_FLAG and USER_HAS_TECH_FLAG:
                # Multi-role user trying to pull heavy desktop dashboards onto a phone screen gets blocked! 
                main_layout.controls = [hard_error_card]
            elif USER_HAS_TECH_FLAG:
                # Pure technicians get the clean mobile suite automatically [cite: 308]
                main_layout.controls = [mobile_view_centered]
            else:
                main_layout.controls = [ft.Container(content=ft.Text("🔒 Access Denied"), alignment=ft.alignment.center)]
        
        # DETECT DESKTOP WORKSTATION LAYER RUNTIME (Large Screen)
        else:
            if USER_HAS_ADMIN_FLAG:
                # Authorized coordinators get the full desktop interface workspace
                main_layout.controls = [desktop_view]
            else:
                # Pure technicians on a desktop get a clean, centered phone-frame model layout
                main_layout.controls = [mobile_view_centered]
                
        page.update()

    main_layout = ft.Column(expand=True)
    page.add(main_layout)

    page.on_resize = evaluate_viewport_governance
    evaluate_viewport_governance()

if __name__ == "__main__":
    ft.app(target=main)