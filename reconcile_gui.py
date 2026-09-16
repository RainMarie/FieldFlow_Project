import os
import re
from pathlib import Path
import flet as ft

# Configuration
ROADMAP_FILE = "roadmap.txt"
IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules"}

def get_codebase_files():
    """Recursively collects all relative file and directory names in the project."""
    project_files = []
    current_dir = Path.cwd()
    
    for root, dirs, files in os.walk(current_dir):
        # Modifying dirs in-place filters out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for name in dirs + files:
            relative_path = Path(root).relative_to(current_dir) / name
            project_files.append(str(relative_path).lower())
            
    return project_files

def parse_roadmap():
    """Reads the text roadmap and extracts clean feature goals."""
    if not os.path.exists(ROADMAP_FILE):
        # Create a dummy roadmap file if it doesn't exist yet
        with open(ROADMAP_FILE, "w") as f:
            f.write("Phase 1: Authentication and Login\nPhase 2: Database Setup\nPhase 3: Image processing with Pillow")
            
    with open(ROADMAP_FILE, "r") as f:
        lines = f.readlines()
        
    # Clean up whitespace and filter out empty lines
    return [line.strip() for line in lines if line.strip()]

def audit_reconciliation():
    """Compares text roadmap lines against actual files found in the codebase."""
    roadmap_items = parse_roadmap()
    codebase_elements = get_codebase_files()
    results = []

    for item in roadmap_items:
        # Extract alphanumeric words longer than 3 characters to search for files
        keywords = re.findall(r'\b[a-zA-Z]{4,}\b', item.lower())
        
        # Check if any keyword matches an existing file or folder name
        matched = False
        matching_file = ""
        for element in codebase_elements:
            if keywords and any(kw in element for kw in keywords):
                matched = True
                matching_file = element
                break
                
        results.append({
            "task": item,
            "status": "Implemented" if matched else "Missing",
            "matched_with": matching_file if matched else "None"
        })
        
    return results

def main(page: ft.Page):
    page.title = "Roadmap Reconciliation Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 30

    # Header
    header = ft.Text(
        "Roadmap vs. Current Codebase State", 
        style=ft.TextThemeStyle.HEADLINE_MEDIUM, 
        color=ft.colors.BLUE_200,
        weight=ft.FontWeight.BOLD
    )
    
    sub_header = ft.Text(
        "Automatically matching text roadmap goals with local project files.",
        style=ft.TextThemeStyle.BODY_LARGE,
        color=ft.colors.GREY_400
    )

    # Data rows generation
    audit_data = audit_reconciliation()
    rows = []
    
    for data in audit_data:
        is_implemented = data["status"] == "Implemented"
        
        status_icon = ft.Icon(
            name=ft.icons.CHECK_CIRCLE if is_implemented else ft.icons.CANCEL,
            color=ft.colors.GREEN_400 if is_implemented else ft.colors.RED_400
        )
        
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(data["task"], width=350, max_lines=2)),
                    ft.DataCell(status_icon),
                    ft.DataCell(
                        ft.Text(
                            data["matched_with"], 
                            color=ft.colors.BLUE_GREY_200 if is_implemented else ft.colors.GREY_600,
                            italic=not is_implemented
                        )
                    ),
                ]
            )
        )

    # Data Table
    results_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Roadmap Goal", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Detected File/Folder Reference", weight=ft.FontWeight.BOLD)),
        ],
        rows=rows,
        heading_row_color=ft.colors.SURFACE_VARIANT,
        divider_thickness=1,
    )

    # Adding elements to page
    page.add(
        ft.Column(
            controls=[
                header,
                sub_header,
                ft.Divider(height=20, color=ft.colors.TRANSPARENT),
                results_table
            ],
            spacing=10
        )
    )

if __name__ == "__main__":
    ft.app(target=main)