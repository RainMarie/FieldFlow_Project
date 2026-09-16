import flet as ft

class FieldFlowLightTheme:
    """
    FieldFlow Light Theme Design System Tokens & Helper Methods.
    Provides a crisp, field-ready color palette and unified visual styles.
    """
    # Canvas & Surface Palette Tokens
    BG_LIGHT = "#F8FAFC"         # Bright Sky-White background
    SURFACE_CARD = "#FFFFFF"     # Crisp White container surface
    SURFACE_HOVER = "#F1F5F9"    # Soft Slate hover highlight
    BORDER_SUBTLE = "#E2E8F0"    # Soft Slate border lines
    BORDER_CARD_EDGE = "#94A3B8"  # High-contrast Slate card border stroke
    BORDER_COLUMN_EDGE = "#64748B"# Defined Slate column boundary stroke

    # Brand & Accent Tokens
    PRIMARY_GREEN = "#15803D"    # Vibrant Field Green
    ACCENT_BLUE = "#0284C7"      # Sky Blue for links and secondary actions
    SUN_AMBER = "#D97706"        # Sun Gold for triage/alerts
    ERROR_RED = "#DC2626"        # Crimson Red for warnings/deletions

    # Pink Design Tokens & Defined Edges
    PINK_PRIMARY = "#DB2777"     # Deep Rose Pink for primary headers & highlights
    PINK_ACCENT = "#EC4899"      # Bright Pink for secondary accents
    BG_PINK_TINT = "#FCE7F3"     # Soft Pastel Pink surface tint
    BORDER_PINK_EDGE = "#F472B6"  # Defined Pink 1.5px/2px border stroke

    # Typography Colors
    TEXT_PRIMARY = "#0F172A"     # Deep Charcoal for text legibility
    TEXT_MUTED = "#64748B"       # Soft Slate for secondary labels

    # Soft Background Tints for Status Badges & Alerts
    BG_AMBER_TINT = "#FEF3C7"
    BG_BLUE_TINT = "#E0F2FE"
    BG_GREEN_TINT = "#DCFCE7"
    BG_RED_TINT = "#FEE2E2"
    SHADOW_COLOR = "#0F172A14"

    @staticmethod
    def get_primary_button_style() -> ft.ButtonStyle:
        """Returns standard primary action button styling (Field Green)."""
        return ft.ButtonStyle(
            bgcolor=FieldFlowLightTheme.PRIMARY_GREEN,
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=ft.padding.symmetric(horizontal=16, vertical=12)
        )

    @staticmethod
    def get_secondary_button_style() -> ft.ButtonStyle:
        """Returns standard secondary action button styling (Sky Blue)."""
        return ft.ButtonStyle(
            bgcolor="transparent",
            color=FieldFlowLightTheme.ACCENT_BLUE,
            shape=ft.RoundedRectangleBorder(radius=6),
            padding=ft.padding.symmetric(horizontal=12, vertical=8)
        )

    @staticmethod
    def get_card_shadow() -> list[ft.BoxShadow]:
        """Returns elevation shadow for crisp card and column boundaries."""
        return [
            ft.BoxShadow(
                spread_radius=1,
                blur_radius=6,
                color=FieldFlowLightTheme.SHADOW_COLOR,
                offset=ft.Offset(0, 2)
            )
        ]

    @staticmethod
    def get_toast_style(kind: str = "info") -> dict:
        """
        Encapsulates alert styling (bg, border, text, icon) based on toast kind.
        """
        if kind == "success":
            return {
                "bg": FieldFlowLightTheme.BG_GREEN_TINT,
                "border": FieldFlowLightTheme.PRIMARY_GREEN,
                "text": FieldFlowLightTheme.PRIMARY_GREEN,
                "icon": ft.icons.CHECK_CIRCLE
            }
        elif kind == "error":
            return {
                "bg": FieldFlowLightTheme.BG_RED_TINT,
                "border": FieldFlowLightTheme.ERROR_RED,
                "text": FieldFlowLightTheme.ERROR_RED,
                "icon": ft.icons.ERROR_OUTLINE
            }
        elif kind == "warning":
            return {
                "bg": FieldFlowLightTheme.BG_AMBER_TINT,
                "border": FieldFlowLightTheme.SUN_AMBER,
                "text": FieldFlowLightTheme.SUN_AMBER,
                "icon": ft.icons.WARNING_AMBER
            }
        else:  # "info"
            return {
                "bg": FieldFlowLightTheme.BG_PINK_TINT,
                "border": FieldFlowLightTheme.PINK_PRIMARY,
                "text": FieldFlowLightTheme.PINK_PRIMARY,
                "icon": ft.icons.INFO_OUTLINE
            }

    @staticmethod
    def resolve_status_badge_colors(status_string: str) -> tuple[str, str]:
        """
        Resolves (background_tint_color, text_color) based on ticket status.
        """
        status = (status_string or "").strip()
        if status in ["Unassigned", "PENDING_TRIAGE"]:
            return (FieldFlowLightTheme.BG_AMBER_TINT, FieldFlowLightTheme.SUN_AMBER)
        elif status in ["Dispatched", "Scheduled", "In Progress", "Traveling"]:
            return (FieldFlowLightTheme.BG_BLUE_TINT, FieldFlowLightTheme.ACCENT_BLUE)
        elif status in ["Completed", "Registration Complete"]:
            return (FieldFlowLightTheme.BG_GREEN_TINT, FieldFlowLightTheme.PRIMARY_GREEN)
        else:
            return (FieldFlowLightTheme.BORDER_SUBTLE, FieldFlowLightTheme.TEXT_MUTED)