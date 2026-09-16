"""
src/backend/export_master_schema_matrix.py
Utility script that inspects all 16 SQLite tables and compares field labels
against Cloud Firestore collections, exporting a unified CSV matrix spreadsheet.
"""

import os
import sys
import csv
import sqlite3
import logging

# Dynamically add project root directory to Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.backend.db_manager import local_db, db as firestore_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Explicit mapping between SQLite tables and Cloud Firestore collections
COLLECTION_MAP = {
    "intake_requests": "intake_ledger",
    "dispatches": "dispatches",
    "projects": "projects",
    "assets": "assets",
    "users": "users",
    "locations": "locations",
    "contractors": "contractors"
}


def export_master_schema_matrix():
    """Extracts SQLite schemas and Firestore keys, writing a unified CSV spreadsheet."""
    output_filename = os.path.join(ROOT_DIR, "fieldflow_master_schema_matrix.csv")
    logging.info(f"Starting schema matrix extraction to: {output_filename}")
    
    # -------------------------------------------------------------------------
    # 1. PARSE LOCAL SQLITE SCHEMAS
    # -------------------------------------------------------------------------
    sqlite_schema = {}
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                cols = cursor.fetchall()
                
                cursor.execute(f"PRAGMA foreign_key_list({table});")
                fks = cursor.fetchall()
                
                fk_map = {fk[3]: f"{fk[2]}({fk[4]})" for fk in fks}
                
                sqlite_schema[table] = []
                for col in cols:
                    col_name = col[1]
                    col_type = col[2]
                    is_pk = bool(col[5])
                    fk_ref = fk_map.get(col_name, "N/A")
                    
                    key_role = "Primary Key" if is_pk else ("Foreign Key" if fk_ref != "N/A" else "Standard Column")
                    sqlite_schema[table].append({
                        "name": col_name,
                        "type": col_type,
                        "role": key_role,
                        "fk_ref": fk_ref
                    })
        logging.info(f"Parsed {len(sqlite_schema)} SQLite tables successfully.")
    except Exception as e:
        logging.error(f"Failed to parse SQLite schema: {e}")
        return

    # -------------------------------------------------------------------------
    # 2. SAMPLE CLOUD FIRESTORE COLLECTIONS
    # -------------------------------------------------------------------------
    firestore_keys = {}
    if firestore_db is not None:
        logging.info("Cloud Firestore client online. Sampling collection documents...")
        for sqlite_table, collection_name in COLLECTION_MAP.items():
            try:
                docs = list(firestore_db.collection(collection_name).limit(1).stream())
                if docs:
                    doc_data = docs[0].to_dict()
                    firestore_keys[collection_name] = set(doc_data.keys())
                else:
                    firestore_keys[collection_name] = set()
            except Exception as err:
                logging.warning(f"Could not sample Firestore collection '{collection_name}': {err}")
                firestore_keys[collection_name] = set()
    else:
        logging.warning("Firestore client offline. CSV will populate local SQLite keys.")

    # -------------------------------------------------------------------------
    # 3. WRITE UNIFIED MASTER MATRIX TO CSV
    # -------------------------------------------------------------------------
    try:
        with open(output_filename, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([
                "Database Layer",
                "Table / Collection Name",
                "Field / Column Name",
                "Data Type",
                "Key Role",
                "Foreign Key Reference",
                "Firestore Equivalent Collection",
                "Parity Match Status"
            ])
            
            for table, cols in sqlite_schema.items():
                target_collection = COLLECTION_MAP.get(table, "N/A (Local Only)")
                fs_set = firestore_keys.get(target_collection, set())
                
                for col in cols:
                    c_name = col["name"]
                    
                    if target_collection == "N/A (Local Only)":
                        parity = "Local SQLite Table Only"
                    elif c_name in fs_set or (c_name == "request_id" and "request_id" in fs_set):
                        parity = "1-to-1 Match"
                    elif fs_set:
                        parity = "Missing in Firestore Sample"
                    else:
                        parity = "Firestore Collection Empty / Unsampled"

                    writer.writerow([
                        "SQLite",
                        table,
                        c_name,
                        col["type"],
                        col["role"],
                        col["fk_ref"],
                        target_collection,
                        parity
                    ])

        logging.info(f"🎉 Master Schema Spreadsheet generated at: {output_filename}")
    except Exception as e:
        logging.error(f"Failed to write CSV file: {e}")


if __name__ == "__main__":
    export_master_schema_matrix()