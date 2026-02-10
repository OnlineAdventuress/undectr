import React, { useState } from 'react';

// Type declarations for Electron API
declare global {
  interface Window {
    api: {
      getLicenseInfo: () => Promise<any>;
      getUsage: () => Promise<any>;
      processAudio: (filePath: string, settings: any) => Promise<any>;
      openFileDialog: () => Promise<string | null>;
      openFolderDialog: () => Promise<string | null>;
      checkLicense: (licenseKey: string) => Promise<any>;
      activateLicense: (licenseKey: string, email: string) => Promise<any>;
      getAppVersion: () => Promise<any>;
    };
  }
}

// Simple icon replacements
const FileAudio = () => <span>🎵</span>;
const Settings = () => <span>⚙️</span>;
const Sparkles = () => <span>✨</span>;
const Upload = () => <span>📤</span>;
const Play = () => <span>▶️</span>;

function App() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [activeTab, setActiveTab] = useState<'process' | 'settings'>('process');

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    const audioFiles = droppedFiles.filter(file => 
      file.type.startsWith('audio/') || file.name.match(/\.(wav|mp3|flac|ogg)$/i)
    );
    setFiles(prev => [...prev, ...audioFiles]);
  };

  const handleBrowseFiles = async () => {
    try {
      // @ts-ignore - window.api is injected by preload
      const filePath = await window.api.openFileDialog();
      if (filePath) {
        // Create a File object from the path (we'll need to read it via IPC)
        const fileName = filePath.split('/').pop() || filePath.split('\\').pop() || 'unknown';
        const mockFile = new File([], fileName, { type: 'audio/mpeg' });
        // Store the actual path separately for processing
        (mockFile as any).path = filePath;
        setFiles(prev => [...prev, mockFile]);
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err);
    }
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    
    setIsProcessing(true);
    
    // Simulate processing
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    alert(`Processed ${files.length} file(s)! Check the output folder.`);
    setIsProcessing(false);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black text-gray-100 p-6">
      {/* Header */}
      <header className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Sparkles />
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text text-transparent">
              Undectr
            </h1>
          </div>
          <div className="flex items-center space-x-4">
            <span className="px-3 py-1 bg-green-900/30 text-green-400 rounded-full text-sm">
              Free Trial: 5 tracks remaining
            </span>
            <button className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg hover:opacity-90 transition">
              Upgrade
            </button>
          </div>
        </div>
        <p className="text-gray-400 mt-2">Remove AI artifacts • Master tracks • Separate stems • 100% local processing</p>
      </header>

      {/* Main Content */}
      <div className="flex space-x-6">
        {/* Sidebar */}
        <div className="w-64 space-y-2">
          <button
            onClick={() => setActiveTab('process')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
              activeTab === 'process' 
                ? 'bg-gray-800 text-white' 
                : 'hover:bg-gray-800/50 text-gray-300'
            }`}
          >
            <FileAudio />
            <span>Process Audio</span>
          </button>
          
          <button
            onClick={() => setActiveTab('settings')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
              activeTab === 'settings' 
                ? 'bg-gray-800 text-white' 
                : 'hover:bg-gray-800/50 text-gray-300'
            }`}
          >
            <Settings />
            <span>Settings</span>
          </button>
        </div>

        {/* Main Panel */}
        <div className="flex-1">
          {activeTab === 'process' ? (
            <div className="space-y-6">
              {/* Drop Zone */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleFileDrop}
                className="border-2 border-dashed border-gray-700 rounded-2xl p-12 text-center hover:border-purple-500 transition cursor-pointer"
              >
                <Upload />
                <h3 className="text-xl font-semibold mb-2">Drop Suno AI audio here</h3>
                <p className="text-gray-400 mb-6">Supports WAV, MP3, FLAC, OGG</p>
                <button 
                  onClick={handleBrowseFiles}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg hover:opacity-90 transition"
                >
                  Browse Files
                </button>
              </div>

              {/* File List */}
              {files.length > 0 && (
                <div className="bg-gray-800/50 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4">Files to Process</h3>
                  <div className="space-y-3">
                    {files.map((file, index) => (
                      <div key={index} className="flex items-center justify-between bg-gray-900/50 p-4 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <FileAudio />
                          <div>
                            <p className="font-medium">{file.name}</p>
                            <p className="text-sm text-gray-400">
                              {(file.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() => removeFile(index)}
                          className="text-red-400 hover:text-red-300 transition"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Process Button */}
                  <div className="mt-6">
                    <button
                      onClick={handleProcess}
                      disabled={isProcessing || files.length === 0}
                      className="w-full py-4 bg-gradient-to-r from-green-600 to-emerald-600 rounded-xl font-semibold text-lg flex items-center justify-center space-x-3 hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isProcessing ? (
                        <>
                          <div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          <span>Processing...</span>
                        </>
                      ) : (
                        <>
                          <Play />
                          <span>Process {files.length} File(s)</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Features */}
              <div className="grid grid-cols-3 gap-6">
                <div className="bg-gray-800/30 p-6 rounded-xl">
                  <div className="h-12 w-12 bg-purple-900/30 rounded-lg flex items-center justify-center mb-4">
                    <Sparkles />
                  </div>
                  <h4 className="font-semibold mb-2">AI Artifact Removal</h4>
                  <p className="text-sm text-gray-400">Remove metallic shimmer and robotic vocals from Suno AI tracks</p>
                </div>
                
                <div className="bg-gray-800/30 p-6 rounded-xl">
                  <div className="h-12 w-12 bg-blue-900/30 rounded-lg flex items-center justify-center mb-4">
                    <FileAudio />
                  </div>
                  <h4 className="font-semibold mb-2">Professional Mastering</h4>
                  <p className="text-sm text-gray-400">Genre-specific mastering presets for radio-ready sound</p>
                </div>
                
                <div className="bg-gray-800/30 p-6 rounded-xl">
                  <div className="h-12 w-12 bg-green-900/30 rounded-lg flex items-center justify-center mb-4">
                    <Settings />
                  </div>
                  <h4 className="font-semibold mb-2">Stem Separation</h4>
                  <p className="text-sm text-gray-400">Separate vocals, drums, bass, and other instruments</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gray-800/30 rounded-xl p-8">
              <h2 className="text-2xl font-semibold mb-6">Settings</h2>
              
              <div className="space-y-6">
                <div>
                  <h3 className="font-medium mb-3">Output Settings</h3>
                  <div className="space-y-4">
                    <label className="flex items-center space-x-3">
                      <input type="checkbox" className="rounded bg-gray-700" defaultChecked />
                      <span>Save processed files to separate folder</span>
                    </label>
                    
                    <label className="flex items-center space-x-3">
                      <input type="checkbox" className="rounded bg-gray-700" />
                      <span>Keep original files</span>
                    </label>
                    
                    <div>
                      <label className="block text-sm mb-2">Output Format</label>
                      <select className="w-full bg-gray-700 rounded-lg px-4 py-2">
                        <option>WAV (Lossless)</option>
                        <option>MP3 (320kbps)</option>
                        <option>FLAC</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-medium mb-3">Processing Settings</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm mb-2">Artifact Removal Intensity</label>
                      <input type="range" min="0" max="100" defaultValue="70" className="w-full" />
                    </div>
                    
                    <div>
                      <label className="block text-sm mb-2">Mastering Preset</label>
                      <select className="w-full bg-gray-700 rounded-lg px-4 py-2">
                        <option>Spotify Ready</option>
                        <option>YouTube Ready</option>
                        <option>Club Master</option>
                        <option>Radio Ready</option>
                        <option>Custom</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-medium mb-3">License</h3>
                  <div className="space-y-4">
                    <div className="bg-gray-900/50 p-4 rounded-lg">
                      <p className="text-sm text-gray-400">Current Plan</p>
                      <p className="font-semibold text-green-400">Free Trial (5 tracks remaining)</p>
                    </div>
                    
                    <div>
                      <label className="block text-sm mb-2">License Key</label>
                      <div className="flex space-x-2">
                        <input 
                          type="text" 
                          placeholder="Enter your license key" 
                          className="flex-1 bg-gray-700 rounded-lg px-4 py-2"
                        />
                        <button className="px-6 py-2 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg">
                          Activate
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-12 pt-6 border-t border-gray-800 text-center text-gray-500 text-sm">
        <p>Undectr • 100% local processing • No data sent to servers</p>
        <p className="mt-1">Version 1.0.0 • Made with ❤️ for Suno AI creators</p>
      </footer>
    </div>
  );
}

export default App;