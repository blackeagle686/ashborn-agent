"""
Centralized design tokens for the Ashborn TUI.
All colors and styles are defined here to keep screens consistent.
"""

from textual.theme import Theme

# ── Color Palette ──────────────────────────────────────────────────────────────
PHOENIX_ORANGE   = "#ff8c00"
PHOENIX_AMBER    = "#ffb347"
PHOENIX_DARK     = "#1B1F24"
PHOENIX_SURFACE  = "#1B1F24"
PHOENIX_PANEL    = "#2E333A"
PHOENIX_BORDER   = "#2E333A"
PHOENIX_MUTED    = "#2E333A"
PHOENIX_DIMTEXT  = "#A89F91"
PHOENIX_TEXT     = "#F1E9DD"
PHOENIX_CYAN     = "#A89F91"
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
