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

echo "📦 Packaging extension..."
npx vsce package --no-dependencies

VSIX_FILE=$(ls *.vsix | tail -n 1)

if [ -z "$VSIX_FILE" ]; then
    echo "❌ Failed to package extension."
    exit 1
fi

echo "🚀 Installing extension into VS Code..."
code --install-extension "$VSIX_FILE" --force

echo "✅ Extension installed successfully!"
echo "Reload VS Code to start using the Ashborn Agent."
