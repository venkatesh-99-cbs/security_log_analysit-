import React, { useEffect, useRef, useState } from 'react';
import { useChat } from '../hooks/useChat';
import { ChatBubble } from '../components/ChatBubble';
import { 
  Bot, 
  Send, 
  Trash2, 
  Database, 
  HelpCircle, 
  Loader2, 
  CheckCircle,
  FileSearch
} from 'lucide-react';

const SUGGESTIONS = [
  'What are the critical steps to triage a port scan?',
  'Explain Windows Security Event ID 4624 Logon Types.',
  'How do I handle lateral movement in a compromised network?',
  'Analyze brute force attack vectors and response protocols.',
];

const AICopilot: React.FC = () => {
  const {
    messages,
    loading,
    error,
    aiStatus,
    sendMessage,
    clearChat,
  } = useChat();

  const [input, setInput] = useState('');
  const [useRag, setUseRag] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || loading) return;
    
    sendMessage(input, useRag);
    setInput('');
  };

  const handleSuggestion = (text: string) => {
    if (loading) return;
    sendMessage(text, useRag);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto flex flex-col h-[calc(100vh-4rem)] max-h-[850px] animate-fade-in">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-4 border-b border-slate-900 mb-6">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Bot className="text-sky-400" size={24} />
            AI Operations Copilot
          </h1>
          <p className="page-subtitle">
            Local SLM assistant grounded with ChromaDB vector search across internal SOC playbooks.
          </p>
        </div>

        <div className="flex items-center gap-4">
          {aiStatus && (
            <span className="flex items-center gap-1.5 text-xs font-mono font-semibold px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
              <span className={`status-dot ${aiStatus.ollama_available ? 'status-dot-online' : 'status-dot-offline'}`}></span>
              {aiStatus.ollama_available ? `OLLAMA: ${aiStatus.model}` : 'OLLAMA: OFFLINE'}
            </span>
          )}
          <button 
            onClick={clearChat}
            className="btn-danger btn-sm flex items-center gap-1.5 font-mono uppercase tracking-wider text-xs"
            title="Clear Chat History"
          >
            <Trash2 size={13} />
            Reset Session
          </button>
        </div>
      </div>

      {/* Main chat window container */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-0">
        
        {/* Left Side Info Panel */}
        <div className="hidden lg:flex flex-col gap-6 lg:col-span-1">
          <div className="glass-card p-5 flex flex-col gap-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Database size={14} className="text-sky-400" />
              Grounded Knowledge Base
            </h3>
            
            <p className="text-xs text-slate-500 leading-relaxed">
              When RAG is enabled, the Copilot searches ChromaDB for matching playbooks, reference guides, and mitigation strategies to inject into context.
            </p>
            
            {aiStatus && (
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-850">
                <CheckCircle size={14} className="text-green-400" />
                {aiStatus.rag_documents} documents in Vector database
              </div>
            )}
          </div>

          <div className="glass-card p-5 flex flex-col gap-4 flex-1 overflow-y-auto">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <HelpCircle size={14} className="text-sky-400" />
              Suggested Queries
            </h3>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((text) => (
                <button
                  key={text}
                  onClick={() => handleSuggestion(text)}
                  disabled={loading}
                  className="text-left text-xs p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-slate-400 hover:text-sky-400 hover:border-sky-500/20 hover:bg-sky-500/5 transition-all"
                >
                  {text}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Chat area */}
        <div className="lg:col-span-3 flex flex-col glass-card border border-slate-800 overflow-hidden min-h-0">
          
          {/* Scrollable messages wrapper */}
          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 scroll-smooth">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-20 px-6 max-w-lg mx-auto">
                <div className="p-4 bg-sky-500/10 border border-sky-500/20 text-sky-400 rounded-2xl mb-4">
                  <Bot size={36} />
                </div>
                <h4 className="font-bold text-slate-300 text-lg">Interactive Security Assistant</h4>
                <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                  Start a conversation to audit raw log files, request mitigating configs, explain anomalous signatures, or map telemetry to MITRE techniques.
                </p>
                <div className="flex flex-col sm:flex-row gap-2 mt-6 w-full lg:hidden">
                  {SUGGESTIONS.slice(0, 2).map((text) => (
                    <button
                      key={text}
                      onClick={() => handleSuggestion(text)}
                      className="text-left text-xs p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-slate-400 hover:text-sky-400 transition-colors"
                    >
                      {text}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((message, idx) => (
                  <ChatBubble key={idx} message={message} />
                ))}
                
                {loading && (
                  <div className="flex items-center gap-2.5 text-xs text-slate-500 font-mono pl-11">
                    <Loader2 size={14} className="animate-spin text-sky-400" />
                    Assistant is fetching response model...
                  </div>
                )}
                
                {error && (
                  <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-xl flex items-center gap-2 font-mono">
                    <Trash2 size={14} />
                    {error}
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Bottom input area */}
          <form onSubmit={handleSend} className="p-4 bg-slate-950/60 border-t border-slate-850 flex flex-col gap-3">
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about active events, query manuals, or parse logs..."
                disabled={loading}
                className="input bg-slate-900 border-slate-800 flex-1 px-4 py-3 text-sm placeholder-slate-600 rounded-xl"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="btn-primary px-5 py-3 rounded-xl flex-shrink-0"
              >
                <Send size={16} />
              </button>
            </div>
            
            <div className="flex items-center gap-2 pl-1 select-none">
              <input
                type="checkbox"
                id="rag-checkbox"
                checked={useRag}
                onChange={(e) => setUseRag(e.target.checked)}
                className="w-3.5 h-3.5 accent-sky-500 bg-slate-900 border-slate-800 rounded focus:ring-0 focus:ring-offset-0 cursor-pointer"
              />
              <label 
                htmlFor="rag-checkbox" 
                className="text-[10px] font-bold text-slate-500 uppercase tracking-widest cursor-pointer flex items-center gap-1 hover:text-slate-400 transition-colors"
              >
                <FileSearch size={10} />
                Ground prompt with RAG playbook context
              </label>
            </div>
          </form>

        </div>
      </div>
    </div>
  );
};

export default AICopilot;
