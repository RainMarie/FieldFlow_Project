"""
src/backend/db_manager.py
Database Manager providing Cloud-First Firebase Firestore synchronization,
offline local SQLite mirroring, and cascading upserts for parent entities.
"""

import os
import json
import sqlite3
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

try:
    from cryptography.fernet import Fernet
except ImportError:
    raise ImportError("Dependency Missing: Please execute 'pip install cryptography'")

from src.backend.validators import is_valid_tbc_job_number, validate_inspection_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
KEY_PATH = os.path.join(ROOT_DIR, "firebase-key.json")

db = None


class WebSafeCredentialManager:
    """Secures master cloud credentials using Keyring or local encrypted vault."""
    def __init__(self, vault_path: str = "local_vault.enc", secret_key_path: str = ".vault_key"):
        self.vault_path = os.path.join(CURRENT_DIR, vault_path)
        self.secret_key_path = os.path.join(CURRENT_DIR, secret_key_path)
        self.fernet = self._init_cipher()

    def _init_cipher(self) -> Fernet:
        if not os.path.exists(self.secret_key_path):
            key = Fernet.generate_key()
            with open(self.secret_key_path, "wb") as f:
                f.write(key)
        else:
            with open(self.secret_key_path, "rb") as f:
                key = f.read()
        return Fernet(key)

    def _read_vault(self) -> Dict[str, str]:
        if not os.path.exists(self.vault_path):
            return {}
        try:
            with open(self.vault_path, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode("utf-8"))
        except Exception:
            logging.error("Failed to decrypt local credential vault.")
            return {}

    def _write_vault(self, data: Dict[str, str]):
        serialized = json.dumps(data).encode("utf-8")
        encrypted_data = self.fernet.encrypt(serialized)
        with open(self.vault_path, "wb") as f:
            f.write(encrypted_data)

    def set_credential(self, service: str, username: str, secret: str):
        if HAS_KEYRING:
            try:
                keyring.set_password(service, username, secret)
                return
            except Exception:
                pass
        
        vault = self._read_vault()
        vault[f"{service}:{username}"] = secret
        self._write_vault(vault)

    def get_credential(self, service: str, username: str) -> Optional[str]:
        if HAS_KEYRING:
            try:
                secret = keyring.get_password(service, username)
                if secret:
                    return secret
            except Exception:
                pass
        
        vault = self._read_vault()
        return vault.get(f"{service}:{username}")


