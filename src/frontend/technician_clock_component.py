import flet as ft
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter

from src.backend.db_manager import db, local_db
from src.frontend.theme import FieldFlowLightTheme


def update_dispatch_status(job_identifier: str, new_status: str) -> bool:
    """Updates dispatch completion status in local SQLite and Cloud Firestore."""
    clean_id = str(job_identifier).strip()
    
    # 1. Update local SQLite database matching EITHER job_id OR tbc_job_number
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dispatches 
                SET completion_status = ? 
                WHERE job_id = ? OR tbc_job_number = ?
            """, (new_status, clean_id, clean_id))
            conn.commit()
    except Exception as e:
        print(f"Error updating local dispatch status: {e}")

    # 2. Update Cloud Firestore dispatches collection[cite: 2]
    if db is not None:
        try:
            db.collection("dispatches").document(clean_id).set({
                "completion_status": new_status,
                "last_modified_timestamp": datetime.now(timezone.utc)
            }, merge=True)
            
            query = db.collection("dispatches").where(filter=FieldFilter("tbc_job_number", "==", clean_id)).stream()
            for doc in query:
                doc.reference.set({
                    "completion_status": new_status,
                    "last_modified_timestamp": datetime.now(timezone.utc)
                }, merge=True)
            return True
        except Exception as e:
            print(f"Error updating cloud dispatch status: {e}")
            return False
    return True


def record_travel_start(job_id: str, tech_email: str, travel_type: str = "Outbound") -> bool:
    """Logs departure timestamp in labor_travel and updates dispatch status[cite: 2]."""
    clean_job_id = str(job_id)
    status_label = "Traveling" if travel_type == "Outbound" else "Traveling (Return)"
    update_dispatch_status(clean_job_id, status_label)

    if db is None:
        return False
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        log_id = f"LOG-{travel_type.upper()}-{clean_job_id}"
        db.collection("labor_travel").document(log_id).set({
            "log_id": log_id,
            "job_id": clean_job_id,
            "tech_email": str(tech_email),
            "travel_start": now_iso
        }, merge=True)
        return True
    except Exception as e:
        print(f"Error logging travel start: {e}")
        return False


def record_travel_arrival(job_id: str) -> bool:
    """Logs arrival timestamp in labor_travel and transitions status to In Progress[cite: 2]."""
    clean_job_id = str(job_id)
    update_dispatch_status(clean_job_id, "In Progress")

    if db is None:
        return False
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        log_query = db.collection("labor_travel").where(filter=FieldFilter("job_id", "==", clean_job_id)).stream()
        for doc in log_query:
            doc.reference.update({"travel_end": now_iso})
        return True
    except Exception as e:
        print(f"Error recording travel arrival: {e}")
        return False


def finish_workday_lifecycle(job_id: str, job_type: str) -> str:
    """Determines final ticket status (Pending for VFD certs vs Completed) and updates storage[cite: 2]."""
    clean_job_id = str(job_id)
    is_vfd = "VFD" in str(job_type or "").upper() or job_type == "VFD_STARTUP"
    target_status = "Pending" if is_vfd else "Completed"
    update_dispatch_status(clean_job_id, target_status)
    return target_status


def build_technician_clock(
    job_data: dict,
    tech_email: str,
    on_status_change_callback,
    show_toast_fn
) -> ft.Control:
    """Renders a technician clock component with step-by-step workday progression[cite: 2]."""
    job_id = str(job_data.get("job_id") or job_data.get("tbc_job_number") or "JOB-UNKNOWN")
    tbc_job_num = str(job_data.get("tbc_job_number", "889900XX"))
    job_type = str(job_data.get("job_type", "VFD_STARTUP"))
    current_status = str(job_data.get("completion_status") or "Scheduled")
    
    is_vfd = "VFD" in job_type.upper() or job_type == "VFD_STARTUP"

    # State Machine Mapping[cite: 2]
    if current_status == "Scheduled":
        status_badge_text = "Status: Ready to Start"
        button_label = "Begin Travel"
        button_color = FieldFlowLightTheme.ACCENT_BLUE
        target_next_status = "Traveling"
        is_disabled = False

    elif current_status == "Traveling":
        status_badge_text = "Status: Traveling (Clock Active)"
        button_label = "Stop to Arrive"
        button_color = FieldFlowLightTheme.PRIMARY_GREEN
        target_next_status = "In Progress"
        is_disabled = False

    elif current_status == "In Progress":
        status_badge_text = "Status: Work In Progress (Clock Active)"
        button_label = "Begin Return Travel"
        button_color = FieldFlowLightTheme.ACCENT_BLUE
        target_next_status = "Traveling (Return)"
        is_disabled = False

    elif current_status == "Traveling (Return)":
        status_badge_text = "Status: Return Travel (Clock Active)"
        if is_vfd:
            button_label = "Complete Return & Hold for Registration"
            button_color = FieldFlowLightTheme.SUN_AMBER
            target_next_status = "Pending"
        else:
            button_label = "Complete & Close Job"
            button_color = FieldFlowLightTheme.PRIMARY_GREEN
            target_next_status = "Completed"
        is_disabled = False

    elif current_status == "Pending":
        status_badge_text = "Status: Registration Hold (Pending Review)"
        button_label = "Job Pending Registration Review"
        button_color = FieldFlowLightTheme.SUN_AMBER
        target_next_status = "Pending"
        is_disabled = True

    else:  # Completed
        status_badge_text = "Status: Ticket Closed"
        button_label = "Job Closed"
        button_color = FieldFlowLightTheme.PRIMARY_GREEN
        target_next_status = "Completed"
        is_disabled = True

    def handle_clock_click(e):
        nonlocal current_status
        if target_next_status == "Traveling":
            record_travel_start(job_id, tech_email, "Outbound")
            show_toast_fn(f"Outbound Travel Started for Job {tbc_job_num}", kind="info")

        elif target_next_status == "In Progress":
            record_travel_arrival(job_id)
            show_toast_fn("Arrived at Site. Status set to In Progress.", kind="success")

        elif target_next_status == "Traveling (Return)":
            record_travel_start(job_id, tech_email, "Return")
            show_toast_fn("Return Travel Started.", kind="info")

        elif target_next_status == "Pending":
            update_dispatch_status(job_id, "Pending")
            show_toast_fn("Return Travel Completed. Job placed on Registration Hold.", kind="warning")

        elif target_next_status == "Completed":
            finish_workday_lifecycle(job_id, job_type)
            show_toast_fn("Job Completed and Closed.", kind="success")

        job_data["completion_status"] = target_next_status

        if on_status_change_callback:
            on_status_change_callback()

    badge_widget = ft.Text(
        value=status_badge_text,
        size=12,
        weight=ft.FontWeight.BOLD,
        color=FieldFlowLightTheme.TEXT_PRIMARY
    )

    action_button = ft.ElevatedButton(
        text=button_label,
        disabled=is_disabled,
        style=ft.ButtonStyle(
            color="#FFFFFF",
            bgcolor=button_color,
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=ft.padding.symmetric(horizontal=12, vertical=8)
        ),
        height=38,
        on_click=handle_clock_click
    )

    return ft.Column([badge_widget, action_button], spacing=6)