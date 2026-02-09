import { create } from 'zustand';

interface StoreState {
  isProcessing: boolean;
  currentFile: string | null;
  processingProgress: number;
  processingLog: string[];
  licenseInfo: any;
  usageInfo: any;
  
  setProcessing: (isProcessing: boolean, file?: string) => void;
  setProcessingProgress: (progress: number) => void;
  addLogMessage: (message: string) => void;
  setLicenseInfo: (info: any) => void;
  setUsageInfo: (info: any) => void;
  incrementProcessing: () => void;
  clearProcessing: () => void;
}

export const useStore = create<StoreState>((set) => ({
  isProcessing: false,
  currentFile: null,
  processingProgress: 0,
  processingLog: [],
  licenseInfo: null,
  usageInfo: null,
  
  setProcessing: (isProcessing, file) => 
    set({ isProcessing, currentFile: file || null }),
  
  setProcessingProgress: (progress) => 
    set({ processingProgress: progress }),
  
  addLogMessage: (message) => 
    set((state) => ({ processingLog: [...state.processingLog, message] })),
  
  setLicenseInfo: (info) => 
    set({ licenseInfo: info }),
  
  setUsageInfo: (info) => 
    set({ usageInfo: info }),
  
  incrementProcessing: () => 
    set((state) => ({
      usageInfo: {
        ...state.usageInfo,
        tracks_this_month: (state.usageInfo?.tracks_this_month || 0) + 1
      }
    })),
  
  clearProcessing: () => 
    set({ 
      isProcessing: false, 
      currentFile: null,
      processingProgress: 0,
      processingLog: [] 
    }),
}));