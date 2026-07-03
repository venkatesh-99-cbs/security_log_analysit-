import React from 'react';
import { useIncidents } from '../hooks/useIncidents';
import { IncidentCard } from '../components/IncidentCard';
import { Loader2, ShieldAlert, RefreshCw, Filter } from 'lucide-react';

const Incidents: React.FC = () => {
  const { 
    incidents, 
    total, 
    loading, 
    filters, 
    updateFilters, 
    refetch 
  } = useIncidents();

  return (
    <div className="p-8 max-w-7xl mx-auto flex flex-col gap-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-4 border-b border-slate-900">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <ShieldAlert className="text-red-400" size={24} />
            Incident Response Queue
          </h1>
          <p className="page-subtitle">
            Correlated high-priority investigations generated from automated heuristics and anomaly clusters.
          </p>
        </div>

        <button 
          onClick={refetch}
          disabled={loading}
          className="btn-secondary btn-sm flex items-center gap-1.5"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Reload Incidents
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="glass-card p-4 flex flex-col sm:flex-row items-center gap-4">
        <span className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
          <Filter size={14} />
          Filter Settings
        </span>

        <div className="flex flex-wrap gap-4 w-full sm:w-auto">
          <div>
            <select
              value={filters.status}
              onChange={(e) => updateFilters({ status: e.target.value })}
              className="input bg-slate-950 border-slate-800 text-xs py-1.5"
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>

          <div>
            <select
              value={filters.severity}
              onChange={(e) => updateFilters({ severity: e.target.value })}
              className="input bg-slate-950 border-slate-800 text-xs py-1.5"
            >
              <option value="">All Severities</option>
              <option value="info">INFO</option>
              <option value="low">LOW</option>
              <option value="medium">MEDIUM</option>
              <option value="high">HIGH</option>
              <option value="critical">CRITICAL</option>
            </select>
          </div>
        </div>

        <span className="text-xs text-slate-500 font-medium ml-auto">
          Showing {incidents.length} of {total} investigation(s)
        </span>
      </div>

      {/* Main Grid View */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
          <Loader2 size={32} className="text-sky-400 animate-spin" />
          <span className="text-xs text-slate-500 font-mono">Triage matching events...</span>
        </div>
      ) : incidents.length === 0 ? (
        <div className="glass-card p-12 text-center flex flex-col items-center gap-4 justify-center">
          <div className="p-4 rounded-full bg-slate-800 border border-slate-700/60 text-slate-500">
            <ShieldAlert size={36} />
          </div>
          <div>
            <h4 className="font-bold text-slate-300 text-lg">No incidents triggered</h4>
            <p className="text-sm text-slate-500 max-w-sm mt-1">
              There are no current security incidents matching the configured rules and log signatures.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {incidents.map((incident) => (
            <IncidentCard key={incident.id} incident={incident} />
          ))}
        </div>
      )}
    </div>
  );
};

export default Incidents;
