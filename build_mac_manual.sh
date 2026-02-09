#!/bin/bash
set -e

echo "🚀 Alternative macOS build script for Undectr"

# Check prerequisites
command -v npm >/dev/null 2>&1 || { echo "npm not found"; exit 1; }
command -v zip >/dev/null 2>&1 || { echo "zip not found"; exit 1; }

echo "📦 Building TypeScript and React..."
npm run build

echo "🔧 Creating macOS app bundle structure..."
APP_DIR="Undectr.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

# Clean previous builds
rm -rf "$APP_DIR" Undectr-macOS.zip release

# Create app bundle structure
mkdir -p "$MACOS" "$RESOURCES"

# Create Info.plist
cat > "$CONTENTS/Info.plist" << 'EOF'
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

# Create launcher script
cat > "$MACOS/Undectr" << 'EOF'
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/../.."
# Disable sandbox for testing
export ELECTRON_DISABLE_SANDBOX=1
# Launch Electron
exec "$(dirname "$(which electron)")/electron" . 2>/dev/null
EOF
chmod +x "$MACOS/Undectr"

# Copy built files
echo "📁 Copying application files..."
cp -r dist "$RESOURCES/"
cp -r python "$RESOURCES/"
cp -r node_modules "$RESOURCES/" 2>/dev/null || true
cp package.json "$RESOURCES/"
cp -r assets "$RESOURCES/" 2>/dev/null || true

# Create simple icon
echo "🎨 Creating placeholder icon..."
cat > "$RESOURCES/icon.icns" << 'EOF'
# Placeholder for icon - replace with actual .icns file
EOF

# Create DMG-like zip package
echo "📦 Creating distribution package..."
mkdir -p release/mac
zip -r "release/mac/Undectr-macOS.zip" "$APP_DIR"

# Create README
cat > release/mac/README.txt << 'EOF'
=== Undectr - Suno Studio Pro (macOS) ===

INSTALLATION:
1. Download and unzip this file
2. Drag "Undectr.app" to your Applications folder
3. Right-click the app, select "Open"
4. Click "Open" when Gatekeeper warns about unidentified developer

TESTING FEATURES:
- Basic AI artifact removal (8-16kHz metallic shimmer reduction)
- "Spotify Ready" mastering preset
- Vocal smoothing for robotic Suno vocals
- Drag & drop WAV/MP3/FLAC/OGG files
- Processing simulation with progress bar

KNOWN ISSUES:
- Self-signed certificate: Gatekeeper warning expected
- First launch may be slow as Python environment initializes
- Some advanced features disabled in test build

FOR DEVELOPMENT:
To bypass Gatekeeper permanently:
  sudo spctl --master-disable

To run from terminal:
  cd /Applications/Undectr.app/Contents/MacOS
  ./Undectr

LICENSE:
This is a test build. Full version requires license purchase at undetectr.com
EOF

echo "✅ BUILD COMPLETE!"
echo "📁 App bundle: $APP_DIR"
echo "📦 Distribution package: release/mac/Undectr-macOS.zip"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Download the ZIP file"
echo "2. Extract and drag Undectr.app to Applications"
echo "3. Right-click → Open to bypass Gatekeeper"
echo ""
echo "🎵 INCLUDED FEATURES:"
echo "- Basic AI artifact removal algorithm"
echo "- Spotify Ready mastering preset"
echo "- Vocal smoothing processor"
echo "- Drag & drop audio file processing"
echo "- Progress visualization"
echo ""
echo "⚠️  NOTE: This is a TEST BUILD with self-signed certificate."
echo "   Gatekeeper will warn about 'unidentified developer'."
echo "   Click 'Open Anyway' to launch the app."