class LocalDatabaseManager:
    """Manages the local SQLite relational layer in WAL mode across 16 normalized schemas."""
    def __init__(self, db_path: str = "tbc_local.db"):
        self.db_path = os.path.join(CURRENT_DIR, db_path)
        self.init_sqlite_schema()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_sqlite_schema(self):
        """Initializes all 16 normalized schemas sequentially."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")

            # 1. LOCATIONS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    site_name TEXT PRIMARY KEY,
                    street_address_1 TEXT,
                    street_address_2 TEXT,
                    city TEXT,
                    state TEXT,
                    postal_code TEXT,
                    country TEXT DEFAULT 'US',
                    site_contact_id TEXT,
                    FOREIGN KEY(site_contact_id) REFERENCES contacts(contact_id) ON DELETE SET NULL
                );
            """)

            # 2. CONTRACTORS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contractors (
                    tbco_account_number TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    trade_specialty TEXT
                );
            """)

            # 3. USERS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_email TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    user_phone TEXT,
                    position TEXT,
                    branch_city TEXT,
                    active_status TEXT DEFAULT 'Active',
                    role TEXT NOT NULL DEFAULT 'Sales' CHECK(role IN ('Admin', 'Technician', 'Sales'))
                );
            """)

            # 4. CONTACTS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    contact_id TEXT PRIMARY KEY,
                    tbco_account_number TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    title TEXT,
                    phone TEXT,
                    email TEXT NOT NULL,
                    is_primary_contact INTEGER DEFAULT 0,
                    FOREIGN KEY(tbco_account_number) REFERENCES contractors(tbco_account_number) ON UPDATE CASCADE ON DELETE CASCADE
                );
            """)

            # 5. TRUCKS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trucks (
                    truck_id TEXT PRIMARY KEY,
                    truck_number TEXT NOT NULL,
                    assigned_tech_email TEXT,
                    FOREIGN KEY(assigned_tech_email) REFERENCES users(user_email) ON DELETE SET NULL
                );
            """)

            # 6. MANUFACTURERS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS manufacturers (
                    manufacturer_id TEXT PRIMARY KEY,
                    company_name TEXT UNIQUE NOT NULL,
                    mfr_contact_first_name TEXT,
                    mfr_contact_last_name TEXT,
                    email TEXT,
                    phone TEXT,
                    website TEXT
                );
            """)

            # 7. PARTS MASTER
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parts_master (
                    sku TEXT PRIMARY KEY,
                    manufacturer TEXT,
                    part_description TEXT NOT NULL,
                    unit_cost REAL DEFAULT 0.0
                );
            """)

            # 8. PROJECTS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    tbc_job_number TEXT PRIMARY KEY,
                    site_name TEXT,
                    tbco_account_number TEXT,
                    pm_contact_id TEXT,
                    project_name TEXT,
                    drive_id TEXT,
                    stage TEXT DEFAULT 'Active',
                    FOREIGN KEY(site_name) REFERENCES locations(site_name) ON UPDATE CASCADE ON DELETE SET NULL,
                    FOREIGN KEY(tbco_account_number) REFERENCES contractors(tbco_account_number) ON UPDATE CASCADE ON DELETE SET NULL,
                    FOREIGN KEY(pm_contact_id) REFERENCES contacts(contact_id) ON DELETE SET NULL
                );
            """)

            # 9. INTAKE REQUESTS (NORMALIZED SCHEMA: SALES REP FK ONLY)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intake_requests (
                    request_id TEXT PRIMARY KEY,
                    tbc_job_number TEXT,
                    team_code TEXT,
                    site_name TEXT,
                    project_name TEXT,
                    contractor_company_name TEXT,
                    street_address_1 TEXT,
                    street_address_2 TEXT,
                    city TEXT,
                    state TEXT,
                    postal_code TEXT,
                    country TEXT DEFAULT 'US',
                    sales_rep_email TEXT,
                    sales_rep_phone TEXT,
                    project_site_contact_first_name TEXT,
                    project_site_contact_last_name TEXT,
                    project_site_contact_email TEXT,
                    project_site_contact_phone TEXT,
                    issue_description TEXT,
                    triage_status TEXT DEFAULT 'Unassigned',
                    request_type TEXT,
                    submission_timestamp TEXT NOT NULL,
                    FOREIGN KEY(tbc_job_number) REFERENCES projects(tbc_job_number) ON DELETE SET NULL,
                    FOREIGN KEY(site_name) REFERENCES locations(site_name) ON DELETE SET NULL,
                    FOREIGN KEY(sales_rep_email) REFERENCES users(user_email) ON DELETE SET NULL
                );
            """)

            # 10. DISPATCHES
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dispatches (
                    job_id TEXT PRIMARY KEY,
                    tbc_job_number TEXT NOT NULL,
                    technician_email TEXT,
                    sales_rep_email TEXT,
                    scheduled_time TEXT,
                    status TEXT DEFAULT 'Scheduled',
                    job_type TEXT,
                    google_calendar_event_id TEXT,
                    last_mutation_token TEXT,
                    report_metrics TEXT,
                    FOREIGN KEY(tbc_job_number) REFERENCES projects(tbc_job_number) ON DELETE CASCADE,
                    FOREIGN KEY(technician_email) REFERENCES users(user_email) ON DELETE SET NULL,
                    FOREIGN KEY(sales_rep_email) REFERENCES users(user_email) ON DELETE SET NULL
                );
            """)

            # 11. ASSETS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assets (
                    asset_id TEXT PRIMARY KEY,
                    tbc_job_number TEXT,
                    site_name TEXT NOT NULL,
                    manufacturer_id TEXT,
                    model_number TEXT,
                    serial_number TEXT,
                    equipment_tag TEXT,
                    installation_date TEXT,
                    warranty_expiration_date TEXT,
                    operational_status TEXT DEFAULT 'Operational',
                    FOREIGN KEY(tbc_job_number) REFERENCES projects(tbc_job_number) ON DELETE SET NULL,
                    FOREIGN KEY(site_name) REFERENCES locations(site_name) ON UPDATE CASCADE ON DELETE CASCADE,
                    FOREIGN KEY(manufacturer_id) REFERENCES manufacturers(manufacturer_id) ON DELETE SET NULL
                );
            """)

            # 12. INVENTORY
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory (
                    inventory_id TEXT PRIMARY KEY,
                    truck_id TEXT,
                    sku TEXT NOT NULL,
                    truck_stock_qty INTEGER DEFAULT 0,
                    baseline_quota INTEGER DEFAULT 10,
                    FOREIGN KEY(truck_id) REFERENCES trucks(truck_id) ON DELETE CASCADE,
                    FOREIGN KEY(sku) REFERENCES parts_master(sku) ON DELETE CASCADE
                );
            """)

            # 13. TIME ENTRIES
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS time_entries (
                    entry_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    tech_email TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    start_timestamp TEXT NOT NULL,
                    end_timestamp TEXT,
                    duration_hours REAL DEFAULT 0.0,
                    FOREIGN KEY(job_id) REFERENCES dispatches(job_id) ON DELETE CASCADE,
                    FOREIGN KEY(tech_email) REFERENCES users(user_email) ON DELETE CASCADE
                );
            """)

            # 14. ASSET INSPECTIONS
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS asset_inspections (
                    report_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    registration_status TEXT,
                    inspection_metrics TEXT,
                    FOREIGN KEY(job_id) REFERENCES dispatches(job_id) ON DELETE CASCADE,
                    FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
                );
            """)

            # 15. JOB PARTS USED
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_parts_used (
                    usage_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    sku TEXT,
                    qty_used REAL DEFAULT 1.0,
                    is_unlisted INTEGER DEFAULT 0,
                    unlisted_description TEXT,
                    manual_cost REAL DEFAULT 0.0,
                    cost_status TEXT DEFAULT 'Pending',
                    FOREIGN KEY(job_id) REFERENCES dispatches(job_id) ON DELETE CASCADE,
                    FOREIGN KEY(sku) REFERENCES parts_master(sku) ON DELETE SET NULL
                );
            """)

            # 16. AUDIT LOG
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id TEXT PRIMARY KEY,
                    user_email TEXT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    FOREIGN KEY(user_email) REFERENCES users(user_email) ON DELETE SET NULL
                );
            """)

            # Performance Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_loc_site ON locations(site_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contractors_acct ON contractors(tbco_account_number);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_tag ON assets(equipment_tag);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_sn ON assets(serial_number);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parts_sku ON parts_master(sku);")

            conn.commit()
        logging.info("🎉 Local SQLite Database Engine initialized across 16 relational tables.")


cred_manager = WebSafeCredentialManager()

if os.path.exists(KEY_PATH):
    try:
        with open(KEY_PATH, "r") as f:
            raw_json_data = f.read()
        cred_manager.set_credential("Firebase", "master_service_account", raw_json_data)
    except Exception as e:
        logging.error(f"Credential migration failed: {e}")

firebase_config_raw = cred_manager.get_credential("Firebase", "master_service_account")

if firebase_config_raw and firestore is not None:
    try:
        config_dict = json.loads(firebase_config_raw)
        db = firestore.Client.from_service_account_info(config_dict)
        logging.info("Google Cloud Firestore connection initialized safely.")
    except Exception as e:
        db = None
else:
    db = None

local_db = LocalDatabaseManager()


def resolve_location(
    site_name: str,
    street_address_1: Optional[str] = None,
    street_address_2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    country: str = "US"
) -> str:
    clean_site = site_name.strip()
    payload = {
        "site_name": clean_site,
        "street_address_1": street_address_1,
        "street_address_2": street_address_2,
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "country": country
    }

    if db is not None:
        try:
            db.collection("locations").document(clean_site).set(payload, merge=True)
        except Exception as err:
            logging.warning(f"Cloud location resolve note: {err}")

    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT site_name FROM locations WHERE LOWER(site_name) = LOWER(?)", (clean_site,))
        row = cursor.fetchone()
        if row:
            return row["site_name"]
        
        cursor.execute("""
            INSERT INTO locations (site_name, street_address_1, street_address_2, city, state, postal_code, country)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (clean_site, street_address_1, street_address_2, city, state, postal_code, country))
        conn.commit()
        return clean_site


