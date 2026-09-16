import flet as ft
import os
import sys

# Dynamic path resolution to locate project root and shared modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.frontend.theme import FieldFlowLightTheme


def build_searchable_input(
    label_text: str,
    fetch_options_fn,
    on_select_callback=None,
    hint_text: str = "",
    initial_value: str = "",
    expand: bool = True
) -> ft.Container:
    """
    Universal Searchable Input Component.
    Provides live filtering dropdown suggestions for Projects, Customers, Assets, Contacts, or Phones.
    Uses static text labels above input controls to eliminate layout collapses in dialogs.
    """
    # Static text label placed above the field
    title_label = ft.Text(
        label_text,
        size=11,
        weight=ft.FontWeight.BOLD,
        color=FieldFlowLightTheme.ACCENT_BLUE
    )

    # TextField uses ONLY hint_text (no dynamic floating labels)
    search_tf = ft.TextField(
        hint_text=hint_text or "Type to search...",
        value=initial_value,
        border_color=FieldFlowLightTheme.ACCENT_BLUE,
        focused_border_color=FieldFlowLightTheme.PRIMARY_GREEN
    )

    suggestions_list = ft.Column(spacing=2, scroll=ft.ScrollMode.ALWAYS)
    
    suggestions_card = ft.Container(
        content=suggestions_list,
        bgcolor=FieldFlowLightTheme.SURFACE_CARD,
        border=ft.border.all(1.5, FieldFlowLightTheme.BORDER_PINK_EDGE),
        border_radius=6,
        padding=4,
        height=120,
        visible=False,
        shadow=FieldFlowLightTheme.get_card_shadow()
    )

    def select_option(item_data):
        chosen_val = str(item_data.get("value", ""))
        search_tf.value = chosen_val
        suggestions_card.visible = False
        search_tf.update()
        suggestions_card.update()
        if on_select_callback:
            on_select_callback(item_data.get("raw_data", {}))

    def on_text_changed(e):
        query = search_tf.value.strip()
        if not query:
            suggestions_list.controls.clear()
            suggestions_card.visible = False
            suggestions_card.update()
            return

        matches = fetch_options_fn(query)
        suggestions_list.controls.clear()

        if not matches:
            suggestions_card.visible = False
        else:
            for match in matches:
                disp_text = str(match.get("display_label", match.get("value", "")))
                tile = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.SEARCH, size=14, color=FieldFlowLightTheme.ACCENT_BLUE),
                        ft.Text(disp_text, size=12, weight=ft.FontWeight.W_500, color=FieldFlowLightTheme.TEXT_PRIMARY)
                    ], spacing=8),
                    padding=8,
                    border_radius=4,
                    bgcolor=FieldFlowLightTheme.SURFACE_HOVER,
                    on_click=lambda ev, m=match: select_option(m)
                )
                suggestions_list.controls.append(tile)
            suggestions_card.visible = True

        suggestions_card.update()

    search_tf.on_change = on_text_changed

    # Outer Container handles horizontal expansion when placed in a Row
    container = ft.Container(
        content=ft.Column([
            title_label,
            search_tf,
            suggestions_card
        ], spacing=2, tight=True),
        expand=expand
    )
    container.text_field = search_tf
    return container