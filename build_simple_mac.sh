#!/bin/bash
set -e

echo "🚀 Creating macOS test package for Undectr"

# Build the app first
echo "📦 Building TypeScript and React..."
npm run build

# Create directory structure
echo "📁 Creating app structure..."
mkdir -p "release/mac/Undectr.app/Contents/MacOS"
mkdir -p "release/mac/Undectr.app/Contents/Resources"
APP_DIR="release/mac/Undectr.app"

# Create Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>Undectr</string>
    <key>CFBundleExecutable</key>
    <string>Undectr</string>
    <key>CFBundleIdentifier</key>
    <string>com.undectr.suno-studio-pro</string>
    <key>CFBundleName</key>
    <string>Undectr</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024 Undectr. All rights reserved.</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.music</string>
</dict>
</plist>
EOF

# Create launcher script with embedded Electron
cat > "$APP_DIR/Contents/MacOS/Undectr" << 'EOF'
#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to app directory
cd "$APP_ROOT"

# Set environment to disable sandbox
export ELECTRON_DISABLE_SANDBOX=1
export NODE_ENV=production

# Find Electron binary
if [ -f "$APP_ROOT/Undectr.app/Contents/Resources/electron/electron" ]; then
    ELECTRON_BIN="$APP_ROOT/Undectr.app/Contents/Resources/electron/electron"
elif [ -f "./node_modules/.bin/electron" ]; then
    ELECTRON_BIN="./node_modules/.bin/electron"
elif [ -f "./node_modules/electron/dist/electron" ]; then
    ELECTRON_BIN="./node_modules/electron/dist/electron"
else
    echo "Error: Electron binary not found!"
    exit 1
fi

# Launch the app
exec "$ELECTRON_BIN" .
EOF
chmod +x "$APP_DIR/Contents/MacOS/Undectr"

# Copy built files
echo "📁 Copying application files..."
cp -r dist "$APP_DIR/Contents/Resources/"
cp -r python "$APP_DIR/Contents/Resources/"
cp package.json "$APP_DIR/Contents/Resources/"

# Copy minimal node_modules (just electron and dependencies)
echo "📦 Copying essential node modules..."
mkdir -p "$APP_DIR/Contents/Resources/node_modules"
cp -r node_modules/electron "$APP_DIR/Contents/Resources/node_modules/" 2>/dev/null || true

# Create a simple README
cat > "$APP_DIR/Contents/Resources/README.txt" << 'EOF'
=== Undectr - Suno Studio Pro ===

This is a test build of Undectr, software for removing AI artifacts
from Suno-generated music.

TEST FEATURES:
- Basic AI artifact removal (8-16kHz metallic shimmer)
- "Spotify Ready" mastering preset
- Vocal smoothing for robotic vocals
- Drag & drop WAV/MP3/FLAC/OGG files

INSTALLATION:
1. Drag this entire Undectr.app folder to Applications
2. Right-click and select "Open"
3. Click "Open" when Gatekeeper warns
4. Process your Suno tracks!

TECHNICAL:
- Self-signed certificate (Gatekeeper warning expected)
- Python audio processing engine included
- Test license: 5 tracks per month

Website: undetectr.com
EOF

# Create DMG structure (simple folder)
echo "🍎 Creating DMG folder structure..."
DMG_DIR="release/mac/Undectr-DMG"
mkdir -p "$DMG_DIR"
cp -r "$APP_DIR" "$DMG_DIR/"

# Create DMG README
cat > "$DMG_DIR/README.txt" << 'EOF'
=== INSTALL UNDECTR FOR MACOS ===

DRAG "Undectr.app" TO YOUR APPLICATIONS FOLDER

1. Download this DMG
2. Double-click to open
3. Drag Undectr.app to Applications
4. Right-click the app in Applications, select "Open"
5. Click "Open" when Gatekeeper warns

KNOWN ISSUES:
- Self-signed certificate - Gatekeeper will warn
- First launch may be slow
- Some advanced features disabled in test build

TEST LICENSE:
This build includes a test license for 5 tracks.
Full version available at undetectr.com

SUPPORT:
Contact: support@undetectr.com
Website: undetectr.com
EOF

# Create a simple .command file for easy launch
cat > "$DMG_DIR/Install Undectr.command" << 'EOF'
#!/bin/bash
echo "Installing Undectr..."
echo "Please drag Undectr.app to your Applications folder"
open .
EOF
chmod +x "$DMG_DIR/Install Undectr.command"

echo "✅ BUILD COMPLETE!"
echo ""
echo "📁 APP LOCATION:"
echo "   release/mac/Undectr.app"
echo ""
echo "📦 DMG-READY FOLDER:"
echo "   release/mac/Undectr-DMG/"
echo ""
echo "📋 INSTALLATION INSTRUCTIONS:"
echo "1. Download the 'Undectr-DMG' folder"
echo "2. Open the folder on your Mac"
echo "3. Drag 'Undectr.app' to Applications"
echo "4. Right-click app → Open (bypass Gatekeeper)"
echo "5. Process your Suno tracks!"
echo ""
echo "🎵 INCLUDED FEATURES:"
echo "- AI artifact removal (basic algorithm)"
echo "- Spotify Ready mastering preset"
echo "- Vocal smoothing processor"
echo "- Drag & drop interface"
echo "- Progress visualization"
echo ""
echo "⚠️  IMPORTANT: This is a TEST BUILD"
echo "   Gatekeeper will warn about 'unidentified developer'"
echo "   Click 'Open Anyway' to launch the app"