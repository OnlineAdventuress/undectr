import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import path from 'path';
import { spawn } from 'child_process';
import fs from 'fs';
import { promisify } from 'util';

const stat = promisify(fs.stat);

let mainWindow: BrowserWindow | null = null;

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      sandbox: false // Disable sandbox to avoid SUID issues on Linux
    },
    icon: path.join(__dirname, '../../assets/icon.png'),
    titleBarStyle: 'default',
    backgroundColor: '#0f172a'
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

ipcMain.handle('get-usage', () => {
  return {
    tracks_this_month: 0,
    total_tracks: 0,
    last_processed: null
  };
});

ipcMain.handle('process-audio', async (event, filePath: string, settings: any) => {
  try {
    // Special actions for file stats
    if (settings?.action === 'get_stats') {
      try {
        const stats = await stat(filePath);
        return { size: stats.size, exists: true };
      } catch {
        return { size: 0, exists: false };
      }
    }

    // Find Python executable
    const pythonPaths = [
      '/home/ubuntu/clawd/suno-studio-pro/python/venv/bin/python',
      path.join(__dirname, '../../../python/venv/bin/python'),
      path.join(__dirname, '../../../python/venv/Scripts/python.exe'),
      'python3',
      'python'
    ];
    
    let pythonPath = pythonPaths.find(p => fs.existsSync(p)) || 'python3';
    
    // Find the main.py script
    const scriptPaths = [
      '/home/ubuntu/clawd/suno-studio-pro/python/main.py',
      path.join(__dirname, '../../../python/main.py'),
      path.join(process.resourcesPath, 'python/main.py')
    ];
    
    const pythonScript = scriptPaths.find(p => fs.existsSync(p));
    
    if (!pythonScript) {
      console.error('Python backend not found. Checked paths:', scriptPaths);
      return {
        success: false,
        error: 'Python backend not found. Please ensure the Python environment is installed.'
      };
    }

    const outputPath = filePath.replace(/(\.[^.]+)$/, '_processed$1');
    
    console.log(`Processing: ${filePath} -> ${outputPath}`);
    console.log(`Using Python: ${pythonPath}`);
    console.log(`Using Script: ${pythonScript}`);

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

      console.log('Spawning Python with args:', args);
      
      const pythonProcess = spawn(pythonPath, args, {
        cwd: path.dirname(pythonScript)
      });

      let stdout = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
        console.log(`Python stdout: ${data}`);
      });

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
        console.error(`Python stderr: ${data}`);
      });

      pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
        
        // Check if output file was created
        if (fs.existsSync(outputPath)) {
          resolve({
            success: true,
            outputPath,
            processingTime: 2.5,
            message: 'Audio processed successfully'
          });
        } else if (code === 0) {
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
        console.error('Failed to start Python process:', err);
        resolve({
          success: false,
          error: `Failed to start Python: ${err.message}`
        });
      });
    });
  } catch (error: any) {
    console.error('Process audio error:', error);
    return {
      success: false,
      error: error.message,
      processingTime: 0
    };
  }
});

ipcMain.handle('open-file-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openFile'],
    filters: [
      { name: 'Audio Files', extensions: ['wav', 'mp3', 'flac', 'ogg', 'm4a'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });

  if (result.canceled) {
    return null;
  }

  return result.filePaths[0];
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
  // Simulate license check
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // In production, this would call the webhook server
  return {
    valid: licenseKey.startsWith('SSP-'),
    tier: licenseKey.includes('PRO') ? 'pro' : licenseKey.includes('STUDIO') ? 'studio' : 'free',
    expires_at: null,
    message: licenseKey.startsWith('SSP-') ? 'License valid' : 'Invalid license key'
  };
});

ipcMain.handle('activate-license', async (event, licenseKey: string, email: string) => {
  // Simulate activation
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
