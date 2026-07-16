import { useState, useEffect, useCallback, useRef } from 'react';
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

  const abortControllerRef = useRef<AbortController | null>(null);
  const sessionIdRef = useRef(sessionId);
  const generatingSessionRef = useRef<string | null>(null);

  // Keep sessionIdRef updated with active sessionId
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Auto-generate session ID if not provided
  useEffect(() => {
    if (!sessionId) {
      const id = `session_${Math.random().toString(36).substring(2, 11)}`;
      setSessionId(id);
    }
  }, [sessionId]);

  const loadHistory = useCallback(async () => {
    if (!sessionId) return;
    const requestedSessionId = sessionId;
    try {
      const history = await api.getChatHistory(sessionId);
      // A quick tab switch can leave an older request in flight. Never let
      // that response replace the newly selected conversation.
      if (sessionIdRef.current === requestedSessionId) setMessages(history);
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

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const sendMessage = async (text: string, useRag = true) => {
    if (!text.trim() || !sessionId || loading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const targetSessionId = sessionId;

    const now = new Date().toISOString();
    const userMessage: ChatMessage = { role: 'user', content: text, timestamp: now };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    generatingSessionRef.current = targetSessionId;
    setError(null);

    let currentAssistantContent = '';

    setMessages((prev) => [...prev, { role: 'assistant', content: '', timestamp: new Date().toISOString() }]);

    try {
      await api.chatStream({
        session_id: targetSessionId,
        message: text,
        use_rag: useRag,
      }, {
        onToken: (token: string) => {
          if (sessionIdRef.current !== targetSessionId) return;
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
          if (sessionIdRef.current !== targetSessionId) return;
          setLoading(false);
          generatingSessionRef.current = null;
          loadSessions();
        },
        onError: (err: string) => {
          if (sessionIdRef.current !== targetSessionId) return;
          if (err.includes('aborted') || err.includes('AbortError')) {
            return;
          }
          console.error('Stream error:', err);
          setError(err);
          setLoading(false);
          generatingSessionRef.current = null;
        }
      }, controller.signal);
    } catch (err: any) {
      if (sessionIdRef.current !== targetSessionId) return;
      if (err.name === 'AbortError' || err.message?.includes('aborted')) return;
      console.error('Failed to send message:', err);
      setError(err.message || 'Failed to connect to assistant stream.');
      setLoading(false);
      generatingSessionRef.current = null;
    }
  };

  const cancelGeneration = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    generatingSessionRef.current = null;
    setLoading(false);
    setMessages((prev) => prev.filter((message, index) => !(index === prev.length - 1 && message.role === 'assistant' && !message.content)));
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
    // Keep any existing stream alive in the background, but make the newly
    // selected conversation immediately interactive.
    setLoading(false);
    setError(null);
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
    cancelGeneration,
  };
};
