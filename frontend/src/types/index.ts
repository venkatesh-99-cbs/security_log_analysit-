export interface SecurityLog {
  id: number;
  timestamp: string;
  source: string;
  category: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  message: string;
  raw_data?: Record<string, any>;
  file_id: number;
}

export interface MitreMapping {
  technique_id: string;
  technique_name: string;
  tactic: string;
}

export interface Incident {
  id: number;
  title: string;
  description: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  updated_at: string;
  mitre_mappings?: MitreMapping[];
  analyses?: AIAnalysis[];
  threat_score?: number;
  source_ip?: string;
  alert_count?: number;
}

export interface AIAnalysis {
  id: number;
  incident_id: number;
  query: string;
  response: string;
  analysis_type: string;
  created_at: string;
}

export interface UploadedFile {
  id: number;
  filename: string;
  status: 'uploaded' | 'processing' | 'processed' | 'failed';
  created_at: string;
  log_count?: number;
}

export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

export interface Report {
  id: number;
  title: string;
  report_type: string;
  created_at: string;
  exists: boolean;
}
