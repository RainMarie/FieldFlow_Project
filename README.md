# FieldFlow Implementation Manual & Technical Baseline

**System Status:** Build Environment Verified Live
**Last Updated:** June 16, 2026
**Target Architecture:** Web-Native Flet (Python/Flutter)

---

## 1. Local Runtime Scaffolding
* **Core Engine:** Python 3.14.6 
* **Sandbox Isolation:** Activated via `.venv` virtual environment.
* **UI Engine:** Flet Framework `v0.21.2`

## 2. Production Library Configuration
The local environment is strictly bound to the following dependency versions:
* `flet==0.21.2` (Cross-platform interface layer)
* `google-cloud-firestore==2.16.0` (Managed NoSQL Cloud database store)
* `cryptography==42.0.5` (Symmetric encryption engine)
* `keyring==25.0.0` (Native hardware vault interface)

## 3. Directory Mapping Matrix
fieldflow/
├── .venv/                   # Isolated python sandbox wrapper
├── assets/                  # Pre-rendered view asset placeholders
└── src/
├── backend/             # Cloud event hooks & local SQLite sync scripts
└── frontend/            # Layout components (Control Tower & Mobile Suite)


## 4. Operational Execution Commands
* **To Reactivate Sandbox Terminal:**
  * Windows: `.venv\Scripts\activate`
  * Mac/Linux: `source .venv/bin/activate`
* **To Re-Verify Dependencies:** `pip install -r requirements.txt`