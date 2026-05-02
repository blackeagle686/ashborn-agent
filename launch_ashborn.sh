#!/usr/bin/env bash
# launch_ashborn.sh
# Launcher for Ashborn Agent — shows splash screen, starts server, then opens VS Codium.

set -e
cd "$(dirname "$0")"

echo "🔥 Launching Ashborn Agent..."
exec python3 launch.py "$@"
