import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Report } from '../types';
import { 
  FileText, 
  Plus, 
  Download, 
  Loader2, 
  RefreshCw, 
  Calendar,
  AlertTriangle,
  CheckCircle,
  FileCheck
} from 'lucide-react';

const Reports: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [newReportTitle, setNewReportTitle] = useState('Executive Incident Report');
  const [severityFilter, setSeverityFilter] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const response = await api.getReports();
      setReports(response);
    } catch (err) {
      console.error('Failed to fetch reports list:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReportTitle.trim() || generating) return;

    setGenerating(true);
    setFeedback(null);
    try {
      await api.generateReport({
        title: newReportTitle,
        severity_filter: severityFilter || undefined,
      });
      setNewReportTitle('Executive Incident Report');
      setSeverityFilter('');
      setFeedback({ type: 'success', msg: 'Report successfully compiled and saved to disk.' });
      await fetchReports();
      
      setTimeout(() => setFeedback(null), 5000);
    } catch (err: any) {
      console.error('Failed to generate report:', err);
      setFeedback({ 
        type: 'error', 
        msg: err.response?.data?.detail || 'Failed to compile report. Make sure you have parsed incidents in the queue.' 
      });
    } finally {
      setGenerating(false);
    }
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
      <div className="flex justify-between items-center pb-4 border-b border-slate-900">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <FileText className="text-sky-400" size={24} />
            Executive Reports Center
          </h1>
          <p className="page-subtitle">
            Compile and archive structured HTML incident summaries, audit logs, and MITRE heatmap reports.
          </p>
        </div>

        <button 
          onClick={fetchReports}
          disabled={loading}
          className="btn-secondary btn-sm flex items-center gap-1.5"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh List
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Generate Report Form */}
        <div className="flex flex-col gap-6 lg:col-span-1">
          <div className="glass-card p-5 flex flex-col gap-4">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Plus size={16} className="text-sky-400" />
              Compile New Report
            </h3>
            
            <form onSubmit={handleGenerate} className="flex flex-col gap-4">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Report Title</label>
                <input 
                  type="text"
                  value={newReportTitle}
                  onChange={(e) => setNewReportTitle(e.target.value)}
                  placeholder="Executive Incident Summary..."
                  required
                  className="input mt-1.5 bg-slate-900 border-slate-800"
                />
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Triage Severity Focus</label>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="input mt-1.5 bg-slate-900 border-slate-800 text-xs py-2"
                >
                  <option value="">All Severities</option>
                  <option value="critical">Critical Focus Only</option>
                  <option value="high">High Severity Focus</option>
                  <option value="medium">Medium Severity Focus</option>
                </select>
              </div>

              {feedback && (
                <div className={`p-3 rounded-lg border text-xs flex items-center gap-2 font-mono ${
                  feedback.type === 'success' 
                    ? 'bg-green-500/10 border-green-500/20 text-green-400' 
                    : 'bg-red-500/10 border-red-500/20 text-red-400'
                }`}>
                  {feedback.type === 'success' ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
                  {feedback.msg}
                </div>
              )}

              <button 
                type="submit"
                disabled={generating || !newReportTitle.trim()}
                className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
              >
                {generating ? (
                  <>
                    <Loader2 size={16} className="animate-spin text-white" />
                    Compiling PDF/HTML...
                  </>
                ) : (
                  <>
                    <FileCheck size={16} />
                    Compile Report
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Reports Archive */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="glass-card p-6 flex flex-col gap-4">
            <h3 className="text-lg font-bold text-slate-200">Archive Directory</h3>
            
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3">
                <Loader2 size={32} className="text-sky-400 animate-spin" />
                <span className="text-xs text-slate-500 font-mono">Scanning archive...</span>
              </div>
            ) : reports.length === 0 ? (
              <div className="text-center py-16 text-slate-500 text-sm italic">
                No reports compiled in the archive yet.
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {reports.map((report) => (
                  <div 
                    key={report.id}
                    className="p-4 bg-slate-950 border border-slate-800/80 hover:border-slate-700/60 rounded-xl flex items-center justify-between transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-sky-400">
                        <FileText size={20} />
                      </div>
                      <div>
                        <h4 className="font-bold text-slate-200 text-sm">{report.title}</h4>
                        <div className="flex items-center gap-3 text-[10px] text-slate-500 mt-1 font-mono">
                          <span className="flex items-center gap-1">
                            <Calendar size={10} />
                            {formatDate(report.created_at)}
                          </span>
                          <span>Scope: {report.report_type.toUpperCase()}</span>
                        </div>
                      </div>
                    </div>

                    <a 
                      href={api.getDownloadReportUrl(report.id)}
                      download
                      className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-sky-400 border border-transparent hover:border-slate-700/60 transition-all flex items-center gap-1 text-xs font-semibold"
                    >
                      <Download size={14} /> Download HTML
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reports;
