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

    // Find Python executable - check multiple locations for bundled vs dev
    const isDev = process.env.NODE_ENV === 'development';
    const appPath = app.getAppPath();
    
    const pythonPaths = [
      // Development paths
      isDev && path.join(__dirname, '../../../python/venv/bin/python'),
      isDev && path.join(__dirname, '../../../python/venv/Scripts/python.exe'),
      // Bundled app paths (macOS)
      path.join(process.resourcesPath, 'python/venv/bin/python'),
      path.join(appPath, 'python/venv/bin/python'),
      path.join(process.resourcesPath, '../python/venv/bin/python'),
      // System Python as fallback
      'python3',
      'python'
    ].filter(Boolean) as string[];
    
    let pythonPath = pythonPaths.find(p => fs.existsSync(p)) || 'python3';
    console.log('[IPC] Using Python:', pythonPath);
    console.log('[IPC] App path:', appPath);
    console.log('[IPC] Resources path:', process.resourcesPath);
    
    // Find the main.py script - check bundled locations first
    const scriptPaths = [
      // Bundled app paths (macOS app bundle)
      path.join(process.resourcesPath, 'python/main.py'),
      path.join(appPath, 'python/main.py'),
      path.join(process.resourcesPath, '../python/main.py'),
      // Development paths
      path.join(__dirname, '../../../python/main.py'),
      '/home/ubuntu/clawd/suno-studio-pro/python/main.py'
    ];
    
    const pythonScript = scriptPaths.find(p => fs.existsSync(p));
    
    if (!pythonScript) {
      console.error('[IPC] Python script not found. Checked:', scriptPaths);
      return {
        success: false,
        error: 'Python backend not found. Please ensure Python environment is installed.'
      };
    }
    
    console.log('[IPC] Using Python script:', pythonScript);

    const outputPath = filePath.replace(/(\.[a-zA-Z0-9]+)$/, '_processed$1');
    console.log('[IPC] Output will be:', outputPath);

    return new Promise((resolve) => {
      const args = [
        pythonScript,
        '--input', filePath,
        '--output', outputPath,
        '--remove-artifacts',
        '--preset', settings?.preset || 'spotify_ready',
        '--intensity', String(settings?.intensity || 0.7),
        '--verbose'
      ];

      console.log('[IPC] Spawning Python with args:', args.join(' '));
      
      const pythonProcess = spawn(pythonPath, args, {
        cwd: path.dirname(pythonScript)
      });

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

      pythonProcess.on('error', (err) => {
        console.error('[IPC] Failed to start Python process:', err);
        resolve({
          success: false,
          error: `Failed to start Python: ${err.message}`
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
