"""
audit_ui_buttons.py
Workspace auditor for Flet UI controls and event callback coverage.
Focuses strictly on actionable interactive controls and ignores static layout containers.
"""

import os
import sys
import ast
import csv

# Dedicated button types that always require event handlers
DEDICATED_BUTTONS = {
    "ElevatedButton",
    "TextButton",
    "IconButton",
    "OutlinedButton",
    "FloatingActionButton",
    "ListTile",
    "GestureDetector",
    "InkWell",
    "PopupMenuButton",
    "MenuItemButton"
}

# Event callback keyword arguments to inspect
CALLBACK_KEYWORDS = {
    "on_click",
    "on_tap",
    "on_change",
    "on_submit",
    "on_dismiss",
    "on_select"
}


def extract_label_text(node: ast.Call) -> str:
    """Extracts text, label, value, or title attributes from AST control arguments."""
    # Check positional arguments (e.g. ft.ElevatedButton("Save"))
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value

    # Check keyword arguments (e.g. ft.TextField(label="Project Name"))
    for kw in node.keywords:
        if kw.arg in ("text", "label", "value", "title", "tooltip"):
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value

    return "<N/A or Dynamic>"


def should_audit_control(node: ast.Call, control_name: str) -> bool:
    """
    Determines whether an AST Call node is a true interactive button or actionable container.
    """
    # 1. Always audit dedicated button controls
    if control_name in DEDICATED_BUTTONS:
        return True

    # 2. Audit Containers only if configured for user interactivity
    if control_name == "Container":
        has_ink = False
        has_callback = False

        for kw in node.keywords:
            if kw.arg == "ink" and isinstance(kw.value, ast.Constant):
                if bool(kw.value.value) is True:
                    has_ink = True
            if kw.arg in CALLBACK_KEYWORDS:
                has_callback = True

        # Audit only if ink ripple is enabled or a callback is already assigned
        return has_ink or has_callback

    # Exclude visual Card elevation wrappers and static containers
    return False


def audit_workspace(root_dir="src"):
    """Scans Python files across the workspace root and writes the audit CSV report."""
    print("=" * 80)
    print("🔍 AUDITING FIELDFLOW WORKSPACE FOR ACTIONABLE UI BUTTONS...")
    print("=" * 80)

    rows = []
    total_found = 0
    missing_count = 0

    for current_root, _, files in os.walk(root_dir):
        for file_name in files:
            if file_name.endswith(".py"):
                file_path = os.path.relpath(os.path.join(current_root, file_name))

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()

                    tree = ast.parse(code)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            control_name = None
                            if isinstance(node.func, ast.Attribute):
                                control_name = node.func.attr
                            elif isinstance(node.func, ast.Name):
                                control_name = node.func.id

                            if control_name and should_audit_control(node, control_name):
                                line_no = getattr(node, "lineno", 0)
                                label_text = extract_label_text(node)

                                has_callback = any(
                                    kw.arg in CALLBACK_KEYWORDS
                                    for kw in node.keywords
                                    if kw.arg
                                )

                                status = "OK" if has_callback else "MISSING CALLBACK"
                                if not has_callback:
                                    missing_count += 1
                                total_found += 1

                                rows.append([
                                    file_path,
                                    line_no,
                                    control_name,
                                    label_text,
                                    status,
                                    ""
                                ])

                except Exception as err:
                    print(f"⚠️ Error parsing {file_path}: {err}")

    output_csv = "ui_callbacks_audit.csv"
    header = [
        "App / File Path",
        "Line Number",
        "Control Type",
        "Button Label / Text",
        "Callback Status",
        "Completed [ ]"
    ]

    try:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        saved_path = output_csv
    except PermissionError:
        saved_path = "ui_callbacks_audit_latest.csv"
        print(f"\n⚠️ '{output_csv}' is locked by another program!")
        print(f"Saving output to fallback file: {saved_path}")
        with open(saved_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

    print(f"\n✅ Audit complete! Spreadsheet saved at:\n   {os.path.abspath(saved_path)}\n")
    print("📊 SUMMARY STATISTICS:")
    print(f"   • Total Actionable Controls Found: {total_found}")
    print(f"   • Controls Missing Callbacks:      {missing_count}")
    print("=" * 80)


if __name__ == "__main__":
    target_folder = "src" if os.path.exists("src") else "."
    audit_workspace(target_folder)