import React, { useEffect, useState } from 'react';
import { FileUploadZone } from '../components/FileUploadZone';
import { LogTable } from '../components/LogTable';
import { api } from '../services/api';
import { SecurityLog, UploadedFile } from '../types';
import { Loader2, RefreshCw, FileText, CheckCircle, AlertTriangle, Search } from 'lucide-react';

const LogUpload: React.FC = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [logs, setLogs] = useState<SecurityLog[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(true);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);

  // Filter states
  const [severityFilter, setSeverityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sourceSearch, setSourceSearch] = useState('');

  const fetchFiles = async () => {
    setLoadingFiles(true);
    try {
      const response = await api.getFiles();
      setFiles(response);
    } catch (err) {
      console.error('Failed to load uploaded files:', err);
    } finally {
      setLoadingFiles(false);
    }
  };

  const fetchLogs = async () => {
    setLoadingLogs(true);
    try {
      const params: any = { limit: 100 };
      if (selectedFileId) params.file_id = selectedFileId;
      if (severityFilter) params.severity = severityFilter;
      if (categoryFilter) params.category = categoryFilter;
      if (sourceSearch) params.source = sourceSearch;
      
      const response = await api.getLogs(params);
      setLogs(response);
    } catch (err) {
      console.error('Failed to load logs:', err);
    } finally {
      setLoadingLogs(false);
    }
  };

  // Poll files status while files are processing
  useEffect(() => {
    fetchFiles();
    fetchLogs();
  }, [selectedFileId]);

  useEffect(() => {
    const hasProcessing = files.some(f => f.status === 'processing' || f.status === 'uploaded');
    if (hasProcessing) {
      const interval = setInterval(async () => {
        const response = await api.getFiles();
        setFiles(response);
        // Refresh logs list as parsing completes
        fetchLogs();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [files]);

  const handleUploadSuccess = () => {
    fetchFiles();
    fetchLogs();
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto flex flex-col gap-8 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="page-title">Log Audit Ingestion</h1>
        <p className="page-subtitle">Ingest security log outputs for real-time parser translation & threat model evaluation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Upload Zone & Ingestion History */}
        <div className="flex flex-col gap-6 lg:col-span-1">
          <div className="glass-card p-5 flex flex-col gap-4">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Upload Log Source</h3>
            <FileUploadZone onUploadSuccess={handleUploadSuccess} />
          </div>

          <div className="glass-card p-5 flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <FileText size={16} />
                Ingested Datasets
              </h3>
              <button 
                onClick={fetchFiles}
                className="p-1.5 hover:bg-slate-800 rounded transition-colors text-slate-400 hover:text-slate-200"
                title="Refresh upload list"
              >
                <RefreshCw size={14} />
              </button>
            </div>

            {loadingFiles ? (
              <div className="flex justify-center py-8">
                <Loader2 className="animate-spin text-sky-400" size={24} />
              </div>
            ) : files.length === 0 ? (
              <div className="text-center py-8 text-slate-500 text-sm italic">
                No logs have been ingested yet.
              </div>
            ) : (
              <div className="flex flex-col gap-3 max-h-60 overflow-y-auto pr-1">
                {files.map((file) => {
                  const isSelected = selectedFileId === file.id;
                  return (
                    <div 
                      key={file.id}
                      onClick={() => setSelectedFileId(isSelected ? null : file.id)}
                      className={`p-3 rounded-lg border transition-all cursor-pointer flex justify-between items-center ${
                        isSelected 
                          ? 'bg-sky-500/10 border-sky-500/30' 
                          : 'bg-slate-950 border-slate-800/60 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex flex-col gap-1 min-w-0 pr-2">
                        <span className="text-xs font-bold text-slate-200 truncate" title={file.filename}>
                          {file.filename}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {formatDate(file.created_at)}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {file.log_count !== undefined && file.log_count > 0 && (
                          <span className="text-[10px] font-bold font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                            {file.log_count} msg
                          </span>
                        )}
                        {file.status === 'processed' && (
                          <CheckCircle size={14} className="text-green-400" />
                        )}
                        {(file.status === 'processing' || file.status === 'uploaded') && (
                          <Loader2 size={14} className="text-amber-400 animate-spin" />
                        )}
                        {file.status === 'failed' && (
                          <AlertTriangle size={14} className="text-red-400" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Parsed Log Output Viewer */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="glass-card p-6 flex flex-col gap-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h3 className="text-lg font-bold text-slate-200">Parsed Audit Trail</h3>
                {selectedFileId && (
                  <p className="text-xs text-sky-400 font-semibold font-mono mt-0.5">
                    Filtering on file reference ID: #{selectedFileId}
                  </p>
                )}
              </div>
              <button 
                onClick={fetchLogs}
                disabled={loadingLogs}
                className="btn-secondary btn-sm flex items-center gap-1.5"
              >
                {loadingLogs ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                Reload Data
              </button>
            </div>

            {/* Filter toolbar */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 bg-slate-950 p-4 border border-slate-800 rounded-xl">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Severity</label>
                <select 
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="input mt-1.5 bg-slate-900 border-slate-800"
                >
                  <option value="">All Severities</option>
                  <option value="info">INFO</option>
                  <option value="low">LOW</option>
                  <option value="medium">MEDIUM</option>
                  <option value="high">HIGH</option>
                  <option value="critical">CRITICAL</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Category</label>
                <select 
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="input mt-1.5 bg-slate-900 border-slate-800"
                >
                  <option value="">All Categories</option>
                  <option value="authentication">Authentication</option>
                  <option value="network">Network</option>
                  <option value="privilege_escalation">Priv Escalation</option>
                  <option value="account_management">Account Mgmt</option>
                  <option value="system">System</option>
                  <option value="detection">Detections</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Search Source Host/IP</label>
                <div className="relative mt-1.5">
                  <input 
                    type="text"
                    placeholder="Search hostname or IP..."
                    value={sourceSearch}
                    onChange={(e) => setSourceSearch(e.target.value)}
                    className="input pl-9 bg-slate-900 border-slate-800"
                  />
                  <Search size={14} className="absolute left-3 top-3 text-slate-500" />
                </div>
              </div>
            </div>

            {/* Log Table Container */}
            {loadingLogs ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3">
                <Loader2 size={32} className="text-sky-400 animate-spin" />
                <span className="text-xs text-slate-500 font-mono">Parsing records...</span>
              </div>
            ) : (
              <LogTable logs={logs} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogUpload;
