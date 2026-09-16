from pathlib import Path

def generate_project_summary(project_directory: str = "."):
    """
    Scans top-level files and main project subfolders while skipping 
    virtual environments, system cache, and hidden directories.
    """
    root_path = Path(project_directory)
    
    # Folders and hidden files to skip
    ignore_list = {".git", "__pycache__", "venv", ".venv", "env", ".vscode", ".idea"}
    
    if not root_path.exists():
        print(f"Error: Path '{project_directory}' does not exist.")
        return

    print(f"Project Structure for: {root_path.resolve()}\n" + "=" * 40)
    
    # Iterate through top-level items in alphabetical order
    for item in sorted(root_path.iterdir()):
        # Skip ignored or hidden files/folders
        if item.name in ignore_list or item.name.startswith('.'):
            continue
            
        # Display top-level files
        if item.is_file():
            print(f"📄 {item.name}")
            
        # Display top-level directories and look 1 level inside them
        elif item.is_dir():
            print(f"📁 {item.name}/")
            for sub_item in sorted(item.iterdir()):
                if sub_item.name in ignore_list or sub_item.name.startswith('.'):
                    continue
                if sub_item.is_file():
                    print(f"    └── 📄 {sub_item.name}")
                elif sub_item.is_dir():
                    print(f"    └── 📁 {sub_item.name}/")

if __name__ == "__main__":
    # Runs in the current working directory
    generate_project_summary()
    