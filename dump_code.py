import os

def bundle_project_code():
    output_filename = "fieldflow_snapshot.txt"
    targets = ["src/backend", "src/frontend"]
    root_files = ["app.py", "requirements.txt"]
    
    with open(output_filename, "w", encoding="utf-8") as outfile:
        outfile.write("=== FIELDFLOW PROJECT CODE SNAPSHOT ===\n\n")
        
        # 1. Process specified root files
        for r_file in root_files:
            if os.path.exists(r_file):
                outfile.write(f"\n{'='*40}\n")
                outfile.write(f"FILE: {r_file}\n")
                outfile.write(f"{'='*40}\n\n")
                with open(r_file, "r", encoding="utf-8", errors="ignore") as f:
                    outfile.write(f.read())
                outfile.write("\n")

        # 2. Process target directories
        for target_dir in targets:
            if not os.path.exists(target_dir):
                continue
            for root, _, files in os.walk(target_dir):
                for file in sorted(files):
                    if file.endswith(".py"):
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path)
                        outfile.write(f"\n{'='*40}\n")
                        outfile.write(f"FILE: {relative_path}\n")
                        outfile.write(f"{'='*40}\n\n")
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            outfile.write(f.read())
                        outfile.write("\n")

    print(f"Done! All your code text has been consolidated into '{output_filename}'.")

if __name__ == "__main__":
    bundle_project_code()