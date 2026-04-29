"""
Centralized design tokens for the Ashborn TUI.
All colors and styles are defined here to keep screens consistent.
"""

from textual.theme import Theme

# ── Color Palette ──────────────────────────────────────────────────────────────
PHOENIX_ORANGE   = "#ff8c00"
PHOENIX_AMBER    = "#ffb347"
PHOENIX_DARK     = "#0d0d0d"
PHOENIX_SURFACE  = "#141414"
PHOENIX_PANEL    = "#1a1a1a"
PHOENIX_BORDER   = "#2a2a2a"
PHOENIX_MUTED    = "#3a3a3a"
PHOENIX_DIMTEXT  = "#666666"
PHOENIX_TEXT     = "#e0e0e0"
PHOENIX_CYAN     = "#00d4ff"
PHOENIX_GREEN    = "#39d353"
PHOENIX_RED      = "#ff4444"
PHOENIX_YELLOW   = "#ffd700"

# ── Textual CSS vars injected via DEFAULT_CSS strings ──────────────────────────
ASHBORN_THEME = Theme(
    name="ashborn",
    primary=PHOENIX_ORANGE,
    secondary=PHOENIX_CYAN,
    accent=PHOENIX_AMBER,
    background=PHOENIX_DARK,
    surface=PHOENIX_SURFACE,
    panel=PHOENIX_PANEL,
    boost=PHOENIX_MUTED,
    warning=PHOENIX_YELLOW,
    error=PHOENIX_RED,
    success=PHOENIX_GREEN,
    dark=True,
)
