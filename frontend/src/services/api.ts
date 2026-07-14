import axios from 'axios';

// Get the base API URL from window location if running in production, or proxy to backend
const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // --- Logs ---
  uploadLog: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await client.post('/logs/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getLogs: async (params?: {
    skip?: number;
    limit?: number;
    severity?: string;
    category?: string;
    source?: string;
    file_id?: number;
  }) => {
    const response = await client.get('/logs/', { params });
    return response.data;
  },

  getFiles: async (params?: { skip?: number; limit?: number }) => {
    const response = await client.get('/logs/files', { params });
    return response.data;
  },

  getFile: async (id: number) => {
    const response = await client.get(`/logs/files/${id}`);
    return response.data;
  },

  getLogStats: async () => {
    const response = await client.get('/logs/stats');
    return response.data;
  },

  // --- Incidents ---
  getIncidents: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    severity?: string;
  }) => {
    const response = await client.get('/incidents/', { params });
    return response.data;
  },

  getIncidentStats: async () => {
    const response = await client.get('/incidents/stats');
    return response.data;
  },

  getIncident: async (id: number) => {
    const response = await client.get(`/incidents/${id}`);
    return response.data;
  },

  updateIncident: async (id: number, data: { status?: string; severity?: string }) => {
    const response = await client.patch(`/incidents/${id}`, null, { params: data });
    return response.data;
  },

  analyzeIncident: async (id: number) => {
    const response = await client.post(`/incidents/${id}/analyze`);
    return response.data;
  },

  // --- AI / Copilot ---
  chat: async (data: { session_id: string; message: string; use_rag?: boolean }) => {
    const response = await client.post('/ai/chat', data);
    return response.data;
  },

  getChatSessions: async () => {
    const response = await client.get('/ai/chat/sessions');
    return response.data;
  },

  getChatHistory: async (sessionId: string, limit?: number) => {
    const response = await client.get(`/ai/chat/${sessionId}/history`, { params: { limit } });
    return response.data;
  },

  clearChatHistory: async (sessionId: string) => {
    const response = await client.delete(`/ai/chat/${sessionId}/history`);
    return response.data;
  },

  deleteSession: async (sessionId: string) => {
    const response = await client.delete(`/ai/chat/${sessionId}`);
    return response.data;
  },

  getAIStatus: async () => {
    const response = await client.get('/ai/status');
    return response.data;
  },

  updateAISettings: async (data: { model: string }) => {
    const response = await client.post('/ai/settings', data);
    return response.data;
  },

  ingestKnowledge: async () => {
    const response = await client.post('/ai/rag/ingest');
    return response.data;
  },

  addKnowledge: async (data: { title: string; content: string; source?: string; category?: string }) => {
    const response = await client.post('/ai/rag/add', data);
    return response.data;
  },

  uploadKnowledgeFile: async (file: File, data: { title?: string; source?: string; category?: string }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (data.title) formData.append('title', data.title);
    if (data.source) formData.append('source', data.source);
    if (data.category) formData.append('category', data.category);
    const response = await client.post('/ai/rag/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // --- Reports ---
  generateReport: async (data: { title: string; severity_filter?: string }) => {
    const response = await client.post('/reports/generate', null, { params: data });
    return response.data;
  },

  getReports: async (params?: { skip?: number; limit?: number }) => {
    const response = await client.get('/reports/', { params });
    return response.data;
  },

  deleteReport: async (id: number) => {
    const response = await client.delete(`/reports/${id}`);
    return response.data;
  },

  getDownloadReportUrl: (id: number) => {
    return `${client.defaults.baseURL}/reports/${id}/download`;
  },

  // --- Health ---
  getHealth: async () => {
    const response = await client.get('/health/');
    return response.data;
  },
};
