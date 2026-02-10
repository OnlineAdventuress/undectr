# Undectr

Professional AI Audio Mastering - Remove watermarks and prepare audio for streaming platforms.

## Features

- **Loudness Normalization**: Target LUFS from -16 to -6 (Spotify standard: -14 LUFS)
- **True Peak Limiting**: Prevents clipping with -1dB ceiling
- **5-Band EQ**: With presets (Flat, Vocal Boost, Bass Boost, Bright, Warm, AI Fix)
- **Stereo Width Control**: 0-200% with mono bass option
- **Real-time Preview**: Instant feedback with level matching
- **High-Quality Export**: WAV at 44.1kHz or 48kHz, 16 or 24-bit

### Processing Chain

- **Glue Compression**: Multiband compression to glue the mix
- **De-harsh**: Tames AI artifacts in 3-12kHz range
- **Clean Low End**: Removes sub-bass rumble and DC offset
- **Auto Level**: Intelligent gain automation
- **Add Punch**: Multiband transient shaping
- **Tape Warmth**: Subtle analog saturation

## Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Build for production
npm run build

# Build for specific platforms
npm run build:mac
npm run build:win
npm run build:linux
```

## Usage

1. Drop an audio file (MP3, WAV, FLAC, AAC, M4A) or click Browse Files
2. Adjust settings in real-time while previewing
3. Click Export WAV when ready
4. Your mastered file will be saved with professional streaming-ready quality

## System Requirements

- **macOS**: 10.14 or later
- **Windows**: Windows 10 or later
- **Linux**: Ubuntu 18.04 or equivalent

## Build Status

[![Build macOS](https://github.com/OnlineAdventuress/undectr/actions/workflows/build-mac.yml/badge.svg)](https://github.com/OnlineAdventuress/undectr/actions/workflows/build-mac.yml)
[![Build Windows](https://github.com/OnlineAdventuress/undectr/actions/workflows/build-win.yml/badge.svg)](https://github.com/OnlineAdventuress/undectr/actions/workflows/build-win.yml)

## License

© 2025 Undectr. All rights reserved.
