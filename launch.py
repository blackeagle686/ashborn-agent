#!/usr/bin/env python3
"""
Ashborn Agent Launcher
Shows a native GTK splash screen, starts the backend server,
polls /health until the agent is ready, then opens VS Codium.
"""

import os
import sys
import subprocess
import threading
import urllib.request
import urllib.error
import json
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
import cairo
import math

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON  = os.path.join(SCRIPT_DIR, "venv", "bin", "python3")
SERVER_CMD   = [VENV_PYTHON, "-m", "uvicorn", "ashborn.server:app",
                "--host", "127.0.0.1", "--port", "8765"]
HEALTH_URL   = "http://127.0.0.1:8765/health"
ICON_PATH    = os.path.join(SCRIPT_DIR, "vscode-extension", "media", "ashborn.png")
POLL_INTERVAL = 1.5  # seconds
VSCODE_BIN   = "code"  # or "codium"

MESSAGES = [
    "Starting Ashborn server…",
    "Loading AI modules…",
    "Initializing Phoenix framework…",
    "Warming up the agent…",
    "Connecting to AI backend…",
    "Almost ready…",
]

# ── Colours (matching the IDE dark theme) ─────────────────────────────────────
BG_DARK    = (0.063, 0.008, 0.031)       # #100208
PURPLE     = (0.722, 0.188, 1.0)         # #b830ff
ORANGE     = (1.0,   0.510, 0.188)       # #ff8230
RED_LAVA   = (1.0,   0.251, 0.125)       # #ff4020
TEXT_DIM   = (0.722, 0.604, 0.800)       # #b89acc
TEXT_MUTED = (0.478, 0.369, 0.541)       # #7a5e8a
WHITE      = (0.961, 0.933, 1.0)         # #f5eeff


