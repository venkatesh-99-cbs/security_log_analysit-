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
  Play,
  Sparkles,
  PlusCircle
} from 'lucide-react';

const Settings: React.FC = () => {
  const [aiStatus, setAIStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [updatingModel, setUpdatingModel] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [addingKnowledge, setAddingKnowledge] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [knowledgeTitle, setKnowledgeTitle] = useState('');
  const [knowledgeContent, setKnowledgeContent] = useState('');
  const [knowledgeSource, setKnowledgeSource] = useState('User Upload');
  const [knowledgeCategory, setKnowledgeCategory] = useState('custom');
  const [selectedKnowledgeFile, setSelectedKnowledgeFile] = useState<File | null>(null);

  const fetchAIStatus = async () => {
    try {
      const response = await api.getAIStatus();
      setAIStatus(response);
      setSelectedModel(response.model || '');
    } catch (err) {
      console.error('Failed to fetch AI status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = async (modelName: string) => {
    setUpdatingModel(true);
    setFeedback(null);
    try {
      await api.updateAISettings({ model: modelName });
      setSelectedModel(modelName);
      setFeedback({
        type: 'success',
        msg: `Preferred Ollama model updated to: ${modelName}`,
      });
      await fetchAIStatus();
    } catch (err) {
      console.error('Failed to update preferred model:', err);
      setFeedback({
        type: 'error',
        msg: 'Failed to update preferred model. Check backend connection.',
      });
    } finally {
      setUpdatingModel(false);
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

  const handleAddKnowledge = async (event: React.FormEvent) => {
    event.preventDefault();
    setAddingKnowledge(true);
    setFeedback(null);
    try {
      let response;
      if (selectedKnowledgeFile) {
        response = await api.uploadKnowledgeFile(selectedKnowledgeFile, {
          title: knowledgeTitle || undefined,
          source: knowledgeSource || undefined,
          category: knowledgeCategory || undefined,
        });
      } else {
        response = await api.addKnowledge({
          title: knowledgeTitle,
          content: knowledgeContent,
          source: knowledgeSource,
          category: knowledgeCategory,
        });
      }
      setFeedback({
        type: 'success',
        msg: `Added custom knowledge entry. Vector DB now contains ${response.total} records.`,
      });
      setKnowledgeTitle('');
      setKnowledgeContent('');
      setKnowledgeSource('User Upload');
      setKnowledgeCategory('custom');
      setSelectedKnowledgeFile(null);
      await fetchAIStatus();
    } catch (err) {
      console.error('Custom knowledge ingestion failed:', err);
      setFeedback({
        type: 'error',
        msg: 'Failed to add custom knowledge. Check backend connection.',
      });
    } finally {
      setAddingKnowledge(false);
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
                  <span className="text-slate-500">Active / Preferred Model:</span>
                  {aiStatus.available_models && aiStatus.available_models.length > 0 ? (
                    <div className="flex items-center gap-2 mt-1">
                      <select
                        value={selectedModel || aiStatus.model}
                        onChange={(e) => handleModelChange(e.target.value)}
                        disabled={updatingModel}
                        className="input bg-slate-900 border-slate-800 text-xs py-1.5 max-w-[200px]"
                      >
                        {aiStatus.available_models.map((modelName: string) => (
                          <option key={modelName} value={modelName}>
                            {modelName}
                          </option>
                        ))}
                      </select>
                      {updatingModel && <Loader2 className="animate-spin text-sky-400" size={16} />}
                    </div>
                  ) : (
                    <p className="text-slate-300 font-semibold mt-1">{aiStatus.model}</p>
                  )}
                </div>
              </div>
              <div className="flex flex-col gap-2 rounded-xl border border-sky-500/20 bg-sky-500/5 p-3 text-xs text-slate-300">
                <div className="flex items-center gap-2 text-sky-300">
                  <Sparkles size={14} />
                  <span className="font-semibold">Recommended local model</span>
                </div>
                <p className="text-slate-400">{aiStatus.recommended_model || 'qwen2.5:3b-instruct'} is a good balance of speed and accuracy for local Ollama setups.</p>
                {aiStatus.available_models?.length ? (
                  <p className="text-slate-400">Detected on this device: {aiStatus.available_models.join(', ')}</p>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 text-xs font-bold text-red-400 bg-red-500/5 p-3 rounded-lg border border-red-500/10">
                <AlertTriangle size={16} />
                Warning: Could not connect to local Ollama engine at http://localhost:11434.
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                The AI Copilot and Root-Cause Incident analysis features require local installation of Ollama. The app will auto-detect a usable model if one is installed, but a small fast model is recommended:
              </p>
              <pre className="bg-slate-950 border border-slate-850 p-3 rounded-lg text-[11px] font-mono text-sky-400 select-all">
                ollama pull qwen2.5:3b-instruct
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
                Seed the vector database with standard SOC playbooks and add your own SOPs or runbooks so the copilot can answer with better grounded context.
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

          <form onSubmit={handleAddKnowledge} className="flex flex-col gap-3 rounded-xl border border-slate-800/80 bg-slate-950/60 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <PlusCircle size={16} className="text-sky-400" />
              Add custom RAG knowledge
            </div>
            <input
              required={!selectedKnowledgeFile}
              value={knowledgeTitle}
              onChange={(event) => setKnowledgeTitle(event.target.value)}
              placeholder="Knowledge title"
              className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"
            />
            <textarea
              required={!selectedKnowledgeFile}
              value={knowledgeContent}
              onChange={(event) => setKnowledgeContent(event.target.value)}
              placeholder="Paste your SOP, runbook, or notes here..."
              rows={5}
              className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"
            />
            <label className="flex cursor-pointer flex-col gap-2 rounded-lg border border-dashed border-slate-700 bg-slate-900/70 px-3 py-3 text-sm text-slate-300">
              <span className="text-xs uppercase tracking-wider text-slate-500">Or upload a .txt/.md/.json file</span>
              <input
                type="file"
                accept=".txt,.md,.json"
                onChange={(event) => setSelectedKnowledgeFile(event.target.files?.[0] || null)}
                className="text-sm"
              />
              {selectedKnowledgeFile ? <span className="text-sky-400">Selected: {selectedKnowledgeFile.name}</span> : null}
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              <input
                value={knowledgeSource}
                onChange={(event) => setKnowledgeSource(event.target.value)}
                placeholder="Source"
                className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"
              />
              <input
                value={knowledgeCategory}
                onChange={(event) => setKnowledgeCategory(event.target.value)}
                placeholder="Category"
                className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200"
              />
            </div>
            <button
              type="submit"
              disabled={addingKnowledge}
              className="btn-primary flex items-center justify-center gap-2 self-start px-4 py-2 text-xs font-mono uppercase tracking-wider"
            >
              {addingKnowledge ? <Loader2 className="animate-spin" size={14} /> : <PlusCircle size={14} />}
              {addingKnowledge ? 'Adding...' : 'Add to RAG'}
            </button>
          </form>

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
