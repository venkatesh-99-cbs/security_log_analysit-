import { useState, useEffect, useCallback } from 'react';
import { ChatMessage } from '../types';
import { api } from '../services/api';

export const useChat = (initialSessionId?: string) => {
  const [sessionId, setSessionId] = useState(initialSessionId || '');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAIStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

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
    fetchAIStatus();
  }, [sessionId, loadHistory]);

  const sendMessage = async (text: string, useRag = true) => {
    if (!text.trim() || !sessionId || loading) return;

    const userMessage: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    try {
      const response = await api.chat({
        session_id: sessionId,
        message: text,
        use_rag: useRag,
      });

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error('Failed to send message:', err);
      setError(err.response?.data?.detail || 'Failed to get response from AI. Please check if Ollama is running.');
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    if (!sessionId) return;
    try {
      await api.clearChatHistory(sessionId);
      setMessages([]);
    } catch (err) {
      console.error('Failed to clear chat history:', err);
    }
  };

  return {
    sessionId,
    messages,
    loading,
    error,
    aiStatus,
    sendMessage,
    clearChat,
    refreshHistory: loadHistory,
    refreshStatus: fetchAIStatus,
  };
};
