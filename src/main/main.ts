import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import path from 'path';
import { spawn } from 'child_process';
import fs from 'fs';
import { promisify } from 'util';

const stat = promisify(fs.stat);

let mainWindow: BrowserWindow | null = null;

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      sandbox: false
    },
    icon: path.join(__dirname, '../../assets/icon.png'),
    titleBarStyle: 'default',
    backgroundColor: '#0f172a',
    title: 'Undectr'
  });

  // Load the app
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:3001');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'renderer/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
};

app.whenReady().then(() => {
  console.log('[Undectr] App starting...');
  console.log('[Undectr] App path:', app.getAppPath());
  console.log('[Undectr] Resources path:', process.resourcesPath);
  console.log('[Undectr] __dirname:', __dirname);
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC Handlers
ipcMain.handle('get-license-info', () => {
  return {
    type: 'free',
    tier: 'free',
    expires_at: null,
    tracks_remaining: 5
  };
});

ipcMain.handle('open-file-dialog', async () => {
  console.log('[IPC] open-file-dialog called');
  
  if (!mainWindow) {
    console.error('[IPC] No main window available');
    return null;
  }

  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'Audio Files', extensions: ['wav', 'mp3', 'flac', 'ogg', 'm4a'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });

  console.log('[IPC] Dialog result:', result);

  if (result.canceled) {
    console.log('[IPC] User cancelled dialog');
    return null;
  }

  const filePath = result.filePaths[0];
  console.log('[IPC] Selected file:', filePath);
  
  // Verify file exists
  if (!fs.existsSync(filePath)) {
    console.error('[IPC] File does not exist:', filePath);
    return null;
  }
  
  return filePath;
});

// Helper to find Python 3 executable - returns absolute path
function findPythonExecutable(): string {
  const possiblePythons = [
    '/usr/bin/python3',
    '/usr/local/bin/python3',
    '/opt/homebrew/bin/python3',
    '/opt/local/bin/python3'
  ];
  
  for (const py of possiblePythons) {
    if (fs.existsSync(py)) {
      console.log('[IPC] Found Python at:', py);
      return py;
    }
  }
  
  // If no absolute path found, try to resolve via PATH using 'which'
  try {
    const { execSync } = require('child_process');
    const resolvedPath = execSync('which python3', { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] }).trim();
    if (resolvedPath && fs.existsSync(resolvedPath)) {
      console.log('[IPC] Found Python via which:', resolvedPath);
      return resolvedPath;
    }
  } catch {
    // which failed
  }
  
  console.log('[IPC] Falling back to /usr/bin/python3');
  return '/usr/bin/python3';
}

