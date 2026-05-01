#!/bin/bash
# install_extension.sh
# Compiles and installs the Ashborn VS Code extension.

set -e

echo "🔥 Building Ashborn VS Code Extension..."

cd vscode-extension

echo "📦 Installing dependencies..."
npm install

echo "🔨 Compiling TypeScript..."
npm run compile

echo "📦 Installing extension into VS Code directly..."
EXT_DIR="$HOME/.vscode/extensions/ashborn-agent-1.0.0"
rm -rf "$EXT_DIR"
mkdir -p "$EXT_DIR"

# Copy essential files
cp -r package.json tsconfig.json media out "$EXT_DIR/"
# Copy node_modules too, but vsce normally strips devDependencies.
# For direct install, we can copy the whole node_modules
cp -r node_modules "$EXT_DIR/"

echo "✅ Extension installed successfully to $EXT_DIR!"
echo "Please reload your VS Code window (Ctrl+Shift+P -> Developer: Reload Window) to activate Ashborn Agent."
