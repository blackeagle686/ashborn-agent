#!/usr/bin/env bash
# launch_ashborn.sh
# Launcher for Ashborn Agent — shows splash screen, starts server, then opens VS Codium.

set -e
# Save the original working directory
ORIGINAL_CWD=$(pwd)

cd "$(dirname "$0")"

echo "🔥 Launching Ashborn Agent..."
# Pass ORIGINAL_CWD to the python launcher
export ASHBORN_WORKSPACE_ROOT="$ORIGINAL_CWD"
exec python3 launch.py "$@"
