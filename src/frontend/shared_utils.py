import os
import sys
import glob
import base64
import urllib.parse
import flet as ft

# Dynamic path resolution to recognize project root directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.frontend.theme import FieldFlowLightTheme


def show_toast(page: ft.Page, message: str, kind: str = "success") -> None:
    """Displays a standardized floating SnackBar toast notification on the page."""
    style = FieldFlowLightTheme.get_toast_style(kind)
    page.snack_bar = ft.SnackBar(
        content=ft.Container(
            content=ft.Row(
                [
                    ft.Icon(style["icon"], color=style["text"], size=20),
                    ft.Text(message, color=style["text"], weight=ft.FontWeight.BOLD, size=13, expand=True),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.START
            ),
            padding=ft.padding.all(8),
            border=ft.border.all(1.5, style["border"]),
            border_radius=8
        ),
        bgcolor=style["bg"],
        behavior=ft.SnackBarBehavior.FLOATING,
        margin=ft.margin.all(16),
        duration=3500,
        dismiss_direction=ft.DismissDirection.HORIZONTAL
    )
    page.snack_bar.open = True
    page.update()


def find_any_local_logo() -> str:
    """Locates any fallback logo image inside project assets folders[cite: 8, 9]."""
    search_dirs = [
        os.path.join(CURRENT_DIR, "assets"),
        os.path.join(SRC_DIR, "assets"),
        os.path.join(ROOT_DIR, "assets"),
        CURRENT_DIR
    ]
    extensions = ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.PNG", "*.JPEG"]
    for d in search_dirs:
        if os.path.exists(d):
            for ext in extensions:
                files = glob.glob(os.path.join(d, ext))
                if files:
                    return files[0]
    return None


def get_base64_from_file(file_path: str):
    """Encodes local image files to base64 for safe rendering in Flet controls[cite: 8, 9]."""
    if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            pass
    return None


def open_drive_link(page: ft.Page, folder_id: str, show_toast_fn=None) -> None:
    """Formats Google Drive folder links, copies URL to clipboard, and opens browser[cite: 6]."""
    clean_folder = str(folder_id or "").strip()
    if not clean_folder or clean_folder.startswith("FLD-"):
        full_url = "https://drive.google.com/drive/my-drive"
    elif clean_folder.startswith("http://") or clean_folder.startswith("https://"):
        full_url = clean_folder
    else:
        full_url = f"https://drive.google.com/drive/folders/{clean_folder}"

    page.set_clipboard(full_url)
    page.launch_url(full_url)

    if show_toast_fn:
        show_toast_fn("📂 Opening Google Drive Folder", kind="info")
    else:
        show_toast(page, "📂 Opening Google Drive Folder", kind="info")


def open_navigation_map(page: ft.Page, address: str) -> None:
    """URL-encodes an address string and opens Google Maps navigation[cite: 6]."""
    encoded_addr = urllib.parse.quote(str(address or "Tampa, FL"))
    maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded_addr}"
    page.launch_url(maps_url)