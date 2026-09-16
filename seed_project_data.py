# seed_database.py Pseudocode Outline

import os, sys, json, logging
from datetime import datetime, timezone
from src.backend.db_manager import local_db, db as firestore_db

def seed_database():
    logging.info("Starting Complete 16-Table Master Seeding...")

    # 1. USERS (Admin, Technician, Sales)
    users_data = [
        ("admin@tombarrow.com", "Alice", "Admin", "813-555-0400", "Service Coordinator", "Tampa", "Active", "Admin"),
        ("tech1@tbcotampaservice.com", "Bob", "Tech", "813-555-0100", "Senior Tech", "Tampa", "Active", "Technician"),
        ("tech2@tbcotampaservice.com", "Alex", "Tech", "813-555-0200", "Field Tech", "Tampa", "Active", "Technician"),
        ("bstapleton@tbco.com", "Brad", "Stapleton", "813-555-0501", "Sales Rep", "Tampa", "Active", "Sales")
    ]

    # 2. CONTRACTORS (From PO: BCH Mechanical)
    contractors_data = [
        ("CON-BCHM120", "BCH Mechanical", "HVAC / Mechanical Contractor")
    ]

    # 3. CONTACTS
    contacts_data = [
        ("CONT-1001", "CON-BCHM120", "Mike", "Castro", "Project Manager", "813-888-9000", "mcastro@bchmech.com", 1)
    ]

    # 4. LOCATIONS
    locations_data = [
        ("BCH Mechanical Tampa Site", "7004 Benjamin Rd, Suite 106", "", "Tampa", "FL", "33634", "US", "CONT-1001")
    ]

    # 5. TRUCKS
    trucks_data = [
        ("TRK-101", "Truck #101 (Tampa Service)", "tech1@tbcotampaservice.com"),
        ("TRK-102", "Truck #102 (Tampa Service)", "tech2@tbcotampaservice.com")
    ]

    # 6. MANUFACTURERS
    manufacturers_data = [
        ("MFR-YASKAWA", "Yaskawa America", "Sarah", "Yaskawa", "support@yaskawa.com", "800-555-0222", "https://www.yaskawa.com"),
        ("MFR-TITUS", "Titus HVAC", "John", "Titus", "orders@titus-hvac.com", "800-555-0333", "https://www.titus-hvac.com")
    ]

    # 7. PARTS MASTER (Real TBCo SKUs from packing list)
    parts_master_data = [
        ("P-ASCD3-0824", "Titus HVAC", "Al 3 Cone Dif, LayIn-, 8\", 24X24", 45.00),
        ("P-ASCD3-1024", "Titus HVAC", "Al 3 Cone Dif, Lay-In, 10\", 24X24", 52.00),
        ("P-ASCD3-0624", "Titus HVAC", "Al 3 Cone Dif, LayIn-, 6\", 24X24", 38.00),
        ("P-630DF-1206", "Titus HVAC", "Alum Ret Gril, Surf Mnt, w/OBD", 28.00),
        ("P-630F-1212",  "Titus HVAC", "Al Ret Gril, Surf Mnt, w/o OBD", 22.00),
        ("ALPF-1212",    "Titus HVAC", "Mounting Frame 12x12", 15.00),
        ("ALPF-2424",    "Titus HVAC", "Mounting Frame 24x24", 25.00)
    ]

    # 8. PROJECTS (Real Job: 194833TYSX11)
    projects_data = [
        ("194833TYSX11", "BCH Mechanical Tampa Site", "CON-BCHM120", "CONT-1001", "Benjamin Rd Air Distribution & Startup", "FLD-DRIVE-194833TYSX11", "Active")
    ]

    # 9. INTAKE REQUESTS (Full 24 Columns)
    intake_data = [
        (
            "REQ-194833TYSX11", "194833TYSX11", "TY", "BCH Mechanical Tampa Site", "Benjamin Rd Air Distribution & Startup",
            "BCH Mechanical", "7004 Benjamin Rd, Suite 106", "", "Tampa", "FL", "33634", "US",
            "Brad", "Stapleton", "bstapleton@tbco.com", "813-555-0501",
            "Mike", "Castro", "mcastro@bchmech.com", "813-888-9000",
            "Grille/Diffuser delivery verification and VFD startup commissioning.", "Dispatched", "VFD Startup", "2026-09-15T10:00:00Z"
        )
    ]

    # 10. DISPATCHES
    dispatches_data = [
        ("JOB-194833TYSX11", "194833TYSX11", "tech1@tbcotampaservice.com", "bstapleton@tbco.com", "2026-09-16", "Scheduled", "VFD Startup", None, None, '{"status":"Scheduled"}')
    ]

    # 11. ASSETS
    assets_data = [
        ("AST-194833TYSX11", "194833TYSX11", "BCH Mechanical Tampa Site", "MFR-YASKAWA", "Z1000", "SN-194833TY", "VFD Drive #1", "2026-01-18", "2029-01-18", "Operational")
    ]

    # 12. INVENTORY
    inventory_data = [
        ("INV-101", "TRK-101", "P-ASCD3-0824", 4, 10),
        ("INV-102", "TRK-101", "ALPF-1212", 10, 20)
    ]

    # 13. TIME ENTRIES
    time_entries_data = [
        ("TIME-001", "JOB-194833TYSX11", "tech1@tbcotampaservice.com", "Site Work", "2026-09-16T08:00:00Z", "2026-09-16T11:30:00Z", 3.5)
    ]

    # 14. ASSET INSPECTIONS
    asset_inspections_data = [
        ("RPT-1001", "JOB-194833TYSX11", "AST-194833TYSX11", "Passed", '{"voltage_l1_l2": 460, "amps_t1": 12.5, "status": "Passed"}')
    ]

    # 15. JOB PARTS USED
    job_parts_used_data = [
        ("USE-001", "JOB-194833TYSX11", "P-ASCD3-0824", 4.0, 0, None, 0.0, "Approved")
    ]

    # 16. AUDIT LOG
    audit_log_data = [
        ("LOG-001", "admin@tombarrow.com", "INTAKE", "REQ-194833TYSX11", "2026-09-15T10:05:00Z", "Unassigned", "Dispatched")
    ]

    # EXECUTE BULK INSERTS INTO SQLITE IN TOPOLOGICAL ORDER
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,?,?)", users_data)
        cursor.executemany("INSERT OR REPLACE INTO contractors VALUES (?,?,?)", contractors_data)
        cursor.executemany("INSERT OR REPLACE INTO contacts VALUES (?,?,?,?,?,?,?,?)", contacts_data)
        cursor.executemany("INSERT OR REPLACE INTO locations VALUES (?,?,?,?,?,?,?,?)", locations_data)
        cursor.executemany("INSERT OR REPLACE INTO trucks VALUES (?,?,?)", trucks_data)
        cursor.executemany("INSERT OR REPLACE INTO manufacturers VALUES (?,?,?,?,?,?,?)", manufacturers_data)
        cursor.executemany("INSERT OR REPLACE INTO parts_master VALUES (?,?,?,?)", parts_master_data)
        cursor.executemany("INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?,?,?)", projects_data)
        cursor.executemany("INSERT OR REPLACE INTO intake_requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", intake_data)
        cursor.executemany("INSERT OR REPLACE INTO dispatches VALUES (?,?,?,?,?,?,?,?,?,?)", dispatches_data)
        cursor.executemany("INSERT OR REPLACE INTO assets VALUES (?,?,?,?,?,?,?,?,?,?)", assets_data)
        cursor.executemany("INSERT OR REPLACE INTO inventory VALUES (?,?,?,?,?)", inventory_data)
        cursor.executemany("INSERT OR REPLACE INTO time_entries VALUES (?,?,?,?,?,?,?)", time_entries_data)
        cursor.executemany("INSERT OR REPLACE INTO asset_inspections VALUES (?,?,?,?,?)", asset_inspections_data)
        cursor.executemany("INSERT OR REPLACE INTO job_parts_used VALUES (?,?,?,?,?,?,?,?)", job_parts_used_data)
        cursor.executemany("INSERT OR REPLACE INTO audit_log VALUES (?,?,?,?,?,?,?)", audit_log_data)
        conn.commit()

    # SYNC TO CLOUD FIRESTORE
    if firestore_db is not None:
        # Sync users, contractors, locations, projects, intake_requests, dispatches, assets, etc.
        ...

    logging.info("Master Seeding Complete across all 16 tables!")

if __name__ == "__main__":
    seed_database()