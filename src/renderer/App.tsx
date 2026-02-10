import React, { useState, useEffect } from 'react';

// Type for file with path
type AudioFile = {
  id: string;
  name: string;
  path: string;
  size: number;
  status: 'pending' | 'processing' | 'done' | 'error';
  outputPath?: string;
  error?: string;
};

// Declare Electron API
declare global {
  interface Window {
    api: {
      openFileDialog: () => Promise<string | null>;
      processAudio: (filePath: string, settings: any) => Promise<any>;
    };
  }
}

export default function App() {
  const [files, setFiles] = useState<AudioFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentFileIndex, setCurrentFileIndex] = useState(-1);
  const [logs, setLogs] = useState<string[]>([]);

  // Debug logging
  const log = (msg: string) => {
    console.log(msg);
    setLogs(prev => [...prev.slice(-9), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  // Browse files button
  const handleBrowse = async () => {
    log('Browse button clicked');
    
    if (!window.api) {
      alert('Error: Electron API not available');
      log('ERROR: window.api is undefined');
      return;
    }

    try {
      log('Calling window.api.openFileDialog()...');
      const filePath = await window.api.openFileDialog();
      log(`File dialog returned: ${filePath || 'null (cancelled)'}`);
      
      if (!filePath) {
        log('User cancelled file selection');
        return;
      }

      // Extract filename and estimate size
      const fileName = filePath.split(/[/\\]/).pop() || 'unknown';
      const newFile: AudioFile = {
        id: `file-${Date.now()}`,
        name: fileName,
        path: filePath,
        size: 0, // Will show as "Unknown" until we get stats
        status: 'pending'
      };

      setFiles(prev => {
        const updated = [...prev, newFile];
        log(`Added file to queue. Total files: ${updated.length}`);
        return updated;
      });

    } catch (err: any) {
      log(`ERROR in handleBrowse: ${err.message}`);
      alert('Failed to open file dialog: ' + err.message);
    }
  };

  // Process all files
  const handleProcess = async () => {
    log('Process button clicked');
    
    if (files.length === 0) {
      alert('Please select at least one file');
      log('No files to process');
      return;
    }

    if (!window.api) {
      alert('Error: Electron API not available');
      log('ERROR: window.api is undefined');
      return;
    }

    const pendingFiles = files.filter(f => f.status === 'pending');
    if (pendingFiles.length === 0) {
      alert('All files already processed');
      log('No pending files to process');
      return;
    }

    setIsProcessing(true);
    log(`Starting to process ${pendingFiles.length} pending files`);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.status !== 'pending') continue;

      setCurrentFileIndex(i);
      
      // Update status to processing
      setFiles(prev => prev.map((f, idx) => 
        idx === i ? { ...f, status: 'processing' } : f
      ));

      log(`Processing file ${i + 1}/${files.length}: ${file.name}`);

      try {
        const result = await window.api.processAudio(file.path, {
          remove_artifacts: true,
          mastering: true,
          preset: 'spotify_ready',
          intensity: 0.7,
          target_lufs: -14
        });

        log(`Python result for ${file.name}: ${JSON.stringify(result).slice(0, 200)}`);

        if (result.success) {
          setFiles(prev => prev.map((f, idx) => 
            idx === i ? { 
              ...f, 
              status: 'done', 
              outputPath: result.outputPath 
            } : f
          ));
          log(`✅ Successfully processed: ${file.name}`);
        } else {
          setFiles(prev => prev.map((f, idx) => 
            idx === i ? { 
              ...f, 
              status: 'error', 
              error: result.error || 'Processing failed' 
            } : f
          ));
          log(`❌ Failed to process: ${file.name} - ${result.error}`);
        }
      } catch (err: any) {
        setFiles(prev => prev.map((f, idx) => 
          idx === i ? { 
            ...f, 
            status: 'error', 
            error: err.message 
          } : f
        ));
        log(`❌ Exception processing ${file.name}: ${err.message}`);
      }
    }

    setIsProcessing(false);
    setCurrentFileIndex(-1);
    log('Processing complete');
  };

  // Remove file from queue
  const removeFile = (id: string) => {
    log(`Removing file: ${id}`);
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  // Clear processed files
  const clearCompleted = () => {
    log('Clearing completed files');
    setFiles(prev => prev.filter(f => f.status !== 'done'));
  };

  // Format file size
  const formatSize = (bytes: number) => {
    if (!bytes || bytes < 0) return 'Unknown size';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Open output folder
  const openOutput = (path: string) => {
    log(`Opening output: ${path}`);
    // In real app, this would open the folder
    alert(`File saved to:\n${path}`);
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)',
      color: '#f8fafc',
      padding: '24px',
      fontFamily: '-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif'
    }}>
      {/* Header */}
      <header style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h1 style={{ 
          fontSize: '2.5rem', 
          fontWeight: 'bold',
          background: 'linear-gradient(90deg, #a855f7, #3b82f6)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '8px'
        }}>
          Undectr
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '1.1rem' }}>
          Remove AI artifacts • Master your tracks
        </p>
      </header>

      {/* Main Content */}
      <div style={{ maxWidth: '700px', margin: '0 auto' }}>
        
        {/* Upload Area */}
        <div style={{
          border: '2px dashed #475569',
          borderRadius: '16px',
          padding: '48px',
          textAlign: 'center',
          background: 'rgba(30, 41, 59, 0.5)',
          marginBottom: '24px'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📤</div>
          <h3 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>
            Drop audio files here
          </h3>
          <p style={{ color: '#94a3b8', marginBottom: '20px' }}>
            WAV, MP3, FLAC supported
          </p>
          <button 
            onClick={handleBrowse}
            disabled={isProcessing}
            style={{
              background: 'linear-gradient(90deg, #a855f7, #3b82f6)',
              color: 'white',
              border: 'none',
              padding: '12px 32px',
              fontSize: '1rem',
              fontWeight: '600',
              borderRadius: '10px',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              opacity: isProcessing ? 0.6 : 1
            }}
          >
            Browse Files
          </button>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div style={{
            background: 'rgba(30, 41, 59, 0.5)',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '24px'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '16px'
            }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '600' }}>
                Files ({files.length})
              </h3>
              <button 
                onClick={clearCompleted}
                style={{
                  background: 'transparent',
                  border: '1px solid #475569',
                  color: '#94a3b8',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Clear Completed
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {files.map((file, index) => (
                <div 
                  key={file.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '12px',
                    background: file.status === 'processing' 
                      ? 'rgba(168, 85, 247, 0.1)' 
                      : file.status === 'done'
                      ? 'rgba(34, 197, 94, 0.1)'
                      : file.status === 'error'
                      ? 'rgba(239, 68, 68, 0.1)'
                      : 'rgba(15, 23, 42, 0.5)',
                    borderRadius: '8px',
                    border: `1px solid ${
                      file.status === 'processing' ? 'rgba(168, 85, 247, 0.3)' :
                      file.status === 'done' ? 'rgba(34, 197, 94, 0.3)' :
                      file.status === 'error' ? 'rgba(239, 68, 68, 0.3)' :
                      '#334155'
                    }`
                  }}
                >
                  <span style={{ marginRight: '12px', fontSize: '20px' }}>
                    {file.status === 'pending' ? '🎵' :
                     file.status === 'processing' ? '⏳' :
                     file.status === 'done' ? '✅' : '❌'}
                  </span>
                  
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{ 
                      fontWeight: '500', 
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {file.name}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      {formatSize(file.size)}
                      {file.status === 'processing' && currentFileIndex === index && ' • Processing...'}
                      {file.status === 'done' && ' • Complete'}
                      {file.status === 'error' && ` • Error: ${file.error}`}
                    </div>
                  </div>

                  {file.status === 'done' && file.outputPath && (
                    <button 
                      onClick={() => openOutput(file.outputPath!)}
                      style={{
                        background: 'rgba(34, 197, 94, 0.2)',
                        border: '1px solid rgba(34, 197, 94, 0.4)',
                        color: '#22c55e',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        marginRight: '8px',
                        fontSize: '0.8rem'
                      }}
                    >
                      Open
                    </button>
                  )}

                  <button 
                    onClick={() => removeFile(file.id)}
                    disabled={file.status === 'processing'}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#ef4444',
                      cursor: file.status === 'processing' ? 'not-allowed' : 'pointer',
                      fontSize: '1.2rem',
                      opacity: file.status === 'processing' ? 0.3 : 1
                    }}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Process Button */}
        {files.length > 0 && (
          <button 
            onClick={handleProcess}
            disabled={isProcessing || files.filter(f => f.status === 'pending').length === 0}
            style={{
              width: '100%',
              background: isProcessing 
                ? 'linear-gradient(90deg, #4b5563, #374151)' 
                : 'linear-gradient(90deg, #22c55e, #16a34a)',
              color: 'white',
              border: 'none',
              padding: '16px',
              fontSize: '1.1rem',
              fontWeight: '600',
              borderRadius: '12px',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            {isProcessing && (
              <span style={{ 
                display: 'inline-block',
                width: '20px',
                height: '20px',
                border: '2px solid rgba(255,255,255,0.3)',
                borderTopColor: 'white',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
            )}
            {isProcessing 
              ? `Processing ${files.filter(f => f.status === 'processing').length} file(s)...` 
              : `Process ${files.filter(f => f.status === 'pending').length} File(s)`
            }
          </button>
        )}

        {/* Debug Logs */}
        <div style={{
          background: 'rgba(0, 0, 0, 0.3)',
          borderRadius: '8px',
          padding: '12px',
          fontSize: '0.75rem',
          fontFamily: 'monospace',
          color: '#94a3b8',
          maxHeight: '150px',
          overflow: 'auto'
        }}>
          <div style={{ marginBottom: '8px', color: '#64748b', borderBottom: '1px solid #334155', paddingBottom: '4px' }}>
            Debug Console
          </div>
          {logs.length === 0 ? (
            <span style={{ opacity: 0.5 }}>No logs yet...</span>
          ) : (
            logs.map((log, i) => (
              <div key={i} style={{ marginBottom: '2px' }}>{log}</div>
            ))
          )}
        </div>

        {/* Features */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: '1fr 1fr', 
          gap: '16px',
          marginTop: '32px'
        }}>
          <div style={{
            background: 'rgba(168, 85, 247, 0.1)',
            border: '1px solid rgba(168, 85, 247, 0.2)',
            borderRadius: '12px',
            padding: '20px'
          }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>✨</div>
            <h4 style={{ fontWeight: '600', marginBottom: '4px' }}>
              AI Artifact Removal
            </h4>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Removes metallic shimmer and robotic artifacts
            </p>
          </div>
          
          <div style={{
            background: 'rgba(59, 130, 246, 0.1)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
            borderRadius: '12px',
            padding: '20px'
          }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>🎵</div>
            <h4 style={{ fontWeight: '600', marginBottom: '4px' }}>
              Professional Mastering
            </h4>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Ready for Spotify, YouTube, streaming
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer style={{ 
        textAlign: 'center', 
        marginTop: '48px', 
        paddingTop: '24px',
        borderTop: '1px solid #334155',
        color: '#64748b',
        fontSize: '0.85rem'
      }}>
        <p>Undectr • 100% local processing</p>
      </footer>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
