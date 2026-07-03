import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { Incident } from '../types';
import { SeverityBadge } from '../components/SeverityBadge';
import { StatusBadge } from '../components/StatusBadge';
import { MitreHeatmap } from '../components/MitreHeatmap';
import { ChatBubble } from '../components/ChatBubble';
import { 
  ChevronLeft, 
  Loader2, 
  ShieldAlert, 
  Bot, 
  Play, 
  Calendar, 
  CheckCircle,
  HelpCircle,
  Settings
} from 'lucide-react';

const IncidentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const incidentId = parseInt(id || '0', 10);

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);

  const fetchIncident = async () => {
    try {
      const response = await api.getIncident(incidentId);
      setIncident(response);
    } catch (err) {
      console.error('Failed to load incident detail:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncident();
  }, [incidentId]);

  const handleStatusChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSavingStatus(true);
    try {
      await api.updateIncident(incidentId, { status: e.target.value });
      await fetchIncident();
    } catch (err) {
      console.error('Failed to update status:', err);
    } finally {
      setSavingStatus(false);
    }
  };

  const handleSeverityChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSavingStatus(true);
    try {
      await api.updateIncident(incidentId, { severity: e.target.value });
      await fetchIncident();
    } catch (err) {
      console.error('Failed to update severity:', err);
    } finally {
      setSavingStatus(false);
    }
  };

  const triggerAIAnalysis = async () => {
    setAnalyzing(true);
    try {
      await api.analyzeIncident(incidentId);
      await fetchIncident(); // Refresh to load new analyses
    } catch (err) {
      console.error('AI Analysis failed:', err);
      alert('Failed to complete AI analysis. Make sure Ollama is running and has the model loaded.');
    } finally {
      setAnalyzing(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] gap-3">
        <Loader2 size={36} className="text-sky-400 animate-spin" />
        <span className="text-sm text-slate-500 font-medium font-mono">Retrieving analysis report...</span>
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="p-8 max-w-3xl mx-auto text-center flex flex-col items-center gap-4 justify-center">
        <div className="p-4 rounded-full bg-slate-800 border border-slate-700/60 text-slate-500">
          <ShieldAlert size={36} />
        </div>
        <div>
          <h4 className="font-bold text-slate-300 text-lg">Incident Not Found</h4>
          <p className="text-sm text-slate-500 mt-1">
            The requested incident report ID #{incidentId} does not exist in the database.
          </p>
        </div>
        <Link to="/incidents" className="btn-primary mt-4">
          <ChevronLeft size={16} /> Back to List
        </Link>
      </div>
    );
  }

  // Get latest analysis response if available
  const latestAnalysis = incident.analyses && incident.analyses.length > 0
    ? incident.analyses[incident.analyses.length - 1]
    : null;

  return (
    <div className="p-8 max-w-7xl mx-auto flex flex-col gap-8 animate-fade-in">
      {/* Back button */}
      <div>
        <Link 
          to="/incidents" 
          className="text-xs font-semibold text-slate-500 hover:text-slate-300 flex items-center gap-1.5 font-mono uppercase tracking-wider"
        >
          <ChevronLeft size={14} /> Back to Incident Queue
        </Link>
      </div>

      {/* Primary header panel */}
      <div className="glass-card p-6 flex flex-col md:flex-row justify-between gap-6">
        <div className="flex-1 flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
              incident.severity === 'critical' || incident.severity === 'high'
                ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}>
              ID: #{incident.id}
            </span>
            <SeverityBadge severity={incident.severity} />
            <StatusBadge status={incident.status} />
          </div>
          
          <h1 className="text-2xl font-bold text-slate-200">{incident.title}</h1>
          
          <div className="flex items-center gap-4 text-xs text-slate-500 mt-1">
            <span className="flex items-center gap-1">
              <Calendar size={12} />
              Opened: {formatDate(incident.created_at)}
            </span>
            {incident.source_ip && (
              <span>Source Host: <code className="font-mono text-slate-400">{incident.source_ip}</code></span>
            )}
          </div>
        </div>

        {/* Triage action configuration */}
        <div className="flex flex-col sm:flex-row md:flex-col gap-4 justify-center bg-slate-950 p-4 border border-slate-800 rounded-xl md:min-w-64">
          <div className="flex-1">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
              <Settings size={10} />
              Set Incident Status
            </label>
            <select 
              value={incident.status}
              onChange={handleStatusChange}
              disabled={savingStatus}
              className="input mt-1 bg-slate-900 border-slate-800 text-xs py-1.5"
            >
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          <div className="flex-1">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
              <Settings size={10} />
              Set Severity Override
            </label>
            <select 
              value={incident.severity}
              onChange={handleSeverityChange}
              disabled={savingStatus}
              className="input mt-1 bg-slate-900 border-slate-800 text-xs py-1.5"
            >
              <option value="info">INFO</option>
              <option value="low">LOW</option>
              <option value="medium">MEDIUM</option>
              <option value="high">HIGH</option>
              <option value="critical">CRITICAL</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left column — details, maps */}
        <div className="lg:col-span-2 flex flex-col gap-8">
          {/* Incident Description */}
          <div className="glass-card p-6 flex flex-col gap-4">
            <h3 className="text-md font-bold text-slate-200 uppercase tracking-wider border-b border-slate-800/80 pb-2">
              Incident Correlation Digest
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
              {incident.description}
            </p>
          </div>

          {/* MITRE Mapping Matrix */}
          <div className="glass-card p-6 flex flex-col gap-4">
            <MitreHeatmap mappings={incident.mitre_mappings || []} />
          </div>
        </div>

        {/* Right column — Copilot analyst helper */}
        <div className="lg:col-span-1 flex flex-col gap-8">
          <div className="glass-card p-6 flex flex-col gap-5 border border-sky-500/10">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800/80">
              <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Bot size={18} className="text-sky-400" />
                AI SOC Playbook Analyst
              </h3>
              <span className="flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                <span className="status-dot status-dot-online"></span>
                Ollama Active
              </span>
            </div>

            {latestAnalysis ? (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-2 text-xs font-bold text-green-400 bg-green-500/5 p-3 rounded-lg border border-green-500/10">
                  <CheckCircle size={16} />
                  AI Investigation Report Available
                </div>
                
                {/* Embedded Analysis content */}
                <div className="bg-slate-950 p-4 border border-slate-800 rounded-xl">
                  <ChatBubble 
                    message={{
                      role: 'assistant',
                      content: latestAnalysis.response,
                    }}
                  />
                </div>

                <button 
                  onClick={triggerAIAnalysis}
                  disabled={analyzing}
                  className="btn-secondary text-xs flex items-center justify-center gap-1.5 mt-2"
                >
                  {analyzing ? (
                    <Loader2 size={14} className="animate-spin text-sky-400" />
                  ) : (
                    <Play size={12} />
                  )}
                  Re-analyze Incident
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-4 text-center py-6 px-4">
                <div className="p-3 bg-slate-800/60 rounded-full text-slate-400 self-center">
                  <HelpCircle size={28} />
                </div>
                <div>
                  <h4 className="font-bold text-slate-300 text-sm">No analysis reports run yet</h4>
                  <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto leading-relaxed">
                    Trigger local Ollama model (qwen3:8b) to run incident root-cause analysis, mapping validations, and mitigation strategies.
                  </p>
                </div>
                <button 
                  onClick={triggerAIAnalysis}
                  disabled={analyzing}
                  className="btn-primary flex items-center justify-center gap-2 mt-4 font-mono uppercase tracking-wider text-xs py-2.5"
                >
                  {analyzing ? (
                    <>
                      <Loader2 size={16} className="animate-spin text-white" />
                      Analyzing telemetry...
                    </>
                  ) : (
                    <>
                      <Play size={14} />
                      Generate AI Analysis
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default IncidentDetail;
