import { contextBridge, ipcRenderer } from 'electron';

// Simple API for the renderer
contextBridge.exposeInMainWorld('api', {
  // License info
  getLicenseInfo: () => ipcRenderer.invoke('get-license-info'),
  getUsage: () => ipcRenderer.invoke('get-usage'),
  
  // Audio processing
  processAudio: (filePath: string, settings: any) => 
    ipcRenderer.invoke('process-audio', filePath, settings),
  
  // File dialogs
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
  openFolderDialog: () => ipcRenderer.invoke('open-folder-dialog'),
  
  // License activation
  checkLicense: (licenseKey: string) => 
    ipcRenderer.invoke('check-license', licenseKey),
  activateLicense: (licenseKey: string, email: string) => 
    ipcRenderer.invoke('activate-license', licenseKey, email),
  
  // App info
  getAppVersion: () => ipcRenderer.invoke('get-app-version')
});