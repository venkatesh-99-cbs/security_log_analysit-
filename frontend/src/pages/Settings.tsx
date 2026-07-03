import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { 
  Settings as SettingsIcon, 
  Database, 
  Cpu, 
  HelpCircle, 
  Loader2, 
  CheckCircle, 
  AlertTriangle,
  Play
} from 'lucide-react';

const Settings: React.FC = () => {
  const [aiStatus, setAIStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const fetchAIStatus = async () => {
    try {
      const response = await api.getAIStatus();
      setAIStatus(response);
    } catch (err) {
      console.error('Failed to fetch AI status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAIStatus();
  }, []);

  const handleIngest = async () => {
    setIngesting(true);
    setFeedback(null);
    try {
      const response = await api.ingestKnowledge();
      setFeedback({
        type: 'success',
        msg: `Ingested ${response.ingested} security playbooks. Vector DB now contains ${response.total} records.`,
      });
      await fetchAIStatus();
    } catch (err) {
      console.error('Knowledge base ingestion failed:', err);
      setFeedback({
        type: 'error',
        msg: 'Failed to ingest knowledge document set. Check backend connection.',
      });
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto flex flex-col gap-8 animate-fade-in">
      {/* Page Header */}
      <div className="pb-4 border-b border-slate-900">
        <h1 className="page-title flex items-center gap-2">
          <SettingsIcon className="text-sky-400" size={24} />
          System Settings &amp; AI Engine Configuration
        </h1>
        <p className="page-subtitle">
          Configure offline SLM parameter variables, test database endpoints, and check ingestion status.
        </p>
      </div>

      <div className="flex flex-col gap-6">
        
        {/* Ollama status card */}
        <div className="glass-card p-6 flex flex-col gap-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 border-b border-slate-800/80 pb-2">
            <Cpu size={16} className="text-sky-400" />
            Ollama Inference System
          </h3>

          {loading ? (
            <div className="flex items-center gap-2 py-4">
              <Loader2 className="animate-spin text-sky-400" size={18} />
              <span className="text-xs text-slate-500 font-mono">Querying inference endpoint...</span>
            </div>
          ) : aiStatus?.ollama_available ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 text-xs font-bold text-green-400 bg-green-500/5 p-3 rounded-lg border border-green-500/10">
                <CheckCircle size={16} />
                Successfully connected to local Ollama inference server.
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs font-mono bg-slate-950 p-4 border border-slate-850 rounded-xl">
                <div>
                  <span className="text-slate-500">Inference Endpoint URL:</span>
                  <p className="text-slate-300 font-semibold mt-1">{aiStatus.base_url}</p>
                </div>
                <div>
                  <span className="text-slate-500">Target Small Language Model:</span>
                  <p className="text-slate-300 font-semibold mt-1">{aiStatus.model}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 text-xs font-bold text-red-400 bg-red-500/5 p-3 rounded-lg border border-red-500/10">
                <AlertTriangle size={16} />
                Warning: Could not connect to local Ollama engine at http://localhost:11434.
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                The AI Copilot and Root-Cause Incident analysis features require local installation of Ollama. Please ensure Ollama is installed and running, then pull the target model in your command line:
              </p>
              <pre className="bg-slate-950 border border-slate-850 p-3 rounded-lg text-[11px] font-mono text-sky-400 select-all">
                ollama pull qwen3:8b
              </pre>
            </div>
          )}
        </div>

        {/* Vector DB card */}
        <div className="glass-card p-6 flex flex-col gap-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 border-b border-slate-800/80 pb-2">
            <Database size={16} className="text-sky-400" />
            Knowledge Base Vector Store (ChromaDB)
          </h3>

          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="flex-1 flex flex-col gap-1">
              <p className="text-xs text-slate-400 leading-relaxed max-w-md">
                Seed the vector database with standard SOC Operations manual, MITRE ATT&amp;CK taxonomy tables, and triage guidelines.
              </p>
              {aiStatus && (
                <span className="text-xs font-mono font-bold text-sky-400 mt-2">
                  Current Document Count: {aiStatus.rag_documents}
                </span>
              )}
            </div>

            <button 
              onClick={handleIngest}
              disabled={ingesting}
              className="btn-primary flex items-center gap-1.5 flex-shrink-0 text-xs font-mono uppercase tracking-wider px-4 py-2.5"
            >
              {ingesting ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Seeding Vector DB...
                </>
              ) : (
                <>
                  <Play size={12} />
                  Ingest Security Knowledge
                </>
              )}
            </button>
          </div>

          {feedback && (
            <div className={`p-3 rounded-lg border text-xs flex items-center gap-2 font-mono mt-2 ${
              feedback.type === 'success' 
                ? 'bg-green-500/10 border-green-500/20 text-green-400' 
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}>
              {feedback.type === 'success' ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}
              {feedback.msg}
            </div>
          )}
        </div>

        {/* Help card */}
        <div className="glass-card p-6 flex flex-col gap-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 border-b border-slate-800/80 pb-2">
            <HelpCircle size={16} className="text-sky-400" />
            Documentation Reference
          </h3>
          <div className="text-xs text-slate-400 flex flex-col gap-2 leading-relaxed">
            <p><strong>Offline Triage System:</strong> This SOC Assistant is architected to run entirely locally. No log payloads are transmitted to any cloud servers.</p>
            <p><strong>MITRE ATT&amp;CK Tactics:</strong> Map detections to initial access, privilege escalation, discovery, and lateral movement tactics.</p>
            <p><strong>Correlations:</strong> Security events are correlated by target workstation IP addresses and subject usernames within rolling time windows.</p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Settings;
