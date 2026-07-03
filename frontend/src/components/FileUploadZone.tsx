import React, { useCallback, useState } from 'react';
import { FileUp, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';

interface FileUploadZoneProps {
  onUploadSuccess: (data: any) => void;
}

export const FileUploadZone: React.FC<FileUploadZoneProps> = ({ onUploadSuccess }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [uploadState, setUploadState] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [fileName, setFileName] = useState('');

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  }, []);

  const uploadFile = async (file: File) => {
    setFileName(file.name);
    setUploadState('uploading');
    setErrorMessage('');
    
    // Import API directly to upload
    try {
      const { api } = await import('../services/api');
      const response = await api.uploadLog(file);
      setUploadState('success');
      onUploadSuccess(response);
      
      // Reset back to idle after 3s
      setTimeout(() => {
        setUploadState('idle');
        setFileName('');
      }, 3000);
    } catch (err: any) {
      console.error(err);
      setUploadState('error');
      setErrorMessage(err.response?.data?.detail || 'Failed to upload and parse the log file.');
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full flex flex-col gap-4">
      <div 
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        className={`w-full h-56 flex flex-col justify-center items-center rounded-xl border-2 border-dashed transition-all cursor-pointer relative overflow-hidden ${
          isDragActive 
            ? 'border-sky-500 bg-sky-500/5' 
            : uploadState === 'success'
            ? 'border-green-500 bg-green-500/5'
            : uploadState === 'error'
            ? 'border-red-500 bg-red-500/5'
            : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60'
        }`}
      >
        <input 
          type="file" 
          id="log-file-input" 
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          onChange={handleFileInput}
          disabled={uploadState === 'uploading'}
        />
        
        {uploadState === 'idle' && (
          <div className="flex flex-col items-center gap-3 p-6 text-center">
            <div className="p-3 rounded-lg bg-slate-800 border border-slate-700/60 text-slate-400">
              <FileUp size={28} />
            </div>
            <div>
              <p className="font-semibold text-slate-300">Drag & drop your log file here</p>
              <p className="text-xs text-slate-500 mt-1">Or click to select a file from your browser</p>
            </div>
            <p className="text-[10px] text-slate-600 font-mono mt-2">
              Supports Syslog (.log), Windows Event (.xml), JSON, and CSV exports
            </p>
          </div>
        )}

        {uploadState === 'uploading' && (
          <div className="flex flex-col items-center gap-3 p-6 text-center">
            <Loader2 size={32} className="text-sky-400 animate-spin" />
            <div>
              <p className="font-semibold text-slate-300">Uploading log file...</p>
              <p className="text-xs text-slate-500 mt-1">{fileName}</p>
            </div>
          </div>
        )}

        {uploadState === 'success' && (
          <div className="flex flex-col items-center gap-3 p-6 text-center animate-fade-in">
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400">
              <CheckCircle size={28} />
            </div>
            <div>
              <p className="font-semibold text-green-400">Upload Successful</p>
              <p className="text-xs text-slate-500 mt-1">
                {fileName} is being parsed & analyzed in the background.
              </p>
            </div>
          </div>
        )}

        {uploadState === 'error' && (
          <div className="flex flex-col items-center gap-3 p-6 text-center animate-fade-in">
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <AlertTriangle size={28} />
            </div>
            <div>
              <p className="font-semibold text-red-400">Upload Failed</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">{errorMessage}</p>
            </div>
            <button 
              onClick={(e) => {
                e.stopPropagation();
                setUploadState('idle');
              }}
              className="text-xs font-semibold text-sky-400 hover:text-sky-300 hover:underline mt-2"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
