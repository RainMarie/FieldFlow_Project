import os

def bundle_split_project_code():
    """
    Automates FieldFlow codebase segmentation. 
    Parses and extracts independent text manifests for Backend and Frontend layers
    to ensure deployment tracking sanity and protect the staging baseline.
    """
    # Define manifest outputs
    backend_output = "fieldflow_backend_manifest.txt"
    frontend_output = "fieldflow_frontend_manifest.txt"
    
    # Target directories
    backend_dir = "src/backend"
    frontend_dir = "src/frontend"
    
    # -----------------------------------------------------------------
    # 1. PROCESS BACKEND ARCHITECTURE LAYER
    # -----------------------------------------------------------------
    print("🚀 Engineering the Backend Architecture Manifest...")
    with open(backend_output, "w", encoding="utf-8") as be_file:
        be_file.write("=== FIELDFLOW BACKEND ARCHITECTURE MANIFEST ===\n")
        be_file.write("Core Mandate: Data foundation, caching infrastructure, security, and cloud sync.\n\n")
        
        # requirements.txt contains critical system-wide engineering dependencies
        if os.path.exists("requirements.txt"):
            write_file_to_manifest("requirements.txt", be_file)
            
        if os.path.exists(backend_dir):
            parse_directory_tree(backend_dir, be_file)
        else:
            print(f"⚠️ Warning: Backend directory '{backend_dir}' not found on disk.")

    # -----------------------------------------------------------------
    # 2. PROCESS FRONTEND VISUAL LAYER
    # -----------------------------------------------------------------
    print("🎨 Engineering the Frontend Interface Manifest...")
    with open(frontend_output, "w", encoding="utf-8") as fe_file:
        fe_file.write("=== FIELDFLOW FRONTEND ARCHITECTURE MANIFEST ===\n")
        fe_file.write("Core Mandate: User interface viewports, validation engines, and user states.\n\n")
        
        # app.py acts as the main system loop and viewport layout router
        if os.path.exists("app.py"):
            write_file_to_manifest("app.py", fe_file)
            
        if os.path.exists(frontend_dir):
            parse_directory_tree(frontend_dir, fe_file)
        else:
            print(f"⚠️ Warning: Frontend directory '{frontend_dir}' not found on disk.")

    print("\n" + "="*50)
    print("🏁 DEV-OPS AUTOMATION SUCCESSFUL: BASELINE SPLIT COMPLETE")
    print("="*50)
    print(f"📦 Generated Backend Ledger:  '{backend_output}'")
    print(f"📦 Generated Frontend Ledger: '{frontend_output}'")

def write_file_to_manifest(file_path, output_stream):
    """Reads file content parameter-safely and writes to the manifest layout stream."""
    try:
        output_stream.write(f"\n{'='*40}\n")
        output_stream.write(f"FILE: {file_path}\n")
        output_stream.write(f"{'='*40}\n\n")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as active_file:
            output_stream.write(active_file.read())
        output_stream.write("\n")
    except Exception as e:
        output_stream.write(f"\n[CRITICAL ERROR READING FILE {file_path}: {str(e)}]\n")

def parse_directory_tree(target_directory, output_stream):
    """Walks the directory sub-trees and sequences valid Python scripts into the active stream."""
    for root, _, files in os.walk(target_directory):
        for file in sorted(files):
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path)
                write_file_to_manifest(relative_path, output_stream)

if __name__ == "__main__":
    bundle_split_project_code()
    