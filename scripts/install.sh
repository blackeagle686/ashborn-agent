#!/bin/bash
# install.sh
# Installer for Ashborn IDE Standalone.

set -e

echo "🐦‍🔥 Welcome to the Ashborn IDE Installer"
echo "----------------------------------------"

ASHBORN_DIR="$HOME/.ashborn"
BIN_DIR="$ASHBORN_DIR/ide-bin"
BACKEND_DIR="$ASHBORN_DIR/backend"
EXT_DIR="$ASHBORN_DIR/ide-extensions"
DATA_DIR="$ASHBORN_DIR/ide-data"

mkdir -p "$ASHBORN_DIR" "$BIN_DIR" "$BACKEND_DIR" "$EXT_DIR" "$DATA_DIR"

# 1. Download Standalone IDE (VSCodium)
echo "📥 Downloading standalone IDE (VSCodium)..."
# Get latest version tag from GitHub
VSC_TAG=$(curl -s https://api.github.com/repos/VSCodium/vscodium/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
VSC_VERSION=${VSC_TAG#v}
VSC_URL="https://github.com/VSCodium/vscodium/releases/download/$VSC_TAG/VSCodium-linux-x64-$VSC_VERSION.tar.gz"

echo "🔗 Fetching version $VSC_TAG..."
curl -L "$VSC_URL" -o vscodium.tar.gz

echo "📦 Extracting IDE..."
tar -xzf vscodium.tar.gz -C "$BIN_DIR" --strip-components=1
rm vscodium.tar.gz

# 2. Extract and Setup Backend
echo "📦 Setting up Ashborn Backend..."
tar -xzf backend.tar.gz -C "$BACKEND_DIR"

echo "🐍 Creating Python virtual environment..."
cd "$BACKEND_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
deactivate

# Get the directory where install.sh is located
INSTALL_SRC_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 3. Install VS Code Extension
echo "🧩 Installing Ashborn VS Code Extension..."
mkdir -p "$EXT_DIR/ashborn-agent"
unzip -q "$INSTALL_SRC_DIR/ashborn-agent.vsix" -d "$EXT_DIR/ashborn-agent"
# Move content from 'extension/' subfolder in VSIX to the root
mv "$EXT_DIR/ashborn-agent/extension/"* "$EXT_DIR/ashborn-agent/"
rm -rf "$EXT_DIR/ashborn-agent/extension"

# 4. Create Launcher Script
echo "🚀 Creating launcher script..."
LAUNCHER="$ASHBORN_DIR/ashborn-ide"
cat <<EOF > "$LAUNCHER"
#!/bin/bash
"$BIN_DIR/bin/codium" \\
    --user-data-dir "$DATA_DIR" \\
    --extensions-dir "$EXT_DIR" \\
    "\$@"
EOF
chmod +x "$LAUNCHER"
 
# 5. Create Desktop Entry
echo "🖥️  Installing Desktop entry..."
DESKTOP_FILE="$HOME/.local/share/applications/ashborn.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"

# Icon installation
if [ -f "ashborn.svg" ]; then
    mkdir -p "$HOME/.local/share/icons"
    cp ashborn.svg "$HOME/.local/share/icons/ashborn.svg"
    ICON_PATH="$HOME/.local/share/icons/ashborn.svg"
else
    ICON_PATH="code" # Fallback
fi

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=Ashborn IDE
Exec=$LAUNCHER %F
Icon=$ICON_PATH
StartupWMClass=VSCodium
Comment=The Autonomous AI Developer Environment
Categories=Development;IDE;
Terminal=false
Type=Application
GenericName=AI Code Editor
EOF

echo "----------------------------------------"
echo "✅ Ashborn IDE installed successfully!"
echo "🌟 You can now find 'Ashborn IDE' in your application menu."
echo "   Or run it from terminal: $LAUNCHER"
