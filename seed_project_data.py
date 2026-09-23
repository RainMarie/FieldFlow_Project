"""
seed_project_data.py
Master seeding script populating all 16 relational database tables with 
multiple records. Assembles child records relationally from parent dictionaries 
to enforce foreign key integrity and prevent data duplication.
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Register project root in Python's search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

try:
    from src.backend.db_manager import db, local_db
except ImportError as err:
    logging.error(f"Failed to import db_manager module: {err}")
    sys.exit(1)


# =====================================================================
# 1. PRIMARY PARENT ENTITIES (SINGLE SOURCE OF TRUTH)
# =====================================================================

CONTRACTORS_DICT = {
    "BCHM120": {
        "company_name": "BCH Mechanical",
        "trade_specialty": "HVAC / Mechanical Contractor"
    },
    "BAYHVAC88": {
        "company_name": "Bay Area HVAC Solutions",
        "trade_specialty": "Commercial Air Distribution"
    }
}

CONTACTS_DICT = {
    "CONT-1001": {
        "tbco_account_number": "BCHM120",
        "first_name": "Mike",
        "last_name": "Castro",
        "title": "Project Manager",
        "phone": "813-888-9000",
        "email": "mcastro@bchmech.com",
        "is_primary_contact": 1
    },
    "CONT-1002": {
        "tbco_account_number": "BAYHVAC88",
        "first_name": "David",
        "last_name": "Miller",
        "title": "Site Superintendent",
        "phone": "727-555-4321",
        "email": "dmiller@bayareahvac.com",
        "is_primary_contact": 1
    }
}

LOCATIONS_DICT = {
    "BCH Mechanical Tampa Site": {
        "street_address_1": "7004 Benjamin Rd, Suite 106",
        "street_address_2": "",
        "city": "Tampa",
        "state": "FL",
        "postal_code": "33634",
        "country": "US",
        "site_contact_id": "CONT-1001"
    },
    "Bay Area HVAC Clearwater Facility": {
        "street_address_1": "14200 US Hwy 19 N",
        "street_address_2": "Building B",
        "city": "Clearwater",
        "state": "FL",
        "postal_code": "33764",
        "country": "US",
        "site_contact_id": "CONT-1002"
    }
}

USERS_DICT = {
    "admin@tombarrow.com": {
        "first_name": "Alice",
        "last_name": "Admin",
        "user_phone": "813-555-0400",
        "position": "Service Coordinator",
        "branch_city": "Tampa",
        "active_status": "Active",
        "role": "Admin"
    },
    "tech1@tbcotampaservice.com": {
        "first_name": "Bob",
        "last_name": "Tech",
        "user_phone": "813-555-0100",
        "position": "Senior Tech",
        "branch_city": "Tampa",
        "active_status": "Active",
        "role": "Technician"
    },
    "tech2@tbcotampaservice.com": {
        "first_name": "Alex",
        "last_name": "Tech",
        "user_phone": "813-555-0200",
        "position": "Field Tech",
        "branch_city": "Tampa",
        "active_status": "Active",
        "role": "Technician"
    },
    "bstapleton@tbco.com": {
        "first_name": "Brad",
        "last_name": "Stapleton",
        "user_phone": "813-555-0501",
        "position": "Sales Rep",
        "branch_city": "Tampa",
        "active_status": "Active",
        "role": "Sales"
    }
}


# =====================================================================
# 2. CHILD SPECIFICATIONS (FOREIGN KEY REFERENCES)
# =====================================================================

PROJECT_SPECS = [
    {
        "tbc_job_number": "194833TYSX11",
        "site_name": "BCH Mechanical Tampa Site",
        "tbco_account_number": "BCHM120",
        "pm_contact_id": "CONT-1001",
        "sales_rep_email": "bstapleton@tbco.com",
        "project_name": "Benjamin Rd Air Distribution & Startup",
        "team_code": "TY",
        "po_number": "PO-99201",
        "drive_id": "FLD-DRIVE-194833TYSX11",
        "stage": "Active",
        "photo_url": "https://storage.googleapis.com/tbc-photos/194833.jpg"
    },
    {
        "tbc_job_number": "202611CWSX02",
        "site_name": "Bay Area HVAC Clearwater Facility",
        "tbco_account_number": "BAYHVAC88",
        "pm_contact_id": "CONT-1002",
        "sales_rep_email": "bstapleton@tbco.com",
        "project_name": "Clearwater VFD Retrofit & Inspection",
        "team_code": "CW",
        "po_number": "PO-88104",
        "drive_id": "FLD-DRIVE-202611CWSX02",
        "stage": "Active",
        "photo_url": "https://storage.googleapis.com/tbc-photos/202611.jpg"
    }
]

INTAKE_SPECS = [
    {
        "request_id": "REQ-194833TYSX11",
        "tbc_job_number": "194833TYSX11",
        "site_name": "BCH Mechanical Tampa Site",
        "tbco_account_number": "BCHM120",
        "contact_id": "CONT-1001",
        "sales_rep_email": "bstapleton@tbco.com",
        "team_code": "TY",
        "issue_description": "Grille/Diffuser delivery verification and VFD startup commissioning.",
        "triage_status": "Dispatched",
        "request_type": "VFD Startup",
        "submission_timestamp": "2026-09-15T10:00:00Z"
    },
    {
        "request_id": "REQ-202611CWSX02",
        "tbc_job_number": "202611CWSX02",
        "site_name": "Bay Area HVAC Clearwater Facility",
        "tbco_account_number": "BAYHVAC88",
        "contact_id": "CONT-1002",
        "sales_rep_email": "bstapleton@tbco.com",
        "team_code": "CW",
        "issue_description": "Annual VFD preventive maintenance and noise inspection.",
        "triage_status": "Dispatched",
        "request_type": "Maintenance",
        "submission_timestamp": "2026-09-18T14:30:00Z"
    }
]


# =====================================================================
# 3. RELATIONAL ASSEMBLY ENGINE (ERROR DETECTION)
# =====================================================================

def build_projects_relational():
    """Assembles 23-column project records dynamically using parent lookups."""
    projects_rows = []
    for spec in PROJECT_SPECS:
        try:
            loc = LOCATIONS_DICT[spec["site_name"]]
            contractor = CONTRACTORS_DICT[spec["tbco_account_number"]]
            pm = CONTACTS_DICT[spec["pm_contact_id"]]
            sales = USERS_DICT[spec["sales_rep_email"]]
        except KeyError as missing_key:
            logging.error(f"❌ RELATIONAL INTEGRITY ERROR: Project '{spec['tbc_job_number']}' referenced non-existent key: {missing_key}")
            raise Exception(f"Seeding aborted due to missing parent reference: {missing_key}")

        projects_rows.append((
            spec["tbc_job_number"],
            spec["site_name"],
            spec["tbco_account_number"],
            spec["pm_contact_id"],
            spec["project_name"],
            contractor["company_name"],
            loc["street_address_1"],
            loc["street_address_2"],
            loc["city"],
            loc["state"],
            loc["postal_code"],
            loc["country"],
            spec["sales_rep_email"],
            sales["user_phone"],
            spec["team_code"],
            pm["first_name"],
            pm["last_name"],
            pm["email"],
            pm["phone"],
            spec["po_number"],
            spec["drive_id"],
            spec["stage"],
            spec["photo_url"]
        ))
    return projects_rows


def build_intake_ledger_relational():
    """Assembles 22-column intake ledger records dynamically using parent lookups."""
    intake_rows = []
    for spec in INTAKE_SPECS:
        try:
            loc = LOCATIONS_DICT[spec["site_name"]]
            contractor = CONTRACTORS_DICT[spec["tbco_account_number"]]
            contact = CONTACTS_DICT[spec["contact_id"]]
            sales = USERS_DICT[spec["sales_rep_email"]]
        except KeyError as missing_key:
            logging.error(f"❌ RELATIONAL INTEGRITY ERROR: Intake '{spec['request_id']}' referenced non-existent key: {missing_key}")
            raise Exception(f"Seeding aborted due to missing parent reference: {missing_key}")

        intake_rows.append((
            spec["request_id"],
            spec["tbc_job_number"],
            spec["team_code"],
            spec["site_name"],
            spec["project_name"],
            contractor["company_name"],
            loc["street_address_1"],
            loc["street_address_2"],
            loc["city"],
            loc["state"],
            loc["postal_code"],
            loc["country"],
            spec["sales_rep_email"],
            sales["user_phone"],
            contact["first_name"],
            contact["last_name"],
            contact["email"],
            contact["phone"],
            spec["issue_description"],
            spec["triage_status"],
            spec["request_type"],
            spec["submission_timestamp"]
        ))
    return intake_rows


# =====================================================================
# 4. MASTER SEED EXECUTION & VERIFICATION
# =====================================================================

def seed_database():
    logging.info("Starting Relational Master Seeding across all 16 datasets...")

    # Assemble parent tuples
    users_data = [(email, data["first_name"], data["last_name"], data["user_phone"], data["position"], data["branch_city"], data["active_status"], data["role"]) for email, data in USERS_DICT.items()]
    contractors_data = [(acct, data["company_name"], data["trade_specialty"]) for acct, data in CONTRACTORS_DICT.items()]
    contacts_data = [(cid, data["tbco_account_number"], data["first_name"], data["last_name"], data["title"], data["phone"], data["email"], data["is_primary_contact"]) for cid, data in CONTACTS_DICT.items()]
    locations_data = [(site, data["street_address_1"], data["street_address_2"], data["city"], data["state"], data["postal_code"], data["country"], data["site_contact_id"]) for site, data in LOCATIONS_DICT.items()]

    # Relationally assemble child records (validates foreign keys)
    projects_data = build_projects_relational()
    intake_ledger_data = build_intake_ledger_relational()

    # Remaining multi-record datasets
    trucks_data = [
        ("TRK-101", "Truck #101 (Tampa)", "tech1@tbcotampaservice.com"),
        ("TRK-102", "Truck #102 (Tampa)", "tech2@tbcotampaservice.com")
    ]

    manufacturers_data = [
        ("MFR-YASKAWA", "Yaskawa America", "Sarah", "Yaskawa", "support@yaskawa.com", "800-555-0222", "https://www.yaskawa.com"),
        ("MFR-TITUS", "Titus HVAC", "John", "Titus", "orders@titus-hvac.com", "800-555-0333", "https://www.titus-hvac.com")
    ]

    parts_master_data = [
        ("P-ASCD3-0824", "Titus HVAC", "Al 3 Cone Dif, LayIn-, 8\", 24X24", 45.00),
        ("P-ASCD3-1024", "Titus HVAC", "Al 3 Cone Dif, Lay-In, 10\", 24X24", 52.00),
        ("P-630DF-1206", "Titus HVAC", "Alum Ret Gril, Surf Mnt, w/OBD", 28.00),
        ("ALPF-1212", "Titus HVAC", "Mounting Frame 12x12", 15.00)
    ]

    dispatches_data = [
        ("JOB-194833TYSX11", "194833TYSX11", "tech1@tbcotampaservice.com", "bstapleton@tbco.com", "2026-09-16T08:00:00Z", "Scheduled", "VFD Startup", "CAL-EVT-9901", "TOK-1002", '{"status":"Scheduled"}'),
        ("JOB-202611CWSX02", "202611CWSX02", "tech2@tbcotampaservice.com", "bstapleton@tbco.com", "2026-09-19T09:30:00Z", "Scheduled", "Maintenance", "CAL-EVT-9902", "TOK-1003", '{"status":"Scheduled"}')
    ]

    assets_data = [
        ("AST-194833TYSX11", "194833TYSX11", "BCH Mechanical Tampa Site", "MFR-YASKAWA", "Z1000", "SN-194833TY", "VFD Drive #1", "2026-01-18", "2029-01-18", "Operational"),
        ("AST-202611CWSX02", "202611CWSX02", "Bay Area HVAC Clearwater Facility", "MFR-YASKAWA", "P1000", "SN-202611CW", "VFD Drive #2", "2025-05-10", "2028-05-10", "Operational")
    ]

    inventory_data = [
        ("INV-101", "TRK-101", "P-ASCD3-0824", 4, 10),
        ("INV-102", "TRK-101", "ALPF-1212", 10, 20),
        ("INV-103", "TRK-102", "P-630DF-1206", 6, 15)
    ]

    time_entries_data = [
        ("TIME-001", "JOB-194833TYSX11", "tech1@tbcotampaservice.com", "Site Work", "2026-09-16T08:00:00Z", "2026-09-16T11:30:00Z", 3.5),
        ("TIME-002", "JOB-202611CWSX02", "tech2@tbcotampaservice.com", "Maintenance", "2026-09-19T09:30:00Z", "2026-09-19T11:30:00Z", 2.0)
    ]

    asset_inspections_data = [
        ("RPT-1001", "JOB-194833TYSX11", "AST-194833TYSX11", "Passed", '{"voltage_l1_l2": 460, "amps_t1": 12.5, "status": "Passed"}'),
        ("RPT-1002", "JOB-202611CWSX02", "AST-202611CWSX02", "Passed", '{"voltage_l1_l2": 460, "amps_t1": 14.1, "status": "Passed"}')
    ]

    job_parts_used_data = [
        ("USE-001", "JOB-194833TYSX11", "P-ASCD3-0824", 4.0, 0, None, 0.0, "Approved"),
        ("USE-002", "JOB-202611CWSX02", "P-630DF-1206", 2.0, 0, None, 0.0, "Approved")
    ]

    audit_log_data = [
        ("LOG-001", "admin@tombarrow.com", "INTAKE", "REQ-194833TYSX11", "2026-09-15T10:05:00Z", "Unassigned", "Dispatched"),
        ("LOG-002", "admin@tombarrow.com", "INTAKE", "REQ-202611CWSX02", "2026-09-18T14:35:00Z", "Unassigned", "Dispatched")
    ]

    # Master schema definitions
    all_datasets = [
        ("users", ["user_email", "first_name", "last_name", "user_phone", "position", "branch_city", "active_status", "role"], users_data),
        ("contractors", ["tbco_account_number", "company_name", "trade_specialty"], contractors_data),
        ("contacts", ["contact_id", "tbco_account_number", "first_name", "last_name", "title", "phone", "email", "is_primary_contact"], contacts_data),
        ("locations", ["site_name", "street_address_1", "street_address_2", "city", "state", "postal_code", "country", "site_contact_id"], locations_data),
        ("trucks", ["truck_id", "truck_number", "assigned_tech_email"], trucks_data),
        ("manufacturers", ["manufacturer_id", "company_name", "mfr_contact_first_name", "mfr_contact_last_name", "email", "phone", "website"], manufacturers_data),
        ("parts_master", ["sku", "manufacturer", "part_description", "unit_cost"], parts_master_data),
        ("projects", ["tbc_job_number", "site_name", "tbco_account_number", "pm_contact_id", "project_name", "contractor_company_name", "street_address_1", "street_address_2", "city", "state", "postal_code", "country", "sales_rep_email", "sales_rep_phone", "team_code", "pm_first_name", "pm_last_name", "pm_email", "pm_phone", "po_number", "drive_id", "stage", "photo_url"], projects_data),
        ("intake_ledger", ["request_id", "tbc_job_number", "team_code", "site_name", "project_name", "contractor_company_name", "street_address_1", "street_address_2", "city", "state", "postal_code", "country", "sales_rep_email", "sales_rep_phone", "project_site_contact_first_name", "project_site_contact_last_name", "project_site_contact_email", "project_site_contact_phone", "issue_description", "triage_status", "request_type", "submission_timestamp"], intake_ledger_data),
        ("dispatches", ["job_id", "tbc_job_number", "technician_email", "sales_rep_email", "scheduled_time", "status", "job_type", "google_calendar_event_id", "last_mutation_token", "report_metrics"], dispatches_data),
        ("assets", ["asset_id", "tbc_job_number", "site_name", "manufacturer_id", "model_number", "serial_number", "equipment_tag", "installation_date", "warranty_expiration_date", "operational_status"], assets_data),
        ("inventory", ["inventory_id", "truck_id", "sku", "truck_stock_qty", "baseline_quota"], inventory_data),
        ("time_entries", ["entry_id", "job_id", "tech_email", "entry_type", "start_timestamp", "end_timestamp", "duration_hours"], time_entries_data),
        ("asset_inspections", ["report_id", "job_id", "asset_id", "registration_status", "inspection_metrics"], asset_inspections_data),
        ("job_parts_used", ["usage_id", "job_id", "sku", "qty_used", "is_unlisted", "unlisted_description", "manual_cost", "cost_status"], job_parts_used_data),
        ("audit_log", ["log_id", "user_email", "entity_type", "entity_id", "timestamp", "old_value", "new_value"], audit_log_data)
    ]

    # STEP 1: Bulk Insert into SQLite
    logging.info("Executing SQLite bulk inserts across all 16 tables...")
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        for table_name, schema, rows in all_datasets:
            placeholders = ",".join(["?"] * len(schema))
            sql = f"INSERT OR REPLACE INTO {table_name} VALUES ({placeholders})"
            cursor.executemany(sql, rows)
            logging.info(f"SQLite -> {table_name}: Inserted {len(rows)} row(s).")
        conn.commit()

    # STEP 2: Sync to Cloud Firestore
    if db is not None:
        logging.info("Syncing all 16 datasets to Cloud Firestore...")
        for table_name, schema, rows in all_datasets:
            pk_col = schema[0]
            col_ref = db.collection(table_name)
            for row in rows:
                doc_dict = dict(zip(schema, row))
                doc_id = str(doc_dict[pk_col])
                col_ref.document(doc_id).set(doc_dict, merge=True)
            logging.info(f"Firestore -> '{table_name}': Uploaded {len(rows)} document(s).")
    else:
        logging.warning("Cloud Firestore client unavailable. Skipped cloud sync.")

    # STEP 3: Verification Audit Report
    verify_database_counts(all_datasets)


def verify_database_counts(all_datasets):
    """Queries both SQLite and Cloud Firestore to display a verification count report."""
    print("\n" + "=" * 65)
    print("      DATABASE SEEDING VERIFICATION REPORT (ALL 16 TABLES)")
    print("=" * 65)
    print(f"{'TABLE NAME':<22} | {'SQLITE ROWS':<12} | {'FIRESTORE DOCS':<15}")
    print("-" * 65)

    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        for table_name, _, _ in all_datasets:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            sql_count = cursor.fetchone()[0]

            if db is not None:
                try:
                    fs_docs = list(db.collection(table_name).stream())
                    fs_count = len(fs_docs)
                except Exception as err:
                    fs_count = f"Error: {err}"
            else:
                fs_count = "Offline"

            print(f"{table_name:<22} | {sql_count:<12} | {fs_count:<15}")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    seed_database()