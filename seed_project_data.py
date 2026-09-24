"""
seed_project_data.py
Master seeding script populating all 16 relational database tables with 
multiple records. Assembles child records relationally across a 5-tier 
dependency structure to enforce foreign key integrity and prevent data duplication.
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
# TIER 1: BASE PARENT ENTITIES (SINGLE SOURCE OF TRUTH)
# =====================================================================

USERS_DICT = {
    "admin@tombarrow.com": {
        "first_name": "Alice", "last_name": "Admin", "user_phone": "813-555-0400",
        "position": "Service Coordinator", "branch_city": "Tampa", "active_status": "Active", "role": "Admin"
    },
    "tech1@tbcotampaservice.com": {
        "first_name": "Bob", "last_name": "Tech", "user_phone": "813-555-0100",
        "position": "Senior Tech", "branch_city": "Tampa", "active_status": "Active", "role": "Technician"
    },
    "tech2@tbcotampaservice.com": {
        "first_name": "Alex", "last_name": "Tech", "user_phone": "813-555-0200",
        "position": "Field Tech", "branch_city": "Tampa", "active_status": "Active", "role": "Technician"
    },
    "bstapleton@tbco.com": {
        "first_name": "Brad", "last_name": "Stapleton", "user_phone": "813-555-0501",
        "position": "Sales Rep", "branch_city": "Tampa", "active_status": "Active", "role": "Sales"
    }
}

CONTRACTORS_DICT = {
    "BCHM120": {
        "company_name": "BCH Mechanical",
        "trade_specialty": "HVAC / Mechanical Contractor"
    },
    "BAYH088": {
        "company_name": "Bay Area HVAC Solutions",
        "trade_specialty": "Commercial Air Distribution"
    }
}

MANUFACTURERS_DICT = {
    "MFR-YASKAWA": {
        "company_name": "Yaskawa America", "mfr_contact_first_name": "Sarah",
        "mfr_contact_last_name": "Yaskawa", "email": "support@yaskawa.com",
        "phone": "800-555-0222", "website": "https://www.yaskawa.com"
    },
    "MFR-TITUS": {
        "company_name": "Titus HVAC", "mfr_contact_first_name": "John",
        "mfr_contact_last_name": "Titus", "email": "orders@titus-hvac.com",
        "phone": "800-555-0333", "website": "https://www.titus-hvac.com"
    }
}

PARTS_MASTER_DICT = {
    "P-ASCD3-0824": {"manufacturer": "Titus HVAC", "part_description": "Al 3 Cone Dif, LayIn-, 8\", 24X24", "unit_cost": 45.00},
    "P-ASCD3-1024": {"manufacturer": "Titus HVAC", "part_description": "Al 3 Cone Dif, Lay-In, 10\", 24X24", "unit_cost": 52.00},
    "P-630DF-1206": {"manufacturer": "Titus HVAC", "part_description": "Alum Ret Gril, Surf Mnt, w/OBD", "unit_cost": 28.00},
    "ALPF-1212": {"manufacturer": "Titus HVAC", "part_description": "Mounting Frame 12x12", "unit_cost": 15.00}
}


# =====================================================================
# TIER 2: PRIMARY DEPENDENT SPECIFICATIONS
# =====================================================================

CONTACTS_SPECS = [
    {"contact_id": "CONT-1001", "tbco_account_number": "BCHM120", "first_name": "Mike", "last_name": "Castro", "title": "Project Manager", "phone": "813-888-9000", "email": "mcastro@bchmech.com", "is_primary_contact": 1},
    {"contact_id": "CONT-1002", "tbco_account_number": "BAYH088", "first_name": "David", "last_name": "Miller", "title": "Site Superintendent", "phone": "727-555-4321", "email": "dmiller@bayareahvac.com", "is_primary_contact": 1}
]

LOCATIONS_SPECS = [
    {"site_name": "BCH Mechanical Tampa Site", "street_address_1": "7004 Benjamin Rd, Suite 106", "street_address_2": "", "city": "Tampa", "state": "FL", "postal_code": "33634", "country": "US", "site_contact_id": "CONT-1001"},
    {"site_name": "Bay Area HVAC Clearwater Facility", "street_address_1": "14200 US Hwy 19 N", "street_address_2": "Building B", "city": "Clearwater", "state": "FL", "postal_code": "33764", "country": "US", "site_contact_id": "CONT-1002"}
]

TRUCKS_SPECS = [
    {"truck_id": "TRK-101", "truck_number": "Truck #101 (Tampa)", "assigned_tech_email": "tech1@tbcotampaservice.com"},
    {"truck_id": "TRK-102", "truck_number": "Truck #102 (Tampa)", "assigned_tech_email": "tech2@tbcotampaservice.com"}
]


# =====================================================================
# TIER 3: PROJECTS & INTAKE LEDGER SPECIFICATIONS
# =====================================================================

PROJECT_SPECS = [
    {
        "tbc_job_number": "194833TY",
        "site_name": "BCH Mechanical Tampa Site",
        "tbco_account_number": "BCHM120",
        "pm_contact_id": "CONT-1001",
        "sales_rep_email": "bstapleton@tbco.com",
        "project_name": "Benjamin Rd Air Distribution & Startup",
        "team_code": "TY", "po_number": "PO-99201", "drive_id": "FLD-DRIVE-194833TY",
        "stage": "Active", "photo_url": "https://storage.googleapis.com/tbc-photos/194833.jpg"
    },
    {
        "tbc_job_number": "202611CW",
        "site_name": "Bay Area HVAC Clearwater Facility",
        "tbco_account_number": "BAYH088",
        "pm_contact_id": "CONT-1002",
        "sales_rep_email": "bstapleton@tbco.com",
        "project_name": "Clearwater VFD Retrofit & Inspection",
        "team_code": "CW", "po_number": "PO-88104", "drive_id": "FLD-DRIVE-202611CW",
        "stage": "Active", "photo_url": "https://storage.googleapis.com/tbc-photos/202611.jpg"
    }
]

INTAKE_SPECS = [
    {
        "request_id": "REQ-194833TY",
        "tbc_job_number": "194833TY",
        "site_name": "BCH Mechanical Tampa Site",
        "tbco_account_number": "BCHM120",
        "contact_id": "CONT-1001",
        "sales_rep_email": "bstapleton@tbco.com",
        "team_code": "TY",
        "issue_description": "Grille/Diffuser delivery verification and VFD startup commissioning.",
        "triage_status": "Dispatched", "request_type": "VFD Startup", "submission_timestamp": "2026-09-15T10:00:00Z"
    },
    {
        "request_id": "REQ-202611CW",
        "tbc_job_number": "202611CW",
        "site_name": "Bay Area HVAC Clearwater Facility",
        "tbco_account_number": "BAYH088",
        "contact_id": "CONT-1002",
        "sales_rep_email": "bstapleton@tbco.com",
        "team_code": "CW",
        "issue_description": "Annual VFD preventive maintenance and noise inspection.",
        "triage_status": "Dispatched", "request_type": "Maintenance", "submission_timestamp": "2026-09-18T14:30:00Z"
    }
]


# =====================================================================
# TIER 4: DISPATCHES & ASSETS SPECIFICATIONS
# =====================================================================

DISPATCH_SPECS = [
    {"job_id": "JOB-194833TY", "tbc_job_number": "194833TY", "technician_email": "tech1@tbcotampaservice.com", "scheduled_time": "2026-09-16T08:00:00Z", "status": "Scheduled", "job_type": "VFD Startup", "google_calendar_event_id": "CAL-EVT-9901", "last_mutation_token": "TOK-1002", "report_metrics": '{"status":"Scheduled"}'},
    {"job_id": "JOB-202611CW", "tbc_job_number": "202611CW", "technician_email": "tech2@tbcotampaservice.com", "scheduled_time": "2026-09-19T09:30:00Z", "status": "Scheduled", "job_type": "Maintenance", "google_calendar_event_id": "CAL-EVT-9902", "last_mutation_token": "TOK-1003", "report_metrics": '{"status":"Scheduled"}'}
]

ASSET_SPECS = [
    {"asset_id": "AST-194833TY", "tbc_job_number": "194833TY", "manufacturer_id": "MFR-YASKAWA", "model_number": "Z1000", "serial_number": "SN-194833TY", "equipment_tag": "VFD Drive #1", "installation_date": "2026-01-18", "warranty_expiration_date": "2029-01-18", "operational_status": "Operational"},
    {"asset_id": "AST-202611CW", "tbc_job_number": "202611CW", "manufacturer_id": "MFR-YASKAWA", "model_number": "P1000", "serial_number": "SN-202611CW", "equipment_tag": "VFD Drive #2", "installation_date": "2025-05-10", "warranty_expiration_date": "2028-05-10", "operational_status": "Operational"}
]


# =====================================================================
# TIER 5: DOWNSTREAM FIELD OPERATIONS SPECIFICATIONS
# =====================================================================

TIME_ENTRY_SPECS = [
    {"entry_id": "TIME-001", "job_id": "JOB-194833TY", "entry_type": "Site Work", "start_timestamp": "2026-09-16T08:00:00Z", "end_timestamp": "2026-09-16T11:30:00Z", "duration_hours": 3.5},
    {"entry_id": "TIME-002", "job_id": "JOB-202611CW", "entry_type": "Maintenance", "start_timestamp": "2026-09-19T09:30:00Z", "end_timestamp": "2026-09-19T11:30:00Z", "duration_hours": 2.0}
]

INSPECTION_SPECS = [
    {"report_id": "RPT-1001", "job_id": "JOB-194833TY", "asset_id": "AST-194833TY", "registration_status": "Passed", "inspection_metrics": '{"voltage_l1_l2": 460, "amps_t1": 12.5, "status": "Passed"}'},
    {"report_id": "RPT-1002", "job_id": "JOB-202611CW", "asset_id": "AST-202611CW", "registration_status": "Passed", "inspection_metrics": '{"voltage_l1_l2": 460, "amps_t1": 14.1, "status": "Passed"}'}
]

PARTS_USED_SPECS = [
    {"usage_id": "USE-001", "job_id": "JOB-194833TY", "sku": "P-ASCD3-0824", "qty_used": 4.0, "is_unlisted": 0, "unlisted_description": None, "manual_cost": 0.0, "cost_status": "Approved"},
    {"usage_id": "USE-002", "job_id": "JOB-202611CW", "sku": "P-630DF-1206", "qty_used": 2.0, "is_unlisted": 0, "unlisted_description": None, "manual_cost": 0.0, "cost_status": "Approved"}
]

INVENTORY_SPECS = [
    {"inventory_id": "INV-101", "truck_id": "TRK-101", "sku": "P-ASCD3-0824", "truck_stock_qty": 4, "baseline_quota": 10},
    {"inventory_id": "INV-102", "truck_id": "TRK-101", "sku": "ALPF-1212", "truck_stock_qty": 10, "baseline_quota": 20},
    {"inventory_id": "INV-103", "truck_id": "TRK-102", "sku": "P-630DF-1206", "truck_stock_qty": 6, "baseline_quota": 15}
]

AUDIT_SPECS = [
    {"log_id": "LOG-001", "user_email": "admin@tombarrow.com", "entity_type": "INTAKE", "entity_id": "REQ-194833TY", "timestamp": "2026-09-15T10:05:00Z", "old_value": "Unassigned", "new_value": "Dispatched"},
    {"log_id": "LOG-002", "user_email": "admin@tombarrow.com", "entity_type": "INTAKE", "entity_id": "REQ-202611CW", "timestamp": "2026-09-18T14:35:00Z", "old_value": "Unassigned", "new_value": "Dispatched"}
]


# =====================================================================
# 5. ASSEMBLY & VALIDATION ENGINE
# =====================================================================

def assemble_and_validate_all_datasets():
    """Validates foreign key relations and dynamically assembles all 16 datasets without duplicate hardcoding."""
    logging.info("Assembling and validating datasets relationally...")

    # --- TIER 1 ---
    users_rows = [(email, d["first_name"], d["last_name"], d["user_phone"], d["position"], d["branch_city"], d["active_status"], d["role"]) for email, d in USERS_DICT.items()]
    contractors_rows = [(acct, d["company_name"], d["trade_specialty"]) for acct, d in CONTRACTORS_DICT.items()]
    manufacturers_rows = [(mid, d["company_name"], d["mfr_contact_first_name"], d["mfr_contact_last_name"], d["email"], d["phone"], d["website"]) for mid, d in MANUFACTURERS_DICT.items()]
    parts_master_rows = [(sku, d["manufacturer"], d["part_description"], d["unit_cost"]) for sku, d in PARTS_MASTER_DICT.items()]

    # --- TIER 2 ---
    contacts_lookup = {}
    contacts_rows = []
    for c in CONTACTS_SPECS:
        if c["tbco_account_number"] not in CONTRACTORS_DICT:
            raise KeyError(f"Contact '{c['contact_id']}' referenced invalid contractor '{c['tbco_account_number']}'")
        contacts_lookup[c["contact_id"]] = c
        contacts_rows.append((c["contact_id"], c["tbco_account_number"], c["first_name"], c["last_name"], c["title"], c["phone"], c["email"], c["is_primary_contact"]))

    locations_lookup = {}
    locations_rows = []
    for loc in LOCATIONS_SPECS:
        if loc["site_contact_id"] not in contacts_lookup:
            raise KeyError(f"Location '{loc['site_name']}' referenced invalid contact '{loc['site_contact_id']}'")
        locations_lookup[loc["site_name"]] = loc
        locations_rows.append((loc["site_name"], loc["street_address_1"], loc["street_address_2"], loc["city"], loc["state"], loc["postal_code"], loc["country"], loc["site_contact_id"]))

    trucks_lookup = {}
    trucks_rows = []
    for t in TRUCKS_SPECS:
        if t["assigned_tech_email"] not in USERS_DICT:
            raise KeyError(f"Truck '{t['truck_id']}' referenced invalid user email '{t['assigned_tech_email']}'")
        trucks_lookup[t["truck_id"]] = t
        trucks_rows.append((t["truck_id"], t["truck_number"], t["assigned_tech_email"]))

    # --- TIER 3 ---
    projects_lookup = {}
    projects_rows = []
    for p in PROJECT_SPECS:
        loc = locations_lookup[p["site_name"]]
        contractor = CONTRACTORS_DICT[p["tbco_account_number"]]
        pm = contacts_lookup[p["pm_contact_id"]]
        sales = USERS_DICT[p["sales_rep_email"]]

        row = (
            p["tbc_job_number"], p["site_name"], p["tbco_account_number"], p["pm_contact_id"], p["project_name"],
            contractor["company_name"], loc["street_address_1"], loc["street_address_2"], loc["city"], loc["state"],
            loc["postal_code"], loc["country"], p["sales_rep_email"], sales["user_phone"], p["team_code"],
            pm["first_name"], pm["last_name"], pm["email"], pm["phone"], p["po_number"],
            p["drive_id"], p["stage"], p["photo_url"]
        )
        projects_lookup[p["tbc_job_number"]] = {
            "site_name": p["site_name"],
            "sales_rep_email": p["sales_rep_email"],
            "sales_rep_phone": sales["user_phone"]
        }
        projects_rows.append(row)

    intake_rows = []
    for i in INTAKE_SPECS:
        proj_info = projects_lookup[i["tbc_job_number"]]
        loc = locations_lookup[i["site_name"]]
        contractor = CONTRACTORS_DICT[i["tbco_account_number"]]
        contact = contacts_lookup[i["contact_id"]]
        sales = USERS_DICT[i["sales_rep_email"]]

        row = (
            i["request_id"], i["tbc_job_number"], i["team_code"], i["site_name"], proj_info["site_name"],
            contractor["company_name"], loc["street_address_1"], loc["street_address_2"], loc["city"], loc["state"],
            loc["postal_code"], loc["country"], i["sales_rep_email"], sales["user_phone"], contact["first_name"],
            contact["last_name"], contact["email"], contact["phone"], i["issue_description"], i["triage_status"],
            i["request_type"], i["submission_timestamp"]
        )
        intake_rows.append(row)

    # --- TIER 4 ---
    dispatches_lookup = {}
    dispatches_rows = []
    for d in DISPATCH_SPECS:
        proj_info = projects_lookup[d["tbc_job_number"]]
        if d["technician_email"] not in USERS_DICT:
            raise KeyError(f"Dispatch '{d['job_id']}' referenced invalid tech email '{d['technician_email']}'")

        # DYNAMICALLY DERIVE sales_rep_email from parent Project record (NO HARDCODING!)
        sales_rep_email = proj_info["sales_rep_email"]

        dispatches_lookup[d["job_id"]] = {
            "technician_email": d["technician_email"],
            "tbc_job_number": d["tbc_job_number"]
        }
        dispatches_rows.append((
            d["job_id"], d["tbc_job_number"], d["technician_email"], sales_rep_email,
            d["scheduled_time"], d["status"], d["job_type"], d["google_calendar_event_id"],
            d["last_mutation_token"], d["report_metrics"]
        ))

    assets_lookup = {}
    assets_rows = []
    for a in ASSET_SPECS:
        proj_info = projects_lookup[a["tbc_job_number"]]
        if a["manufacturer_id"] not in MANUFACTURERS_DICT:
            raise KeyError(f"Asset '{a['asset_id']}' referenced invalid manufacturer '{a['manufacturer_id']}'")

        # DYNAMICALLY DERIVE site_name from parent Project record (NO HARDCODING!)
        site_name = proj_info["site_name"]

        assets_lookup[a["asset_id"]] = a
        assets_rows.append((
            a["asset_id"], a["tbc_job_number"], site_name, a["manufacturer_id"],
            a["model_number"], a["serial_number"], a["equipment_tag"], a["installation_date"],
            a["warranty_expiration_date"], a["operational_status"]
        ))

    # --- TIER 5 ---
    time_entries_rows = []
    for te in TIME_ENTRY_SPECS:
        dispatch_info = dispatches_lookup[te["job_id"]]

        # DYNAMICALLY DERIVE tech_email from assigned Dispatch record (NO HARDCODING!)
        tech_email = dispatch_info["technician_email"]

        time_entries_rows.append((
            te["entry_id"], te["job_id"], tech_email, te["entry_type"],
            te["start_timestamp"], te["end_timestamp"], te["duration_hours"]
        ))

    inspections_rows = []
    for insp in INSPECTION_SPECS:
        if insp["job_id"] not in dispatches_lookup:
            raise KeyError(f"Inspection '{insp['report_id']}' referenced invalid dispatch '{insp['job_id']}'")
        if insp["asset_id"] not in assets_lookup:
            raise KeyError(f"Inspection '{insp['report_id']}' referenced invalid asset '{insp['asset_id']}'")

        inspections_rows.append((insp["report_id"], insp["job_id"], insp["asset_id"], insp["registration_status"], insp["inspection_metrics"]))

    parts_used_rows = []
    for pu in PARTS_USED_SPECS:
        if pu["job_id"] not in dispatches_lookup:
            raise KeyError(f"Part Usage '{pu['usage_id']}' referenced invalid dispatch '{pu['job_id']}'")
        if pu["sku"] not in PARTS_MASTER_DICT:
            raise KeyError(f"Part Usage '{pu['usage_id']}' referenced invalid SKU '{pu['sku']}'")

        parts_used_rows.append((pu["usage_id"], pu["job_id"], pu["sku"], pu["qty_used"], pu["is_unlisted"], pu["unlisted_description"], pu["manual_cost"], pu["cost_status"]))

    inventory_rows = []
    for inv in INVENTORY_SPECS:
        if inv["truck_id"] not in trucks_lookup:
            raise KeyError(f"Inventory '{inv['inventory_id']}' referenced invalid truck '{inv['truck_id']}'")
        if inv["sku"] not in PARTS_MASTER_DICT:
            raise KeyError(f"Inventory '{inv['inventory_id']}' referenced invalid SKU '{inv['sku']}'")

        inventory_rows.append((inv["inventory_id"], inv["truck_id"], inv["sku"], inv["truck_stock_qty"], inv["baseline_quota"]))

    audit_rows = []
    for log in AUDIT_SPECS:
        if log["user_email"] not in USERS_DICT:
            raise KeyError(f"Audit log '{log['log_id']}' referenced invalid user email '{log['user_email']}'")

        audit_rows.append((log["log_id"], log["user_email"], log["entity_type"], log["entity_id"], log["timestamp"], log["old_value"], log["new_value"]))

    # Bundle all 16 datasets with explicit column headers
    return [
        ("users", ["user_email", "first_name", "last_name", "user_phone", "position", "branch_city", "active_status", "role"], users_rows),
        ("contractors", ["tbco_account_number", "company_name", "trade_specialty"], contractors_rows),
        ("contacts", ["contact_id", "tbco_account_number", "first_name", "last_name", "title", "phone", "email", "is_primary_contact"], contacts_rows),
        ("locations", ["site_name", "street_address_1", "street_address_2", "city", "state", "postal_code", "country", "site_contact_id"], locations_rows),
        ("trucks", ["truck_id", "truck_number", "assigned_tech_email"], trucks_rows),
        ("manufacturers", ["manufacturer_id", "company_name", "mfr_contact_first_name", "mfr_contact_last_name", "email", "phone", "website"], manufacturers_rows),
        ("parts_master", ["sku", "manufacturer", "part_description", "unit_cost"], parts_master_rows),
        ("projects", ["tbc_job_number", "site_name", "tbco_account_number", "pm_contact_id", "project_name", "contractor_company_name", "street_address_1", "street_address_2", "city", "state", "postal_code", "country", "sales_rep_email", "sales_rep_phone", "team_code", "pm_first_name", "pm_last_name", "pm_email", "pm_phone", "po_number", "drive_id", "stage", "photo_url"], projects_rows),
        ("intake_ledger", ["request_id", "tbc_job_number", "team_code", "site_name", "project_name", "contractor_company_name", "street_address_1", "street_address_2", "city", "state", "postal_code", "country", "sales_rep_email", "sales_rep_phone", "project_site_contact_first_name", "project_site_contact_last_name", "project_site_contact_email", "project_site_contact_phone", "issue_description", "triage_status", "request_type", "submission_timestamp"], intake_rows),
        ("dispatches", ["job_id", "tbc_job_number", "technician_email", "sales_rep_email", "scheduled_time", "status", "job_type", "google_calendar_event_id", "last_mutation_token", "report_metrics"], dispatches_rows),
        ("assets", ["asset_id", "tbc_job_number", "site_name", "manufacturer_id", "model_number", "serial_number", "equipment_tag", "installation_date", "warranty_expiration_date", "operational_status"], assets_rows),
        ("inventory", ["inventory_id", "truck_id", "sku", "truck_stock_qty", "baseline_quota"], inventory_rows),
        ("time_entries", ["entry_id", "job_id", "tech_email", "entry_type", "start_timestamp", "end_timestamp", "duration_hours"], time_entries_rows),
        ("asset_inspections", ["report_id", "job_id", "asset_id", "registration_status", "inspection_metrics"], inspections_rows),
        ("job_parts_used", ["usage_id", "job_id", "sku", "qty_used", "is_unlisted", "unlisted_description", "manual_cost", "cost_status"], parts_used_rows),
        ("audit_log", ["log_id", "user_email", "entity_type", "entity_id", "timestamp", "old_value", "new_value"], audit_rows)
    ]


# =====================================================================
# 6. MASTER SEED EXECUTION & VERIFICATION REPORT
# =====================================================================

def seed_database():
    logging.info("Starting Relational Master Seeding across all 16 datasets...")

    try:
        all_datasets = assemble_and_validate_all_datasets()
    except KeyError as err:
        logging.error(f"❌ Seeding aborted due to broken relational foreign key: {err}")
        return

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
    """Queries both SQLite and Cloud Firestore to print a verification summary."""
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