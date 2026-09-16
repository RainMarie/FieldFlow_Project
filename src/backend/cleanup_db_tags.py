import sqlite3
import os

# Dynamic path resolution to connect with your local SQLite database
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "tbc_local.db")

def clean_legacy_database_tags():
    """
    Scans tbc_local.db and permanently strips prefix tags 
    from existing database records on disk[cite: 2].
    """
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    print("=" * 60)
    print("🧹 STARTING DATABASE TAG CLEANUP MIGRATION")
    print("=" * 60)

    # 1. Clean 'projects' table[cite: 2, 3]
    cursor.execute("""
        UPDATE projects
        SET project_name = REPLACE(project_name, 'Service: ', ''),
            site_address = REPLACE(site_address, 'Address: ', ''),
            contractor_name = REPLACE(contractor_name, 'Client: ', '')
        WHERE project_name LIKE 'Service:%'
           OR site_address LIKE 'Address:%'
           OR contractor_name LIKE 'Client:%';
    """)
    projects_cleaned = cursor.rowcount

    # 2. Clean 'intake_requests' table[cite: 2, 3]
    cursor.execute("""
        UPDATE intake_requests
        SET tbc_job_number = REPLACE(REPLACE(tbc_job_number, 'Job #', ''), 'JOB-', ''),
            project_site_address = REPLACE(project_site_address, 'Address: ', ''),
            issue_description = REPLACE(issue_description, 'Issue: ', '')
        WHERE tbc_job_number LIKE '%Job #%'
           OR tbc_job_number LIKE 'JOB-%'
           OR project_site_address LIKE 'Address:%'
           OR issue_description LIKE 'Issue:%';
    """)
    intake_cleaned = cursor.rowcount

    # 3. Clean 'dispatches' table[cite: 2, 3]
    cursor.execute("""
        UPDATE dispatches
        SET tbc_job_number = REPLACE(REPLACE(tbc_job_number, 'Job #', ''), 'JOB-', '')
        WHERE tbc_job_number LIKE '%Job #%'
           OR tbc_job_number LIKE 'JOB-%';
    """)
    dispatches_cleaned = cursor.rowcount

    conn.commit()
    conn.close()

    print(f"✅ Projects table rows updated: {projects_cleaned}")
    print(f"✅ Intake Requests table rows updated: {intake_cleaned}")
    print(f"✅ Dispatches table rows updated: {dispatches_cleaned}")
    print("=" * 60)
    print("🎉 MIGRATION COMPLETE: All legacy tags permanently removed!")
    print("=" * 60)

if __name__ == "__main__":
    clean_legacy_database_tags()