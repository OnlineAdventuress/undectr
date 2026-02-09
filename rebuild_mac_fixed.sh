#!/bin/bash
set -e

echo "🚀 Rebuilding Undectr app with fixed bundle structure..."

# Clean previous build
rm -rf release dist

# Build the app
echo "📦 Building TypeScript and React..."
npm run build

# Create proper macOS app bundle
echo "🍎 Creating macOS app bundle..."
APP_DIR="release/mac/Undectr.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

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
# Launch Undectr - Simple wrapper
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"

# Set environment
export ELECTRON_DISABLE_SANDBOX=1
export NODE_ENV=production

cd "$RESOURCES_DIR"

# Check if electron is available
if command -v electron >/dev/null 2>&1; then
    exec electron .
else
    echo "Electron not found. Please install: npm install -g electron"
    echo "Then launch again from Applications folder."
    exit 1
fi
EOF
chmod +x "$MACOS/Undectr"

# Copy built files
echo "📁 Copying application files..."
cp -r dist "$RESOURCES/"
cp -r python "$RESOURCES/"
cp package.json "$RESOURCES/"

# Create README
cat > "$RESOURCES/README.txt" << 'EOF'
=== Undectr - Suno Studio Pro ===

This is a test build of Undectr for removing AI artifacts
from Suno-generated music.

INSTALLATION:
1. Drag Undectr.app to Applications folder
2. Install Electron globally: npm install -g electron
3. Right-click app, select "Open"
4. Click "Open" when Gatekeeper warns

FEATURES:
- AI artifact removal (8-16kHz metallic shimmer)
- "Spotify Ready" mastering preset
- Vocal smoothing for robotic vocals
- Drag & drop audio processing

Website: undetectr.com
EOF

echo "✅ REBUILD COMPLETE!"
echo ""
echo "📁 APP LOCATION:"
echo "   release/mac/Undectr.app"
echo ""
echo "📋 INSTALLATION:"
echo "1. Download Undectr.app"
echo "2. Drag to Applications folder"
echo "3. Install Electron: npm install -g electron"
echo "4. Right-click app → Open (bypass Gatekeeper)"
echo ""
echo "🎯 FIXED: Bundle structure now correct"
echo "   Resources at: Undectr.app/Contents/Resources"
echo "   NOT: Undectr.app/Undectr.app/Contents/Resources"
echo ""
echo "⚠️  REQUIREMENT: User must install Electron globally"
echo "   Command: npm install -g electron"