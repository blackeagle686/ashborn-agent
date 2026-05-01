#!/bin/bash
# verify_install.sh
# Tests the installer in a temporary directory.

set -e

TEST_DIR="$(pwd)/install_test"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

echo "🧪 Verifying Ashborn IDE Packaging & Installation..."

# Extract the distribution package
cd "$TEST_DIR"
tar -xzf ../dist/ashborn-ide-linux.tar.gz

# Patch install.sh to use the test directory instead of $HOME
sed -i "s|ASHBORN_DIR=\"\$HOME/.ashborn\"|ASHBORN_DIR=\"$TEST_DIR/ashborn_root\"|g" install.sh
sed -i "s|DESKTOP_FILE=\"\$HOME/.local/share/applications/ashborn.desktop\"|DESKTOP_FILE=\"$TEST_DIR/ashborn.desktop\"|g" install.sh

# Run the installer
# Note: This will download VSCodium (~100MB), so we might want to skip that in a quick test
# but let's see if it works.
bash install.sh

echo "✅ Verification complete!"
ls -R "$TEST_DIR/ashborn_root"