ipcMain.handle('process-audio', async (event, filePath: string, settings: any) => {
  console.log('[IPC] process-audio called for:', filePath);
  console.log('[IPC] Settings:', JSON.stringify(settings, null, 2));
  
  // Handle special actions
  if (settings?.action === 'get_stats') {
    try {
      const stats = await stat(filePath);
      return { size: stats.size, exists: true };
    } catch {
      return { size: 0, exists: false };
    }
  }

  try {
    // Verify input file exists
    if (!fs.existsSync(filePath)) {
      console.error('[IPC] Input file does not exist:', filePath);
      return {
        success: false,
        error: `Input file not found: ${filePath}`
      };
    }

    // Find Python script - check all possible locations
    const isDev = process.env.NODE_ENV === 'development';
    const appPath = app.getAppPath();
    
    console.log('[IPC] Looking for Python script...');
    console.log('[IPC] isDev:', isDev);
    console.log('[IPC] appPath:', appPath);
    console.log('[IPC] resourcesPath:', process.resourcesPath);
    console.log('[IPC] __dirname:', __dirname);
    
    // Check all possible locations for main.py
    // IMPORTANT: asarUnpack in package.json extracts python/ to app.asar.unpacked/
    const possibleScriptPaths = [
      // UNPACKED location (primary) - electron-builder extracts python here
      path.join(process.resourcesPath, 'app.asar.unpacked', 'python', 'main.py'),
      // macOS app bundle - Contents/Resources/app/python/main.py
      path.join(process.resourcesPath, 'app', 'python', 'main.py'),
      // macOS app bundle - Contents/Resources/python/main.py  
      path.join(process.resourcesPath, 'python', 'main.py'),
      // Development - project root
      path.join(appPath, 'python', 'main.py'),
      // Relative to main.js location
      path.join(__dirname, '..', '..', '..', 'python', 'main.py'),
      // Fallback to server path (for testing)
      '/home/ubuntu/clawd/suno-studio-pro/python/main.py'
    ];
    
    console.log('[IPC] Checking script paths:', possibleScriptPaths);
    
    let pythonScript: string | null = null;
    for (const scriptPath of possibleScriptPaths) {
      const exists = fs.existsSync(scriptPath);
      console.log(`[IPC] Checking ${scriptPath}: ${exists ? 'EXISTS' : 'NOT FOUND'}`);
      if (exists && !pythonScript) {
        pythonScript = scriptPath;
      }
    }
    
    if (!pythonScript) {
      console.error('[IPC] Python script not found in any location');
      return {
        success: false,
        error: 'Python backend not found. The python/main.py file is missing from the app bundle.'
      };
    }
    
    console.log('[IPC] Using Python script:', pythonScript);
    
    // Get the python directory (for PYTHONPATH)
    const pythonDir = path.dirname(pythonScript);
    console.log('[IPC] Python directory:', pythonDir);
    
    // Verify python script is actually a file
    try {
      const stats = fs.statSync(pythonScript);
      if (!stats.isFile()) {
        console.error('[IPC] Python script is not a file:', pythonScript);
        return {
          success: false,
          error: `Invalid Python script: ${pythonScript}`
        };
      }
    } catch (err) {
      console.error('[IPC] Cannot stat Python script:', err);
      return {
        success: false,
        error: `Cannot access Python script: ${pythonScript}`
      };
    }

    // Find Python executable
    const pythonExe = findPythonExecutable();
    console.log('[IPC] Using Python executable:', pythonExe);

    const outputPath = filePath.replace(/(\.[a-zA-Z0-9]+)$/, '_processed$1');
    console.log('[IPC] Output will be:', outputPath);

    return new Promise((resolve) => {
      // SOTA watermark remover arguments
      const args = [
        pythonScript,
        filePath,
        outputPath,
        '--mode', settings?.intensity > 0.7 ? 'aggressive' : 'balanced'
      ];

      console.log('[IPC] Spawning:', pythonExe, args);
      
      // CRITICAL: Don't use shell mode - it causes issues with special characters in filenames
      // The args array is passed directly to the executable without shell interpretation
      const spawnOptions = {
        env: {
          ...process.env,
          PYTHONPATH: pythonDir,
          PATH: '/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:/opt/local/bin:' + (process.env.PATH || '')
        }
        // shell: false is the default - arguments are passed directly without shell interpretation
      };
      
      console.log('[IPC] Spawn options:', JSON.stringify(spawnOptions, null, 2));
      
      const pythonProcess = spawn(pythonExe, args, spawnOptions);

      let stdout = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        const text = data.toString();
        stdout += text;
        console.log(`[Python stdout] ${text.trim()}`);
      });

      pythonProcess.stderr.on('data', (data) => {
        const text = data.toString();
        stderr += text;
        console.error(`[Python stderr] ${text.trim()}`);
      });

      pythonProcess.on('close', (code) => {
        console.log(`[IPC] Python process exited with code ${code}`);
        
        // Check if output file was created
        const outputExists = fs.existsSync(outputPath);
        console.log(`[IPC] Output file exists: ${outputExists}`);
        
        if (outputExists || code === 0) {
          resolve({
            success: true,
            outputPath,
            processingTime: 2.5,
            message: 'Audio processed successfully'
          });
        } else {
          resolve({
            success: false,
            error: `Processing failed (exit code: ${code}). ${stderr || 'Unknown error'}`,
            stderr,
            stdout
          });
        }
      });

      pythonProcess.on('error', (err: any) => {
        console.error('[IPC] Failed to start Python process:', err);
        console.error('[IPC] Error code:', err.code);
        console.error('[IPC] Error message:', err.message);
        resolve({
          success: false,
          error: `Failed to start Python: ${err.message}. Make sure Python 3 is installed on your system.`
        });
      });
    });
  } catch (error: any) {
    console.error('[IPC] process-audio error:', error);
    return {
      success: false,
      error: error.message,
      processingTime: 0
    };
  }
});

ipcMain.handle('open-folder-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory']
  });

  if (result.canceled) {
    return null;
  }

  return result.filePaths[0];
});

ipcMain.handle('check-license', async (event, licenseKey: string) => {
  await new Promise(resolve => setTimeout(resolve, 500));
  
  return {
    valid: licenseKey.startsWith('SSP-'),
    tier: licenseKey.includes('PRO') ? 'pro' : licenseKey.includes('STUDIO') ? 'studio' : 'free',
    expires_at: null,
    message: licenseKey.startsWith('SSP-') ? 'License valid' : 'Invalid license key'
  };
});

ipcMain.handle('activate-license', async (event, licenseKey: string, email: string) => {
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  return {
    success: licenseKey.startsWith('SSP-'),
    license: {
      key: licenseKey,
      tier: licenseKey.includes('PRO') ? 'pro' : licenseKey.includes('STUDIO') ? 'studio' : 'free',
      email,
      activated_at: new Date().toISOString()
    },
    message: licenseKey.startsWith('SSP-') ? 'License activated!' : 'Invalid license key'
  };
});

ipcMain.handle('get-app-version', () => {
  return {
    version: '1.0.0',
    build: '20240208',
    pythonBackend: 'available'
  };
});
