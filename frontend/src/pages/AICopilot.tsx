import React, { useEffect, useRef, useState } from 'react';
import { useChat } from '../hooks/useChat';
import { ChatBubble } from '../components/ChatBubble';
import { parseServerDate } from '../utils/formatDate';
import { 
  Bot, 
  Send, 
  Trash2, 
  Database, 
  HelpCircle, 
  Loader2, 
  CheckCircle,
  FileSearch,
  MessageSquare,
  Plus,
  Clock,
  Menu,
  X,
  ChevronRight
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
    deleteSession,
    sessions,
    sessionId,
    switchSession,
    createNewSession,
    cancelGeneration,
  } = useChat();

  const [input, setInput] = useState('');
  const [useRag, setUseRag] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [hoveredSession, setHoveredSession] = useState<string | null>(null);
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

  const handleDeleteSession = async (sessionIdToDelete: string) => {
    if (!window.confirm('Delete this conversation permanently?')) return;

    setDeleting(sessionIdToDelete);
    try {
      await deleteSession(sessionIdToDelete);
    } catch (err) {
      console.error('Failed to delete session:', err);
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const date = parseServerDate(dateStr);
    if (!date) return 'unknown time';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    
    return date.toLocaleDateString();
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-950">
      
      {/* Sidebar */}
      <div className={`
        fixed lg:relative z-40 h-full bg-slate-950 border-r border-slate-900
        transition-all duration-300 ease-in-out
        ${sidebarOpen ? 'w-72' : 'w-0 -translate-x-full lg:w-0'}
        lg:translate-x-0 lg:w-72
      `}>
        <div className="h-full flex flex-col overflow-hidden">
          
          {/* Sidebar Header */}
          <div className="p-4 border-b border-slate-900 flex-shrink-0">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-slate-200 text-sm flex items-center gap-2">
                <MessageSquare size={16} className="text-sky-400" />
                Conversations
              </h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="lg:hidden text-slate-400 hover:text-slate-300 transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            <button
              onClick={createNewSession}
              className="w-full py-2 px-3 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              <Plus size={14} />
              New Chat
            </button>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {sessions.length === 0 ? (
              <p className="text-xs text-slate-600 py-8 text-center">No conversations yet</p>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.session_id}
                  onMouseEnter={() => setHoveredSession(session.session_id)}
                  onMouseLeave={() => setHoveredSession(null)}
                  className="group relative"
                >
                  <button
                    onClick={() => {
                      switchSession(session.session_id);
                      setSidebarOpen(false);
                    }}
                    className={`w-full text-left p-3 rounded-lg text-xs transition-all border ${
                      sessionId === session.session_id
                        ? 'bg-sky-500/15 border-sky-500/30 text-sky-300 shadow-lg shadow-sky-500/20'
                        : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:bg-slate-800/50 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <Clock size={12} className="flex-shrink-0 mt-1" />
                      <div className="flex-1 min-w-0">
                        <p className="truncate font-semibold text-slate-300">{session.preview || 'Empty'}</p>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          {formatDate(session.last_message)} • {session.message_count} msgs
                        </p>
                      </div>
                    </div>
                  </button>

                  {/* Delete Button - Visible on Hover */}
                  {(hoveredSession === session.session_id || deleting === session.session_id) && (
                    <button
                      onClick={() => handleDeleteSession(session.session_id)}
                      disabled={deleting === session.session_id}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                      title="Delete session"
                    >
                      {deleting === session.session_id ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                    </button>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Sidebar Footer - Knowledge Base Info */}
          <div className="p-4 border-t border-slate-900 space-y-3 flex-shrink-0">
            <div className="glass-card p-3 bg-slate-900/50 rounded-lg border-slate-800">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <Database size={12} className="text-sky-400" />
                Vector DB
              </p>
              {aiStatus && (
                <div className="flex items-center gap-1.5 text-xs text-slate-300 bg-slate-950 p-2 rounded border border-slate-800">
                  <CheckCircle size={12} className="text-green-400" />
                  <span>{aiStatus.rag_documents} docs</span>
                </div>
              )}
            </div>
            
            {aiStatus && (
              <div className="flex items-center gap-1.5 text-xs font-mono p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                <span className={`w-2 h-2 rounded-full ${aiStatus.ollama_available ? 'bg-green-500' : 'bg-red-500'}`}></span>
                {aiStatus.ollama_available ? `${aiStatus.model}` : 'OLLAMA: OFFLINE'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-900 bg-slate-950/50 backdrop-blur flex-shrink-0">
          <div className="flex items-center gap-4 flex-1">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden text-slate-400 hover:text-slate-300 p-2 hover:bg-slate-900 rounded-lg transition-colors"
            >
              <Menu size={20} />
            </button>
            <div>
              <h1 className="page-title flex items-center gap-2 text-xl">
                <Bot className="text-sky-400" size={24} />
                AI Operations Copilot
              </h1>
              <p className="page-subtitle text-xs">ChromaDB-grounded SOC assistant</p>
            </div>
          </div>

          <button 
            onClick={clearChat}
            className="btn-danger btn-sm flex items-center gap-1.5 font-mono uppercase tracking-wider text-xs flex-shrink-0"
            title="Clear current chat messages"
          >
            <Trash2 size={13} />
            Clear
          </button>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4 scroll-smooth">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-20 px-6">
              <div className="p-4 bg-sky-500/10 border border-sky-500/20 text-sky-400 rounded-2xl mb-4">
                <Bot size={36} />
              </div>
              <h4 className="font-bold text-slate-300 text-lg">Interactive Security Assistant</h4>
              <p className="text-sm text-slate-500 mt-2 leading-relaxed text-center max-w-md">
                Start a conversation to audit log files, request configs, explain alerts, or map telemetry to MITRE techniques.
              </p>
              
              <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-md">
                {SUGGESTIONS.map((text) => (
                  <button
                    key={text}
                    onClick={() => handleSuggestion(text)}
                    disabled={loading}
                    className="text-left text-xs p-3 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 hover:text-sky-300 hover:border-sky-500/20 hover:bg-sky-500/5 transition-all"
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
                <div className="flex items-center gap-2.5 text-xs text-slate-500 font-mono pl-4">
                  <Loader2 size={14} className="animate-spin text-sky-400" />
                  <span>Assistant thinking...</span>
                  <button type="button" onClick={cancelGeneration} className="ml-2 btn-danger btn-sm py-1 px-2 text-[10px]">
                    <X size={12} /> Cancel
                  </button>
                </div>
              )}
              
              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-xl flex items-start gap-3 font-mono">
                  <Trash2 size={16} className="flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <form onSubmit={handleSend} className="p-4 bg-slate-950/60 border-t border-slate-900 flex flex-col gap-3 flex-shrink-0">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about logs, alerts, mitigations..."
              disabled={loading}
              className="input bg-slate-900 border-slate-800 flex-1 px-4 py-3 text-sm placeholder-slate-600 rounded-xl"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn-primary px-4 py-3 rounded-xl flex-shrink-0"
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
              Ground with RAG context
            </label>
          </div>
        </form>
      </div>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/30 lg:hidden z-30"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};

export default AICopilot;
