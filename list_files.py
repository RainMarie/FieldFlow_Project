from pathlib import Path

def list_all_files(project_directory: str = "."):
    """
    Recursively scans and prints all files in the target directory and subdirectories.
    
    Parameters:
        project_directory (str): Path to the project folder (defaults to current directory).
    """
    root_path = Path(project_directory)
    
    # Verify path validity
    if not root_path.exists():
        print(f"Error: Path '{project_directory}' does not exist.")
        return
    if not root_path.is_dir():
        print(f"Error: Path '{project_directory}' is not a directory.")
        return

    print(f"Listing all files in: {root_path.resolve()}\n" + "-" * 40)
    
    file_count = 0
    
    # rglob('*') recursively finds all items across all subdirectories
    for item in root_path.rglob('*'):
        # Filter to display only files, skipping folders
        if item.is_file():
            # Show path relative to current folder for clean output
            print(item.relative_to(root_path))
            file_count += 1
            
    print("-" * 40)
    print(f"Total files found: {file_count}")

if __name__ == "__main__":
    # Scans the directory where the script is located
    list_all_files()