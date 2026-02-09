import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import path from 'path';
import { spawn } from 'child_process';
import fs from 'fs';

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
    // Simulate Python processing
    const pythonScript = path.join(__dirname, '../../../python/main.py');
    
    if (fs.existsSync(pythonScript)) {
      const outputPath = filePath.replace(/(\.\w+)$/, '_processed$1');
      
      // In production, this would spawn the Python process
      // const pythonProcess = spawn('python', [pythonScript, '--input', filePath, '--output', outputPath]);
      
      // For now, simulate processing
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      return {
        success: true,
        outputPath,
        processingTime: 2.5,
        message: 'Audio processed successfully'
      };
    } else {
      throw new Error('Python backend not found');
    }
  } catch (error: any) {
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

  if ((result as any).canceled) {
    return null;
  }

  return (result as any).filePaths[0];
});

ipcMain.handle('open-folder-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory']
  });

  if ((result as any).canceled) {
    return null;
  }

  return (result as any).filePaths[0];
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