"""
Centralized design tokens for the Ashborn TUI.
All colors and styles are defined here to keep screens consistent.
"""

from textual.theme import Theme

# ── Modern Premium Palette ───────────────────────────────────────────────────
# Backgrounds
PHOENIX_DARK     = "#0A0C10"  # Deep Onyx
PHOENIX_SURFACE  = "#12161D"  # Obsidian Surface
PHOENIX_PANEL    = "#1C2128"  # Slate Panel

# Accents
PHOENIX_ORANGE   = "#FF7B00"  # Vibrant Solar Orange
PHOENIX_AMBER    = "#FF9500"  # Warm Glow
PHOENIX_GOLD     = "#D4AF37"  # Metallic Gold
PHOENIX_GLOW     = "#FFD700"  # Pure Gold Glow

# Functional
PHOENIX_BORDER   = "#30363D"  # Steel Border
PHOENIX_MUTED    = "#484F58"  # Iron Gray
PHOENIX_DIMTEXT  = "#8B949E"  # Muted Ash
PHOENIX_TEXT     = "#E6EDF3"  # Soft Cloud
PHOENIX_GREEN    = "#238636"  # Forest Emerald
PHOENIX_RED      = "#DA3633"  # Crimson Edge
PHOENIX_YELLOW   = "#D29922"  # Ochre Warning

# ── Textual Theme ────────────────────────────────────────────────────────────
ASHBORN_THEME = Theme(
    name="ashborn",
    primary=PHOENIX_ORANGE,
    secondary=PHOENIX_GOLD,
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
