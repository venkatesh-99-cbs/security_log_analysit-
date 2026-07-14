import { useState, useEffect, useCallback } from 'react';
import { ChatMessage } from '../types';
import { api } from '../services/api';

export interface ChatSession {
  session_id: string;
  last_message: string;
  preview: string;
  message_count: number;
}

export const useChat = (initialSessionId?: string) => {
  const [sessionId, setSessionId] = useState(initialSessionId || '');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAIStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  // Auto-generate session ID if not provided
  useEffect(() => {
    if (!sessionId) {
      const id = `session_${Math.random().toString(36).substring(2, 11)}`;
      setSessionId(id);
    }
  }, [sessionId]);

  const loadHistory = useCallback(async () => {
    if (!sessionId) return;
    try {
      const history = await api.getChatHistory(sessionId);
      setMessages(history);
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  }, [sessionId]);

  const loadSessions = useCallback(async () => {
    try {
      const sess = await api.getChatSessions();
      setSessions(sess);
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
    }
  }, []);

  const fetchAIStatus = async () => {
    try {
      const status = await api.getAIStatus();
      setAIStatus(status);
    } catch (err) {
      console.error('Failed to fetch AI/Ollama status:', err);
    }
  };

  useEffect(() => {
    if (sessionId) {
      loadHistory();
    }
    loadSessions();
    fetchAIStatus();
  }, [sessionId, loadHistory, loadSessions]);

  const sendMessage = async (text: string, useRag = true) => {
    if (!text.trim() || !sessionId || loading) return;

    const userMessage: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    // Placeholder for assistant message to append tokens dynamically
    let currentAssistantContent = '';

    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    try {
      await api.chatStream({
        session_id: sessionId,
        message: text,
        use_rag: useRag,
      }, {
        onToken: (token: string) => {
          currentAssistantContent += token;
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === 'assistant') {
              last.content = currentAssistantContent;
            }
            return updated;
          });
        },
        onMetadata: (ragUsed: boolean) => {
          console.log('RAG groundings used:', ragUsed);
        },
        onDone: () => {
          setLoading(false);
          loadSessions();
        },
        onError: (err: string) => {
          console.error('Stream error:', err);
          setError(err);
          setLoading(false);
        }
      });
    } catch (err: any) {
      console.error('Failed to send message:', err);
      setError(err.message || 'Failed to connect to assistant stream.');
      setLoading(false);
    }
  };

  const clearChat = async () => {
    if (!sessionId) return;
    try {
      await api.clearChatHistory(sessionId);
      setMessages([]);
      loadSessions();
    } catch (err) {
      console.error('Failed to clear chat history:', err);
    }
  };

  const deleteSession = async (sessionIdToDelete: string) => {
    try {
      await api.deleteSession(sessionIdToDelete);
      
      // If we deleted the current session, create a new one
      if (sessionIdToDelete === sessionId) {
        const newId = `session_${Math.random().toString(36).substring(2, 11)}`;
        setSessionId(newId);
        setMessages([]);
      }
      
      loadSessions();
    } catch (err) {
      console.error('Failed to delete session:', err);
      throw err;
    }
  };

  const switchSession = (newSessionId: string) => {
    setSessionId(newSessionId);
  };

  const createNewSession = () => {
    const id = `session_${Math.random().toString(36).substring(2, 11)}`;
    setSessionId(id);
    setMessages([]);
  };

  return {
    sessionId,
    messages,
    loading,
    error,
    aiStatus,
    sendMessage,
    clearChat,
    deleteSession,
    refreshHistory: loadHistory,
    refreshStatus: fetchAIStatus,
    sessions,
    switchSession,
    createNewSession,
    refreshSessions: loadSessions,
  };
};
