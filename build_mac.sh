#!/bin/bash
set -e

echo "🚀 Building Suno Studio Pro for macOS..."

# Install dependencies if needed
npm install

# Clean previous builds
rm -rf release dist

# Build the app
echo "📦 Building TypeScript and React..."
npm run build

# Create self-signed certificate for macOS development
echo "🔐 Creating self-signed certificate..."
if [ ! -f "macos.p12" ]; then
  openssl req -x509 -newkey rsa:4096 -keyout macos.key -out macos.crt -days 365 -nodes -subj "/C=US/ST=California/L=San Francisco/O=Undectr/CN=com.undectr.suno-studio-pro"
  openssl pkcs12 -export -out macos.p12 -inkey macos.key -in macos.crt -password pass:password
  echo "✅ Created self-signed certificate"
fi

# Set environment for self-signed build
export CSC_LINK="file://$(pwd)/macos.p12"
export CSC_KEY_PASSWORD="password"

# Build macOS app with self-signed certificate
echo "🍎 Building macOS app (.dmg)..."
npm run build:mac

# Check if build succeeded
if [ -f "release/mac/Suno Studio Pro-1.0.0.dmg" ]; then
  echo "✅ SUCCESS: macOS .dmg created!"
  echo "📁 Location: $(pwd)/release/mac/Suno Studio Pro-1.0.0.dmg"
  echo ""
  echo "📋 INSTALLATION INSTRUCTIONS FOR MACOS:"
  echo "========================================"
  echo "1. Download the .dmg file"
  echo "2. Double-click to open (Gatekeeper may warn)"
  echo "3. Click 'Open Anyway' when prompted"
  echo "4. Drag Suno Studio Pro to Applications folder"
  echo "5. Right-click app in Applications, select 'Open'"
  echo "6. Click 'Open' on the security warning"
  echo ""
  echo "🔧 To bypass Gatekeeper permanently:"
  echo "   sudo spctl --master-disable"
  echo ""
  echo "🎵 TESTING FEATURES INCLUDED:"
  echo "- Basic AI artifact removal"
  echo "- 'Spotify Ready' mastering preset"
  echo "- Vocal smoothing (basic)"
  echo "- Drag & drop audio processing"
  echo "- WAV, MP3, FLAC, OGG support"
else
  echo "❌ Build failed, check logs above"
  exit 1
fi