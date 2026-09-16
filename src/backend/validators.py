import re
from typing import Any, Dict, Tuple

FORM_BLUEPRINTS = {
    "VFD_STARTUP": {
        "required_fields": [
            "unit_type",
            "unit_tag_mark",
            "photo_unit_label",
            "photo_motor_tag",
            "wiring_distance_ft",
            "is_reactor_present",
            "drive_tag",
            "photo_drive_label",
            "l1_l2", "l2_l3", "l3_l1",
            "l1_gnd", "l2_gnd", "l3_gnd",
            "t1_t2", "t2_t3", "t3_t1",
            "t1", "t2", "t3",
            "verified_yaskawa_params",
            "software_version",
            "serial_comm_method",
            "bypass_software_num",
            "application_type",
            "field_notes",
            "status",
            "resolution_next_steps",
            "travel_hours",
            "work_hours"
        ],
        "field_types": {
            "unit_type": str,
            "unit_tag_mark": str,
            "photo_unit_label": str,
            "photo_motor_tag": str,
            "wiring_distance_ft": (int, float),
            "is_reactor_present": str,
            "drive_tag": str,
            "photo_drive_label": str,
            "l1_l2": (int, float),
            "l2_l3": (int, float),
            "l3_l1": (int, float),
            "l1_gnd": (int, float),
            "l2_gnd": (int, float),
            "l3_gnd": (int, float),
            "t1_t2": (int, float),
            "t2_t3": (int, float),
            "t3_t1": (int, float),
            "t1": (int, float),
            "t2": (int, float),
            "t3": (int, float),
            "verified_yaskawa_params": str,
            "software_version": str,
            "serial_comm_method": str,
            "bypass_software_num": str,
            "application_type": str,
            "field_notes": str,
            "status": str,
            "resolution_next_steps": str,
            "travel_hours": (int, float),
            "work_hours": (int, float)
        }
    },
    "GENERAL_SERVICE": {
        "required_fields": [
            "work_completed",
            "unit_status"
        ],
        "field_types": {
            "description_of_issue": str,
            "photo_unit_tag": str,
            "addl_photos": str,
            "photo_unit_condition": str,
            "visual_inspection_results": str,
            "electrical_mechanical_checks": str,
            "root_cause_identified": str,
            "recommended_repairs_parts": str,
            "recommended_repairs_labor": str,
            "additional_recommendations": str,
            "work_completed": str,
            "parts_replaced": str,
            "operational_test_results": str,
            "airflow_performance_verification": str,
            "unit_status": str,
            "additional_notes": str,
            "travel_hours": (int, float),
            "work_hours": (int, float)
        }
    }
}


def is_valid_tbc_job_number(job_number: str) -> bool:
    """Enforces the Tom Barrow Company project identity standard."""
    if not job_number:
        return False
    pattern = r"^\d{6}[a-zA-Z]{2}$"
    return bool(re.match(pattern, job_number.strip()))


def validate_inspection_metrics(job_type: str, metrics: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates incoming form payloads against official template blueprints."""
    if not isinstance(metrics, dict):
        return False, "Validation Error: Inspection metrics payload must be a key-value dictionary."

    job_type_upper = job_type.upper() if job_type else ""
    
    if job_type_upper in ["GENERAL_SERVICE", "GENERAL SERVICE", "TROUBLESHOOTING"]:
        job_type_upper = "GENERAL_SERVICE"

    if job_type_upper not in FORM_BLUEPRINTS:
        return True, "Validation Passed: Generic job type."

    blueprint = FORM_BLUEPRINTS[job_type_upper]
    
    # 1. Enforce Required Fields
    for field in blueprint["required_fields"]:
        if field not in metrics or metrics[field] is None or str(metrics[field]).strip() == "":
            return False, f"Missing required field '{field}' for form type '{job_type_upper}'."
        
    # 2. Enforce Field Types when values are provided
    for field, val in metrics.items():
        if field in blueprint["field_types"] and val is not None and val != "":
            expected_type = blueprint["field_types"][field]
            if expected_type == (int, float) and isinstance(val, str):
                try:
                    val = float(val)
                except ValueError:
                    return False, f"Field '{field}' must be numeric, but received string '{val}'."
            elif not isinstance(val, expected_type):
                return False, f"Field '{field}' must be of type {expected_type}, but received {type(val).__name__}."

    return True, "Validation Passed."