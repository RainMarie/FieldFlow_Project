"""
reset_database.py
Single-use setup script to completely wipe local SQLite (tbc_local.db)
and dynamically delete ALL Cloud Firestore collections.
Leaves both storage layers clean and ready for master seeding.
"""

import os
import sys
import logging

# Ensure project root is registered in Python's search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

try:
    from src.backend.db_manager import db, local_db
except ImportError as err:
    logging.error(f"Failed to import db_manager module: {err}")
    sys.exit(1)


def wipe_and_rebuild_sqlite():
    """Wipes all local SQLite tables and re-initializes all 16 relational schema tables."""
    logging.info("Starting local SQLite purge...")
    try:
        with local_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = OFF;")

            # Fetch and drop all user tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for table_tuple in tables:
                table_name = table_tuple[0]
                if not table_name.startswith("sqlite_"):
                    cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
                    logging.info(f"Dropped local SQLite table: {table_name}")

            cursor.execute("PRAGMA foreign_keys = ON;")
            conn.commit()

        logging.info("Re-initializing 16 local SQLite tables...")
        local_db.init_sqlite_schema()
        logging.info("🎉 Local SQLite database reset complete.")
    except Exception as err:
        logging.error(f"Error resetting local SQLite database: {err}")


def purge_all_firestore_collections():
    """Dynamically discovers and deletes ALL documents across ALL Cloud Firestore collections."""
    if db is None:
        logging.warning("Firestore client is not connected. Skipping cloud purge.")
        return

    logging.info("Discovering all active Cloud Firestore collections dynamically...")
    try:
        collections = list(db.collections())

        if not collections:
            logging.info("No collections found in Cloud Firestore. Database is clean!")
            return

        for col in collections:
            logging.info(f"Purging Firestore collection: '{col.id}'...")
            docs = list(col.stream())
            deleted_count = 0
            
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1

            logging.info(f"Successfully deleted {deleted_count} document(s) from '{col.id}'.")

        logging.info("🎉 Cloud Firestore completely purged!")
    except Exception as err:
        logging.error(f"Error purging Cloud Firestore collections: {err}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STARTING FULL DATABASE RESET (SQLITE & FIRESTORE)")
    print("=" * 60 + "\n")

    wipe_and_rebuild_sqlite()
    purge_all_firestore_collections()

    print("\n" + "=" * 60)
    print("SETUP COMPLETE: DATABASE IS CLEAN AND READY FOR SEEDING!")
    print("=" * 60 + "\n")