def resolve_contractor(tbco_account_number: str, company_name: str, trade_specialty: Optional[str] = None) -> str:
    clean_acct = tbco_account_number.strip().upper()
    clean_name = company_name.strip()
    payload = {
        "tbco_account_number": clean_acct,
        "company_name": clean_name,
        "trade_specialty": trade_specialty
    }

    if db is not None:
        try:
            db.collection("contractors").document(clean_acct).set(payload, merge=True)
        except Exception as err:
            logging.warning(f"Cloud contractor resolve note: {err}")

    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tbco_account_number FROM contractors WHERE tbco_account_number = ?", (clean_acct,))
        row = cursor.fetchone()
        if row:
            return row["tbco_account_number"]
        
        cursor.execute("""
            INSERT INTO contractors (tbco_account_number, company_name, trade_specialty)
            VALUES (?, ?, ?)
        """, (clean_acct, clean_name, trade_specialty))
        conn.commit()
        return clean_acct


def resolve_sales_user(
    user_email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    user_phone: Optional[str] = None,
    branch_city: Optional[str] = None
) -> str:
    clean_email = user_email.strip().lower()

    f_name = (first_name or "").strip()
    l_name = (last_name or "").strip()

    if f_name and not l_name:
        parts = f_name.split(" ", 1)
        f_name = parts[0]
        l_name = parts[1] if len(parts) > 1 else ""

    if not f_name:
        f_name = clean_email.split("@")[0]

    payload = {
        "user_email": clean_email,
        "first_name": f_name,
        "last_name": l_name,
        "user_phone": user_phone,
        "branch_city": branch_city,
        "role": "Sales",
        "active_status": "Active"
    }

    if db is not None:
        try:
            db.collection("users").document(clean_email).set(payload, merge=True)
        except Exception as err:
            logging.warning(f"Cloud sales user resolve note: {err}")

    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_email FROM users WHERE LOWER(user_email) = ?", (clean_email,))
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE users SET first_name = ?, last_name = ?, user_phone = COALESCE(?, user_phone)
                WHERE LOWER(user_email) = ?
            """, (f_name, l_name, user_phone, clean_email))
            conn.commit()
            return row["user_email"]

        cursor.execute("""
            INSERT INTO users (user_email, first_name, last_name, user_phone, branch_city, role)
            VALUES (?, ?, ?, ?, ?, 'Sales')
        """, (clean_email, f_name, l_name, user_phone, branch_city))
        conn.commit()
        return clean_email


def resolve_pm_contact(
    tbco_account_number: str,
    first_name: str,
    last_name: str,
    email: str,
    phone: Optional[str] = None,
    title: str = "Project Manager"
) -> str:
    clean_email = email.strip().lower()
    clean_acct = tbco_account_number.strip().upper()

    contact_id = None
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT contact_id FROM contacts WHERE LOWER(email) = ?", (clean_email,))
        row = cursor.fetchone()
        if row:
            contact_id = row["contact_id"]

    if not contact_id:
        contact_id = f"CONT-{uuid.uuid4().hex[:8].upper()}"

    payload = {
        "contact_id": contact_id,
        "tbco_account_number": clean_acct,
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": clean_email,
        "phone": phone,
        "title": title
    }

    if db is not None:
        try:
            db.collection("contacts").document(contact_id).set(payload, merge=True)
        except Exception as err:
            logging.warning(f"Cloud contact resolve note: {err}")

    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT contact_id FROM contacts WHERE LOWER(email) = ?", (clean_email,))
        row = cursor.fetchone()
        if row:
            return row["contact_id"]

        cursor.execute("""
            INSERT INTO contacts (contact_id, tbco_account_number, first_name, last_name, email, phone, title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (contact_id, clean_acct, first_name.strip(), last_name.strip(), clean_email, phone, title))
        conn.commit()
        return contact_id


