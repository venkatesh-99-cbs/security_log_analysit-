import React from 'react';
import { useIncidents } from '../hooks/useIncidents';
import { IncidentCard } from '../components/IncidentCard';
import { Loader2, ShieldAlert, RefreshCw, Filter, Trash2, UploadCloud } from 'lucide-react';

const Incidents: React.FC = () => {
  const { 
    incidents, 
    total, 
    loading, 
    filters, 
    updateFilters, 
    refetch,
    deleteIncident,
    bulkDeleteIncidents
    , error
  } = useIncidents();

  const handleDeleteIndividual = async (id: number, title: string) => {
    if (window.confirm(`Are you sure you want to delete incident: "${title}"?\nThis cannot be undone.`)) {
      try {
        await deleteIncident(id);
      } catch (err) {
        alert('Failed to delete incident.');
      }
    }
  };

  const handleDeleteAll = async () => {
    if (window.confirm('Are you sure you want to clear the entire incident response queue?\nAll incident data, AI analyses, and MITRE maps will be permanently deleted.')) {
      try {
        await bulkDeleteIncidents([], true);
      } catch (err) {
        alert('Failed to clear incident queue.');
      }
    }
  };

  const groupedIncidents = incidents.reduce<Record<string, typeof incidents>>((groups, incident) => {
    const key = incident.upload_id ? String(incident.upload_id) : 'unassigned';
    (groups[key] ||= []).push(incident);
    return groups;
  }, {});

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

        <div className="flex items-center gap-2">
          {incidents.length > 0 && (
            <button
              onClick={handleDeleteAll}
              disabled={loading}
              className="btn-danger btn-sm flex items-center gap-1.5 font-semibold text-xs py-2 px-3 border border-red-500/25 bg-red-500/10 hover:bg-red-500/25 rounded-xl transition-all"
            >
              <Trash2 size={14} />
              Clear Queue
            </button>
          )}
          <button 
            onClick={refetch}
            disabled={loading}
            className="btn-secondary btn-sm flex items-center gap-1.5"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Reload Incidents
          </button>
        </div>
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
            <h4 className="font-bold text-slate-300 text-lg">{error ? 'Incident queue unavailable' : 'No incidents triggered'}</h4>
            <p className="text-sm text-slate-500 max-w-sm mt-1">
              {error ? 'The incident service could not be reached. Reload the queue to try again.' : 'There are no current security incidents matching the configured rules and log signatures.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="queue-scroll-area flex flex-col gap-6 pr-2">
          {Object.entries(groupedIncidents).map(([uploadKey, uploadIncidents], index) => {
            const first = uploadIncidents[0];
            return (
              <section key={uploadKey} className="incident-upload-group">
                <div className="incident-upload-heading">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="incident-upload-icon"><UploadCloud size={16} /></span>
                    <div className="min-w-0">
                      <p className="incident-upload-kicker">Log upload {index + 1}</p>
                      <h2 className="incident-upload-title truncate">{first.upload_filename || 'Unassigned upload'}</h2>
                    </div>
                  </div>
                  <span className="incident-upload-count">{uploadIncidents.length} {uploadIncidents.length === 1 ? 'incident' : 'incidents'}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 p-5">
                  {uploadIncidents.map((incident) => (
                    <IncidentCard key={incident.id} incident={incident} onDelete={() => handleDeleteIndividual(incident.id, incident.title)} />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Incidents;
