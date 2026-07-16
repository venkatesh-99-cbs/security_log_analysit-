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
  upload_id?: number | null;
  upload_filename?: string;
  upload_created_at?: string | null;
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
  /** File size in bytes (populated after upload) */
  file_size?: number | null;
  /** Number of security alerts/findings detected during pipeline processing */
  findings_count?: number | null;
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

/** A single event in the SOC investigation timeline for an incident. */
export interface TimelineEvent {
  id: string;
  event_type:
    | 'log_uploaded'
    | 'parsing_completed'
    | 'incident_detected'
    | 'mitre_mapped'
    | 'analysis_completed'
    | string;
  title: string;
  description: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
  /** UTC ISO timestamp string from the backend — localize on the frontend */
  timestamp: string | null;
}

export interface IncidentTimeline {
  incident_id: number;
  events: TimelineEvent[];
}
