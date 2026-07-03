import React from 'react';
import { Incident } from '../types';
import { SeverityBadge } from './SeverityBadge';
import { StatusBadge } from './StatusBadge';
import { Link } from 'react-router-dom';
import { AlertCircle, Calendar, ShieldAlert } from 'lucide-react';

interface IncidentCardProps {
  incident: Incident;
}

export const IncidentCard: React.FC<IncidentCardProps> = ({ incident }) => {
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="glass-card-hover p-5 flex flex-col gap-4">
      <div className="flex justify-between items-start gap-4">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg mt-0.5 ${
            incident.severity === 'critical' || incident.severity === 'high'
              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
          }`}>
            <AlertCircle size={20} />
          </div>
          <div>
            <h4 className="font-bold text-slate-200 text-lg hover:text-sky-400 transition-colors">
              <Link to={`/incidents/${incident.id}`}>
                {incident.title}
              </Link>
            </h4>
            <div className="flex items-center gap-4 text-xs text-slate-500 mt-1">
              <span className="flex items-center gap-1">
                <Calendar size={12} />
                {formatDate(incident.created_at)}
              </span>
              {incident.source_ip && (
                <span>IP: <code className="font-mono text-slate-400">{incident.source_ip}</code></span>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <SeverityBadge severity={incident.severity} />
          <StatusBadge status={incident.status} />
        </div>
      </div>

      <p className="text-slate-400 text-sm line-clamp-3 leading-relaxed">
        {incident.description}
      </p>

      {incident.mitre_mappings && incident.mitre_mappings.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-800/60">
          {incident.mitre_mappings.slice(0, 3).map((m, idx) => (
            <span key={idx} className="mitre-chip" title={m.technique_name}>
              {m.technique_id}
            </span>
          ))}
          {incident.mitre_mappings.length > 3 && (
            <span className="text-xs text-slate-500 self-center font-semibold pl-1">
              +{incident.mitre_mappings.length - 3} more
            </span>
          )}
        </div>
      )}

      <div className="flex justify-between items-center mt-auto pt-3 border-t border-slate-800/60">
        {incident.threat_score !== undefined && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Threat Score</span>
            <span className={`text-sm font-bold font-mono px-2 py-0.5 rounded ${
              incident.threat_score >= 70
                ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                : incident.threat_score >= 40
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                : 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
            }`}>
              {incident.threat_score}/100
            </span>
          </div>
        )}
        <Link 
          to={`/incidents/${incident.id}`} 
          className="text-xs font-semibold text-sky-400 hover:text-sky-300 transition-colors flex items-center gap-1 ml-auto"
        >
          Investigate <ShieldAlert size={14} />
        </Link>
      </div>
    </div>
  );
};
