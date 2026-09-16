import flet as ft
import threading
import time

def main(page: ft.Page):
    page.title = "FieldFlow - Smart Form Sandbox"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK

    photo_states = {"data_plate": False, "control_screen": False}
    
    # Emergency Brake Switch: Used to signal the background clock to stop
    timer_cancelled = False

    # Asynchronous Clock Loop
    def countdown_clock_worker():
        nonlocal timer_cancelled
        timer_cancelled = False  # Reset the brake flag on launch
        total_seconds = 10       # 10 seconds for rapid testing!
        
        while total_seconds > 0:
            # STEP 1: Constantly check if the technician pulled the emergency brake
            if timer_cancelled:
                return  # Quietly exit and kill this background thread loop completely!
                
            mins, secs = divmod(total_seconds, 60)
            countdown_text.value = f"Local Edit Window: {mins}:{secs:02d} remaining before data freeze."
            page.update()
            time.sleep(1)
            total_seconds -= 1
            
        countdown_text.value = "Local edit window has expired. Data is frozen. 🔒"
        countdown_container.bgcolor = "#7f1d1d" 
        countdown_container.border = ft.border.all(1, ft.colors.RED_400)
        
        serial_field.read_only = True
        model_field.read_only = True
        serial_field.border_color = ft.colors.GREY_700
        model_field.border_color = ft.colors.GREY_700
        page.update()

    # STEP 2: The Emergency Brake Function (Fires the moment a text box is clicked)
    def handle_field_focus(e):
        nonlocal timer_cancelled
        
        # Only pull the brake if the 5-minute freeze hasn't firmly engaged yet 
        if not e.control.read_only and countdown_container.visible == True:
            timer_cancelled = True  # Tell the background thread to die
            
            # Instantly revert visual layout states back to an active editing draft 
            status_text.value = "FORM STATUS: LOCAL DRAFT"
            status_text.color = ft.colors.AMBER_400
            status_container.bgcolor = "#3A2A00"
            
            countdown_container.visible = False  # Hide the ticking clock
            
            # Restore the Submit Button to its live, active state
            submit_button.disabled = False
            submit_button.text = "Submit Field Report"
            submit_button.style.bgcolor = ft.colors.BLUE_600
            page.update()

    def start_submit_sequence(e):
        status_text.value = "FORM STATUS: READY FOR REVIEW"
        status_text.color = ft.colors.GREEN_400
        status_container.bgcolor = "#064E3B"
        
        countdown_container.visible = True
        
        submit_button.disabled = True
        submit_button.text = "Report Staged for Sync"
        submit_button.style.bgcolor = ft.colors.BLUE_GREY_800
        page.update()
        
        clock_thread = threading.Thread(target=countdown_clock_worker, daemon=True)
        clock_thread.start()

    def validate_evidence_locks():
        if photo_states["data_plate"] and photo_states["control_screen"]:
            submit_button.disabled = False
            submit_button.style.color = ft.colors.WHITE
            submit_button.style.bgcolor = ft.colors.BLUE_600
        else:
            submit_button.disabled = True
        page.update()

    def upload_data_plate(e):
        photo_states["data_plate"] = True
        data_plate_box.bgcolor = "#064E3B"
        data_plate_box.border = ft.border.all(1, ft.colors.GREEN_400)
        data_plate_icon.name = ft.icons.CHECK_CIRCLE
        data_plate_icon.color = ft.colors.GREEN_400
        data_plate_text.value = "Data Plate Photo Logged! ✅"
        data_plate_text.color = ft.colors.GREEN_400
        validate_evidence_locks()

    def upload_control_screen(e):
        photo_states["control_screen"] = True
        control_box.bgcolor = "#064E3B"
        control_box.border = ft.border.all(1, ft.colors.GREEN_400)
        control_icon.name = ft.icons.CHECK_CIRCLE
        control_icon.color = ft.colors.GREEN_400
        control_text.value = "Control Screen Photo Logged! ✅"
        control_text.color = ft.colors.GREEN_400
        validate_evidence_locks()

    def handle_typing(e):
        if not e.control.read_only:
            e.control.border_color = ft.colors.AMBER_600
            e.control.focused_border_color = ft.colors.AMBER_600
            page.update()

    def handle_save(e):
        if not e.control.read_only:
            if e.control.value:
                e.control.border_color = ft.colors.GREEN_600
                e.control.focused_border_color = ft.colors.GREEN_600
            else:
                e.control.border_color = ft.colors.GREY_600
                e.control.focused_border_color = ft.colors.BLUE_400
            page.update()

    status_text = ft.Text("FORM STATUS: LOCAL DRAFT", size=11, weight=ft.FontWeight.BOLD, color=ft.colors.AMBER_400)
    status_container = ft.Container(content=status_text, bgcolor="#3A2A00", padding=ft.padding.symmetric(horizontal=12, vertical=6), border_radius=4)

    countdown_text = ft.Text("", size=13, color=ft.colors.AMBER_300, weight=ft.FontWeight.W_500)
    countdown_container = ft.Container(
        content=ft.Row([ft.Icon(ft.icons.TIMER_OUTLINED, color=ft.colors.AMBER_300, size=18), countdown_text], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#2C1A04", padding=10, border_radius=6, visible=False, border=ft.border.all(1, ft.colors.AMBER_800)
    )

    # STEP 3: Integrated 'on_focus' listener straight to our text boxes
    serial_field = ft.TextField(
        label="Asset Serial Number", hint_text="Enter plate serial number", 
        border_width=2, border_color=ft.colors.GREY_600, focused_border_color=ft.colors.BLUE_400, 
        on_change=handle_typing, on_submit=handle_save, on_blur=handle_save,
        on_focus=handle_field_focus  # Intercepts focus event to kill the timer loop
    )
    
    model_field = ft.TextField(
        label="Asset Model Number", hint_text="Enter equipment model structure", 
        border_width=2, border_color=ft.colors.GREY_600, focused_border_color=ft.colors.BLUE_400, 
        on_change=handle_typing, on_submit=handle_save, on_blur=handle_save,
        on_focus=handle_field_focus  # Intercepts focus event to kill the timer loop
    )

    data_plate_icon = ft.Icon(ft.icons.CAMERA_ALT, color=ft.colors.GREY_400)
    data_plate_text = ft.Text("Upload Data Plate Photo", color=ft.colors.GREY_400, weight=ft.FontWeight.BOLD)
    control_icon = ft.Icon(ft.icons.EJECT, color=ft.colors.GREY_400)
    control_text = ft.Text("Upload Control Screen Photo", color=ft.colors.GREY_400, weight=ft.FontWeight.BOLD)

    submit_button = ft.ElevatedButton(
        text="Submit Field Report", disabled=True,
        style=ft.ButtonStyle(color=ft.colors.GREY_500, bgcolor=ft.colors.BLUE_GREY_800, padding=18, shape=ft.RoundedRectangleBorder(radius=8)),
        width=350, on_click=start_submit_sequence
    )

    form_chassis = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row([status_container], alignment=ft.MainAxisAlignment.START),
                ft.Text("Asset Validation Form", size=22, weight=ft.FontWeight.BOLD),
                countdown_container,
                ft.Divider(height=5, color=ft.colors.GREY_700),
                serial_field, model_field,
                ft.Divider(height=5, color=ft.colors.GREY_700),
                ft.Text("Mandatory Evidence Locks", size=16, weight=ft.FontWeight.W_600),
                data_plate_box := ft.Container(content=ft.Row([data_plate_icon, data_plate_text], alignment=ft.MainAxisAlignment.CENTER), bgcolor=ft.colors.BLUE_GREY_800, padding=15, border_radius=8, border=ft.border.all(1, ft.colors.GREY_600), on_click=upload_data_plate),
                control_box := ft.Container(content=ft.Row([control_icon, control_text], alignment=ft.MainAxisAlignment.CENTER), bgcolor=ft.colors.BLUE_GREY_800, padding=15, border_radius=8, border=ft.border.all(1, ft.colors.GREY_600), on_click=upload_control_screen),
                ft.Divider(height=5, color=ft.colors.GREY_700),
                ft.Row([submit_button], alignment=ft.MainAxisAlignment.CENTER)
            ],
            spacing=15,
        ),
        bgcolor=ft.colors.BLUE_GREY_900, padding=24, border_radius=12, width=400,
    )
    page.add(form_chassis)

ft.app(target=main)