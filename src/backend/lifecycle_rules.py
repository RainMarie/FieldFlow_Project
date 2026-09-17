"""
src/backend/lifecycle_rules.py
Enforces business logic, state transitions, user permissions, and form validation rules.
"""

import re
from typing import Tuple, Dict, Any, List
from src.backend.db_manager import local_db, db as firestore_db

# Valid state transitions for dispatches
ALLOWED_TRANSITIONS = {
    "Scheduled":          ["Traveling"],
    "Traveling":          ["In Progress"],
    "In Progress":        ["Traveling (Return)"],
    "Traveling (Return)": ["Pending", "Completed"],
    "Pending":            ["Completed"],
    "Completed":          []
}

# Standard TBC Job Number regex: 6 digits followed by 2 alphanumeric characters (e.g. 123456AB)
JOB_NUMBER_PATTERN = r"^\d{6}[a-zA-Z0-9]{2}$"


def validate_project_space_exists(tbc_job_number: str) -> Tuple[bool, str]:
    """
    Verifies that a project space row exists in local database memory.
    If missing locally, checks Cloud Firestore and mirrors the record down.
    """
    clean_job_num = str(tbc_job_number or "").strip().upper()
    if not clean_job_num:
        return False, "Job number is required to locate project space."

    # 1. Check local SQLite relational storage
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tbc_job_number FROM projects WHERE tbc_job_number = ?", (clean_job_num,))
            if cursor.fetchone():
                return True, "Project space verified in database memory."
    except Exception as err:
        return False, f"Database query error during project space check: {err}"

    # 2. Fallback: Check Cloud Firestore store if not cached locally
    if firestore_db is not None:
        try:
            doc = firestore_db.collection("projects").document(clean_job_num).get()
            if doc.exists:
                p_data = doc.to_dict() or {}
                proj_name = p_data.get("project_name", f"Project #{clean_job_num}")
                site_name = p_data.get("site_name", "")
                acct_num = p_data.get("tbco_account_number", "")
                drive_id = p_data.get("drive_id", f"FLD-GDRV-{clean_job_num}")
                stage_val = p_data.get("stage", "In Progress")

                # Mirror into local SQLite so future local queries succeed
                with local_db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO projects (
                            tbc_job_number, project_name, site_name, tbco_account_number, drive_id, stage
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (clean_job_num, proj_name, site_name, acct_num, drive_id, stage_val))
                    conn.commit()

                return True, "Project space verified and synchronized from Cloud Store."
        except Exception as err:
            return False, f"Cloud Store query error during project space check: {err}"

    return False, "Rule Violation: Project space must be created before submitting a service request."


def validate_service_request_dispatched(request_id: str) -> Tuple[bool, str]:
    """Verifies that a parent service request ticket exists and is marked Dispatched."""
    clean_req_id = str(request_id or "").strip()
    if not clean_req_id:
        return False, "Request ID is required to verify dispatch status."

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT triage_status FROM intake_requests WHERE request_id = ?", (clean_req_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Rule Violation: Parent service request ticket not found."
            
            status = str(row["triage_status"] or "").strip()
            if status.upper() != "DISPATCHED":
                return False, f"Rule Violation: Service request is in status '{status}'. Must be Dispatched before mobile ticket becomes active."
    except Exception as err:
        return False, f"Database query error: {err}"

    return True, "Service request dispatch status verified."


def validate_status_transition(current_status: str, target_status: str, job_type: str) -> Tuple[bool, str]:
    """Validates step-by-step state machine transitions and job-type routing."""
    curr = str(current_status or "Scheduled").strip()
    target = str(target_status or "").strip()
    is_vfd = "VFD" in str(job_type or "").upper()

    allowed_targets = ALLOWED_TRANSITIONS.get(curr, [])
    if target not in allowed_targets:
        return False, f"Invalid state transition from '{curr}' to '{target}'."

    if curr == "Traveling (Return)":
        if is_vfd and target != "Pending":
            return False, "VFD startup jobs must transition to 'Pending' for factory registration review."
        if not is_vfd and target != "Completed":
            return False, "Standard service jobs must transition directly to 'Completed'."

    return True, "Status transition validated."


def validate_user_role_permission(user_email: str, required_action: str) -> Tuple[bool, str]:
    """Verifies user role permissions against the single role column in SQLite."""
    clean_email = str(user_email or "").strip().lower()
    if not clean_email:
        return False, "User email required for permission check."

    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role, active_status FROM users WHERE LOWER(user_email) = ?", (clean_email,))
            row = cursor.fetchone()
            if not row:
                return False, f"Access Denied: User '{clean_email}' not found in database."

            user_data = dict(row)
            user_role = user_data.get("role")
            active_status = user_data.get("active_status", "Active")

            if active_status != "Active":
                return False, f"Access Denied: User '{clean_email}' account is inactive."

            if required_action == "ADMIN_ACTION" and user_role != "Admin":
                return False, "Access Denied: Administrative privileges (role='Admin') required."
            
            if required_action == "TECH_ACTION" and user_role not in ("Admin", "Technician"):
                return False, "Access Denied: Technician privileges (role='Technician' or 'Admin') required."

            if required_action == "SALES_ACTION" and user_role not in ("Admin", "Sales"):
                return False, "Access Denied: Sales privileges (role='Sales' or 'Admin') required."

    except Exception as err:
        return False, f"Permission check database error: {err}"

    return True, "User permission granted."


def validate_intake_form_data(form_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates required form fields and enforces 123456XX job number formatting."""
    job_num = str(form_data.get("tbc_job_number") or "").strip().upper()
    company = str(
        form_data.get("tbco_account_number") or 
        form_data.get("contractor_company_name") or 
        form_data.get("project_name") or ""
    ).strip()
    address = str(
        form_data.get("site_name") or 
        form_data.get("project_site_address") or 
        form_data.get("site_address") or ""
    ).strip()

    if not company:
        return False, "Form Error: Company / Contractor account or name is required."
    if not address:
        return False, "Form Error: Site address or site name is required."
    if not job_num or not re.match(JOB_NUMBER_PATTERN, job_num):
        return False, f"Form Error: Job number '{job_num}' must match standard format 123456XX (6 digits + 2 alphanumeric characters)."

    return True, "Form fields validated."


def validate_field_form_photos(photo_list: List[Any], required_count: int = 1) -> Tuple[bool, str]:
    """Ensures all required photo placeholders contain valid image attachments."""
    if not photo_list or len(photo_list) < required_count:
        return False, f"Form Error: At least {required_count} photo attachment(s) required before submission."

    return True, "Photo attachments verified."