def process_service_intake_transaction(form_data: Dict[str, Any]) -> str:
    """Executes atomic service intake transaction using normalized intake_requests schema."""
    req_id = form_data.get("request_id") or f"REQ-{uuid.uuid4().hex[:8].upper()}"
    job_no = form_data.get("tbc_job_number", "889900XX").strip().upper()
    submission_time = form_data.get("submission_timestamp") or datetime.now(timezone.utc).isoformat()

    sales_email = (form_data.get("sales_rep_email") or "").strip().lower()
    if sales_email:
        resolve_sales_user(
            user_email=sales_email,
            first_name=form_data.get("sales_rep_first_name", ""),
            last_name=form_data.get("sales_rep_last_name", ""),
            user_phone=form_data.get("sales_rep_phone", "")
        )

    standardized_payload = {
        "request_id": req_id,
        "tbc_job_number": job_no,
        "team_code": form_data.get("team_code", ""),
        "site_name": form_data.get("site_name", "Default Campus"),
        "project_name": form_data.get("project_name", "Default Project"),
        "contractor_company_name": form_data.get("contractor_company_name", "Default Contractor"),
        "street_address_1": form_data.get("street_address_1", ""),
        "street_address_2": form_data.get("street_address_2", ""),
        "city": form_data.get("city", ""),
        "state": form_data.get("state", ""),
        "postal_code": form_data.get("postal_code", ""),
        "country": form_data.get("country", "US"),
        "sales_rep_email": sales_email,
        "sales_rep_phone": form_data.get("sales_rep_phone", ""),
        "project_site_contact_first_name": form_data.get("project_site_contact_first_name", ""),
        "project_site_contact_last_name": form_data.get("project_site_contact_last_name", ""),
        "project_site_contact_email": form_data.get("project_site_contact_email", ""),
        "project_site_contact_phone": form_data.get("project_site_contact_phone", ""),
        "issue_description": form_data.get("issue_description", ""),
        "triage_status": form_data.get("triage_status", "Unassigned"),
        "request_type": form_data.get("request_type", "VFD Startup"),
        "submission_timestamp": submission_time
    }

    # Primary Cloud Write to Firestore 'intake_requests' collection
    if db is not None:
        try:
            db.collection("intake_requests").document(req_id).set(standardized_payload, merge=True)
        except Exception as err:
            logging.warning(f"Cloud transaction note: {err}")

    # Offline Local SQLite Mirror
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION;")

        cursor.execute("""
            INSERT OR REPLACE INTO intake_requests (
                request_id, tbc_job_number, team_code, site_name, project_name,
                contractor_company_name, street_address_1, street_address_2, city, state,
                postal_code, country, sales_rep_email, sales_rep_phone,
                project_site_contact_first_name, project_site_contact_last_name,
                project_site_contact_email, project_site_contact_phone, issue_description,
                triage_status, request_type, submission_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(standardized_payload.values()))

        conn.commit()
        return req_id


def create_job_dispatch(tbc_job_number: str, technician_email: str, scheduled_time: str, job_type: str) -> Dict[str, Any]:
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sales_rep_email FROM intake_requests WHERE tbc_job_number = ? LIMIT 1", (tbc_job_number,))
        row = cursor.fetchone()
        sales_rep = row["sales_rep_email"] if row and row["sales_rep_email"] else "sales1@tombarrow.com"

        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        cursor.execute("""
            INSERT INTO dispatches (job_id, tbc_job_number, technician_email, sales_rep_email, scheduled_time, status, job_type)
            VALUES (?, ?, ?, ?, ?, 'Scheduled', ?)
        """, (job_id, tbc_job_number, technician_email, sales_rep, scheduled_time, job_type))
        conn.commit()

        return {
            "job_id": job_id,
            "tbc_job_number": tbc_job_number,
            "technician_email": technician_email,
            "sales_rep_email": sales_rep,
            "scheduled_time": scheduled_time,
            "job_type": job_type
        }


def save_asset_inspection(job_id: str, asset_id: str, registration_status: str, inspection_metrics: dict) -> str:
    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    metrics_json = json.dumps(inspection_metrics)
    
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO asset_inspections (report_id, job_id, asset_id, registration_status, inspection_metrics)
            VALUES (?, ?, ?, ?, ?)
        """, (report_id, job_id, asset_id, registration_status, metrics_json))
        conn.commit()
        
    return report_id


def record_job_part_used(
    job_id: str,
    sku: Optional[str] = None,
    qty_used: float = 1.0,
    is_unlisted: bool = False,
    unlisted_description: Optional[str] = None,
    manual_cost: float = 0.0,
    cost_status: str = "Pending"
) -> str:
    usage_id = f"USE-{uuid.uuid4().hex[:8].upper()}"
    is_unlisted_flag = 1 if is_unlisted else 0
    actual_sku = None if is_unlisted else sku
    
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO job_parts_used (usage_id, job_id, sku, qty_used, is_unlisted, unlisted_description, manual_cost, cost_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (usage_id, job_id, actual_sku, qty_used, is_unlisted_flag, unlisted_description, manual_cost, cost_status))
        conn.commit()
        
    return usage_id


def log_system_event(
    user_email: str,
    entity_type: str,
    entity_id: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None
) -> str:
    log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    with local_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (log_id, user_email, entity_type, entity_id, timestamp, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (log_id, user_email, entity_type, entity_id, timestamp, old_value, new_value))
        conn.commit()
        
    return log_id