import { defineConfig } from 'vite';
import electron from 'vite-plugin-electron/simple';
import { resolve } from 'path';

const rootDir = __dirname;

export default defineConfig(({ command }) => ({
  // Use src/renderer as the root for the renderer process
  root: 'src/renderer',

  // Build with relative asset paths for Electron
  base: command === 'build' ? './' : '/',

  plugins: [
    electron({
      main: {
        entry: resolve(rootDir, 'src/main/main.js'),
        vite: {
          build: {
            outDir: resolve(rootDir, 'dist-electron'),
          },
        },
      },
      preload: {
        input: resolve(rootDir, 'src/main/preload.js'),
        vite: {
          build: {
            outDir: resolve(rootDir, 'dist-electron'),
          },
        },
      },
    }),
  ],
  build: {
    outDir: resolve(rootDir, 'dist'),
    emptyOutDir: true
  },
  server: {
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': 'require-corp'
    }
  },
  optimizeDeps: {
    exclude: ['@ffmpeg/ffmpeg', '@ffmpeg/util']
  }
}));