"""
src/backend/search_engine.py
Dedicated query execution engine for Admin Portal and Mobile Suite application search views.
"""

import logging
from typing import Any, Dict, List
from src.backend.db_manager import local_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def search_admin_portal(search_term: str) -> List[Dict[str, Any]]:
    """
    Executes a multi-table search across Projects, Contractors, Users, and Intake Requests.
    Concatenates first_name and last_name for user lookups.
    """
    clean_term = str(search_term or "").strip().lower()
    if not clean_term:
        return []

    pattern = f"%{clean_term}%"
    results = []
    
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 'Project' AS category, p.tbc_job_number AS key_id, COALESCE(l.site_name, p.site_name) AS detail 
                FROM projects p
                LEFT JOIN locations l ON p.site_name = l.site_name
                WHERE LOWER(p.tbc_job_number) LIKE ? OR LOWER(l.site_name) LIKE ? OR LOWER(p.site_name) LIKE ?
                
                UNION ALL
                
                SELECT 'Contractor' AS category, c.tbco_account_number AS key_id, c.company_name AS detail 
                FROM contractors c
                WHERE LOWER(c.tbco_account_number) LIKE ? OR LOWER(c.company_name) LIKE ?
                
                UNION ALL
                
                SELECT 'User' AS category, u.user_email AS key_id, (u.first_name || ' ' || u.last_name || ' (' || u.role || ')') AS detail 
                FROM users u
                WHERE LOWER(u.user_email) LIKE ? OR LOWER(u.first_name || ' ' || u.last_name) LIKE ?
                
                UNION ALL
                
                SELECT 'Intake Ticket' AS category, i.request_id AS key_id, i.tbc_job_number || ' - ' || i.issue_description AS detail 
                FROM intake_requests i
                WHERE LOWER(i.request_id) LIKE ? OR LOWER(i.issue_description) LIKE ?
            """, (pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern, pattern))
            
            for row in cursor.fetchall():
                results.append(dict(row))

    except Exception as err:
        logging.error(f"Error executing admin portal search for '{search_term}': {err}")
            
    return results


def search_mobile_portal(search_term: str, tech_email: str) -> List[Dict[str, Any]]:
    """
    Executes a technician-scoped search across Dispatches, Equipment Assets, and Parts Catalog.
    """
    clean_term = str(search_term or "").strip().lower()
    clean_tech = str(tech_email or "").strip().lower()
    if not clean_term:
        return []

    pattern = f"%{clean_term}%"
    results = []
    
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 'Assigned Dispatch' AS category, d.job_id AS key_id, d.tbc_job_number || ' - ' || p.site_name AS detail
                FROM dispatches d
                JOIN projects p ON d.tbc_job_number = p.tbc_job_number
                WHERE LOWER(d.technician_email) = ? AND (LOWER(d.tbc_job_number) LIKE ? OR LOWER(p.site_name) LIKE ?)
                
                UNION ALL
                
                SELECT 'Job Asset' AS category, a.asset_id AS key_id, a.equipment_tag || ' | SN: ' || a.serial_number AS detail
                FROM assets a
                WHERE LOWER(a.equipment_tag) LIKE ? OR LOWER(a.serial_number) LIKE ? OR LOWER(a.model_number) LIKE ?
                
                UNION ALL
                
                SELECT 'Part Catalog' AS category, pm.sku AS key_id, pm.part_description || ' ($' || pm.unit_cost || ')' AS detail
                FROM parts_master pm
                WHERE LOWER(pm.sku) LIKE ? OR LOWER(pm.part_description) LIKE ?
            """, (clean_tech, pattern, pattern, pattern, pattern, pattern, pattern, pattern))
            
            for row in cursor.fetchall():
                results.append(dict(row))

    except Exception as err:
        logging.error(f"Error executing mobile portal search for '{search_term}': {err}")
            
    return results