class SplashWindow(Gtk.Window):
    def __init__(self):
        super().__init__(Gtk.WindowType.POPUP)

        # Window setup ─────────────────────────────────────────────────────────
        self.set_title("Ashborn Agent")
        self.set_default_size(400, 480)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_app_paintable(True)

        # Transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # Animation state ──────────────────────────────────────────────────────
        self._angle        = 0.0          # ring rotation
        self._pulse        = 0.0          # orb pulse
        self._dot_phase    = 0.0          # loading dots
        self._status_text  = MESSAGES[0]
        self._msg_index    = 0
        self._done         = False
        self._success      = False
        self._fade_alpha   = 1.0
        self._logo_pixbuf  = None

        # Load the Ashborn logo
        if os.path.exists(ICON_PATH):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(ICON_PATH)
                self._logo_pixbuf = pb.scale_simple(80, 80, GdkPixbuf.InterpType.BILINEAR)
            except Exception:
                pass

        # Drawing area
        self._da = Gtk.DrawingArea()
        self._da.connect("draw", self._on_draw)
        self.add(self._da)

        # Rounded corners via shape mask (CSS)
        css = b"""
        window {
          border-radius: 20px;
          box-shadow: 0 30px 80px rgba(0,0,0,0.8),
                      0 0 60px rgba(184,48,255,0.3);
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        self.get_style_context().add_provider(
            css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # 60 fps animation loop
        GLib.timeout_add(16, self._tick)
        # Cycle status messages every 2.5s
        GLib.timeout_add(2500, self._next_message)

        self.show_all()

    # ── Animation tick ─────────────────────────────────────────────────────────
    def _tick(self):
        self._angle     = (self._angle + 2.0) % 360
        self._pulse     = (self._pulse + 0.03) % (2 * math.pi)
        self._dot_phase = (self._dot_phase + 0.06) % (2 * math.pi)

        if self._done:
            self._fade_alpha = max(0.0, self._fade_alpha - 0.035)
            self._da.queue_draw()
            if self._fade_alpha <= 0.0:
                Gtk.main_quit()
                return False
            return True

        self._da.queue_draw()
        return True

    def _next_message(self):
        if not self._done:
            self._msg_index = (self._msg_index + 1) % len(MESSAGES)
            self._status_text = MESSAGES[self._msg_index]
        return not self._done

    # ── Drawing ────────────────────────────────────────────────────────────────
    def _on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        cx, cy = w / 2, h / 2

        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # Global fade alpha
        cr.push_group()

        # ── Background with rounded rect ──────────────────────────────────────
        self._rounded_rect(cr, 0, 0, w, h, 20)
        cr.set_source_rgb(*BG_DARK)
        cr.fill()

        # ── Ambient orbs ──────────────────────────────────────────────────────
        pulse = 0.85 + 0.15 * math.sin(self._pulse)

        # Purple orb top-left
        pat = cairo.RadialGradient(60, 60, 0, 60, 60, 140 * pulse)
        pat.add_color_stop_rgba(0, *PURPLE, 0.30)
        pat.add_color_stop_rgba(1, *PURPLE, 0.0)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # Orange orb bottom-right
        pat2 = cairo.RadialGradient(w - 60, h - 60, 0, w - 60, h - 60, 120 * pulse)
        pat2.add_color_stop_rgba(0, *RED_LAVA, 0.25)
        pat2.add_color_stop_rgba(1, *RED_LAVA, 0.0)
        cr.set_source(pat2)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # ── Spinning gradient ring ─────────────────────────────────────────────
        ring_r = 72
        ring_w = 4.5
        angle_rad = math.radians(self._angle)
        cr.save()
        cr.translate(cx, cy - 60)
        # Outer glow
        cr.set_line_width(ring_w + 10)
        cr.set_source_rgba(*PURPLE, 0.15)
        cr.arc(0, 0, ring_r, 0, 2 * math.pi)
        cr.stroke()
        # Main ring — drawn as arc segments with colour sweep
        segments = 120
        for i in range(segments):
            t   = i / segments
            t1  = (i + 1) / segments
            a0  = angle_rad + t  * 2 * math.pi
            a1  = angle_rad + t1 * 2 * math.pi
            # Lerp purple → orange → red
            if t < 0.5:
                r = PURPLE[0] + (ORANGE[0] - PURPLE[0]) * t * 2
                g = PURPLE[1] + (ORANGE[1] - PURPLE[1]) * t * 2
                b = PURPLE[2] + (ORANGE[2] - PURPLE[2]) * t * 2
            else:
                r = ORANGE[0] + (RED_LAVA[0] - ORANGE[0]) * (t - 0.5) * 2
                g = ORANGE[1] + (RED_LAVA[1] - ORANGE[1]) * (t - 0.5) * 2
                b = ORANGE[2] + (RED_LAVA[2] - ORANGE[2]) * (t - 0.5) * 2
            alpha = 0.4 + 0.6 * t
            cr.set_source_rgba(r, g, b, alpha)
            cr.set_line_width(ring_w)
            cr.arc(0, 0, ring_r, a0, a1)
            cr.stroke()
        cr.restore()

        # ── Logo inside ring ──────────────────────────────────────────────────
        logo_x = cx - 40
        logo_y = cy - 60 - 40
        logo_float = 4 * math.sin(self._pulse)
        if self._logo_pixbuf:
            cr.save()
            cr.translate(logo_x, logo_y + logo_float)
            # Logo glow
            glow = cairo.RadialGradient(40, 40, 0, 40, 40, 45)
            glow.add_color_stop_rgba(0, *PURPLE, 0.35)
            glow.add_color_stop_rgba(1, *PURPLE, 0.0)
            cr.set_source(glow)
            cr.arc(40, 40, 45, 0, 2 * math.pi)
            cr.fill()
            Gdk.cairo_set_source_pixbuf(cr, self._logo_pixbuf, 0, 0)
            cr.paint()
            cr.restore()
        else:
            # Fallback: draw a flame emoji-style circle
            cr.set_source_rgba(*ORANGE, 0.9)
            cr.arc(cx, cy - 60 + logo_float, 30, 0, 2 * math.pi)
            cr.fill()

        # ── Title ─────────────────────────────────────────────────────────────
        cr.save()
        cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(26)
        # Gradient text (approximate with orange)
        cr.set_source_rgb(*ORANGE)
        title = "Ashborn Agent"
        ext = cr.text_extents(title)
        cr.move_to(cx - ext.width / 2, cy + 30)
        cr.show_text(title)
        cr.restore()

        # ── Subtitle ──────────────────────────────────────────────────────────
        cr.save()
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11)
        cr.set_source_rgba(*TEXT_MUTED, 0.85)
        sub = "Autonomous AI Development Partner"
        ext = cr.text_extents(sub)
        cr.move_to(cx - ext.width / 2, cy + 52)
        cr.show_text(sub)
        cr.restore()

        # ── Animated loading dots ─────────────────────────────────────────────
        dot_y = cy + 90
        dot_r = 5
        dot_gap = 18
        for i in range(3):
            phase = self._dot_phase - i * 0.7
            scale = 0.5 + 0.5 * (0.5 + 0.5 * math.sin(phase))
            t = i / 2.0
            r = PURPLE[0] + (ORANGE[0] - PURPLE[0]) * t
            g = PURPLE[1] + (ORANGE[1] - PURPLE[1]) * t
            b = PURPLE[2] + (ORANGE[2] - PURPLE[2]) * t
            dx = cx + (i - 1) * dot_gap
            cr.set_source_rgba(r, g, b, 0.4 + 0.6 * scale)
            cr.arc(dx, dot_y, dot_r * scale, 0, 2 * math.pi)
            cr.fill()

        # ── Status text ───────────────────────────────────────────────────────
        cr.save()
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(11.5)
        if self._success:
            cr.set_source_rgba(0.30, 0.78, 0.51, 1.0)  # green
        else:
            cr.set_source_rgba(*TEXT_DIM, 0.80)
        ext = cr.text_extents(self._status_text)
        cr.move_to(cx - ext.width / 2, dot_y + 28)
        cr.show_text(self._status_text)
        cr.restore()

        # ── "Powered by Phoenix AI" footer ────────────────────────────────────
        cr.save()
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(10)
        cr.set_source_rgba(*TEXT_MUTED, 0.45)
        footer = "Powered by Phoenix AI Framework"
        ext = cr.text_extents(footer)
        cr.move_to(cx - ext.width / 2, h - 28)
        cr.show_text(footer)
        cr.restore()

        # Apply global fade
        cr.pop_group_to_source()
        cr.paint_with_alpha(self._fade_alpha)

    def _rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + r,     y + r,     r, math.pi,       1.5 * math.pi)
        cr.arc(x + w - r, y + r,     r, 1.5 * math.pi, 2   * math.pi)
        cr.arc(x + w - r, y + h - r, r, 0,             0.5 * math.pi)
        cr.arc(x + r,     y + h - r, r, 0.5 * math.pi, math.pi)
        cr.close_path()

    # ── Called from worker thread via GLib ────────────────────────────────────
    def set_status(self, text):
        GLib.idle_add(self._set_status_idle, text)

    def _set_status_idle(self, text):
        self._status_text = text
        return False

    def finish(self, success=True):
        self._success = success
        GLib.idle_add(self._finish_idle)

    def _finish_idle(self):
        self._done = True
        return False


# ── Backend management ────────────────────────────────────────────────────────
def start_server():
    """Start uvicorn in the background."""
    env = os.environ.copy()
    env["PYTHONPATH"] = SCRIPT_DIR
    proc = subprocess.Popen(
        SERVER_CMD,
        cwd=SCRIPT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def poll_until_ready(splash: SplashWindow):
    """Poll /health in a background thread until agent_ready==True."""
    time.sleep(1.0)  # give the process a moment to boot

    while True:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as resp:
                data = json.loads(resp.read())
            if data.get("agent_ready"):
                splash.set_status("✅ Agent ready! Opening Ashborn IDE…")
                time.sleep(0.8)
                splash.finish(success=True)
                # Open VS Codium / VS Code pointing at the workspace
                subprocess.Popen([VSCODE_BIN, SCRIPT_DIR])
                return
            else:
                splash.set_status("Server up — loading AI agent…")
        except Exception:
            pass  # server not yet up — keep cycling messages from timer

        time.sleep(POLL_INTERVAL)


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    # 1. Kill any stale server on port 8765 first
    subprocess.run(["fuser", "-k", "8765/tcp"], stderr=subprocess.DEVNULL)
    time.sleep(0.3)

    # 2. Show splash
    splash = SplashWindow()

    # 3. Start the backend server
    server_proc = start_server()

    # 4. Poll in a daemon thread (won't block GTK main loop)
    t = threading.Thread(target=poll_until_ready, args=(splash,), daemon=True)
    t.start()

    # 5. Run GTK — blocks until splash fades out
    Gtk.main()

    # 6. Make sure the server keeps running after we exit
    #    (it's a child process; we just detach)
    try:
        server_proc.wait(timeout=0)  # non-blocking
    except subprocess.TimeoutExpired:
        pass  # server is still alive — good


if __name__ == "__main__":
    main()
