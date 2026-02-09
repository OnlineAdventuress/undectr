#!/bin/bash
# Launch script for macOS - fixes sandbox issues

# Fix sandbox permission if needed
if [ -f node_modules/electron/dist/chrome-sandbox ]; then
    chmod 4755 node_modules/electron/dist/chrome-sandbox 2>/dev/null || true
fi

# Set environment to disable sandbox on Linux
export ELECTRON_DISABLE_SANDBOX=1

# Launch Electron
npx electron .
