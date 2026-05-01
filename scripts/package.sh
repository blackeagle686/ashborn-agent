#!/bin/bash
# package.sh
# Bundles Ashborn IDE into a distributable archive.

set -e

PROJECT_ROOT=$(pwd)
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build_temp"

echo "🔥 Starting Ashborn IDE Packaging..."

# 1. Clean up old builds
rm -rf "$DIST_DIR" "$BUILD_DIR"
mkdir -p "$DIST_DIR" "$BUILD_DIR"

# 2. Build VS Code Extension
echo "📦 Building VS Code Extension..."
cd "$PROJECT_ROOT/vscode-extension"
npm install
npm run compile
# Use local vsce if global fails
./node_modules/.bin/vsce package -o "$BUILD_DIR/ashborn-agent.vsix"

# 3. Package Backend
echo "📦 Packaging Python Backend..."
cd "$PROJECT_ROOT"
tar -czf "$BUILD_DIR/backend.tar.gz" \
    ashborn/ \
    requirements.txt \
    pyproject.toml \
    LICENSE \
    README.md

# 4. Prepare Installer and Assets
echo "📦 Preparing Installer..."
cp "$PROJECT_ROOT/scripts/install.sh" "$BUILD_DIR/install.sh"
chmod +x "$BUILD_DIR/install.sh"

# Find icon (assuming it's in a standard place or we have one)
# For now, let's look for the one mentioned in the .desktop file
ICON_PATH="/home/tlk/.local/share/icons/ashborn.svg"
if [ -f "$ICON_PATH" ]; then
    cp "$ICON_PATH" "$BUILD_DIR/ashborn.svg"
fi

# 5. Create Final Distribution Archive
echo "📦 Creating final distribution archive..."
cd "$BUILD_DIR"
tar -czf "$DIST_DIR/ashborn-ide-linux.tar.gz" .

echo "✅ Packaging complete!"
echo "📍 Location: $DIST_DIR/ashborn-ide-linux.tar.gz"
echo "🚀 You can now upload this file to your server."
