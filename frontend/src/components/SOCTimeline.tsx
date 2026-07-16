/**
 * SOCTimeline — Professional Security Operations Center investigation timeline.
 *
 * Renders a vertical, chronologically-ordered list of pipeline events for
 * an incident. All timestamps are localized from UTC ISO strings using the
 * browser's Intl.DateTimeFormat — never hardcoded.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../services/api';
import { TimelineEvent } from '../types';
import { formatLocalTime, formatLocalDateTime } from '../utils/formatDate';
import {
  Upload,
  FileSearch,
  ShieldAlert,
  Target,
  Bot,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Clock,
} from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────

interface SOCTimelineProps {
  incidentId: number;
}

// ─── Event config ──────────────────────────────────────────────────────────

const EVENT_META: Record<
  string,
  { icon: React.ReactNode; label: string; dotClass: string; ringClass: string }
> = {
  log_uploaded: {
    icon: <Upload size={14} />,
    label: 'Uploaded',
    dotClass: 'bg-emerald-500',
    ringClass: 'ring-emerald-500/30',
  },
  parsing_completed: {
    icon: <FileSearch size={14} />,
    label: 'Parsed',
    dotClass: 'bg-sky-500',
    ringClass: 'ring-sky-500/30',
  },
  incident_detected: {
    icon: <ShieldAlert size={14} />,
    label: 'Detected',
    dotClass: 'bg-amber-500',
    ringClass: 'ring-amber-500/30',
  },
  mitre_mapped: {
    icon: <Target size={14} />,
    label: 'MITRE',
    dotClass: 'bg-red-500',
    ringClass: 'ring-red-500/30',
  },
  analysis_completed: {
    icon: <Bot size={14} />,
    label: 'AI Done',
    dotClass: 'bg-indigo-500',
    ringClass: 'ring-indigo-500/30',
  },
};

const SEVERITY_BADGE: Record<string, string> = {
  info:     'bg-sky-500/10     text-sky-400     border-sky-500/20',
  low:      'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  medium:   'bg-amber-500/10   text-amber-400   border-amber-500/20',
  high:     'bg-orange-500/10  text-orange-400  border-orange-500/20',
  critical: 'bg-red-500/10     text-red-400     border-red-500/20',
};

// ─── Component ─────────────────────────────────────────────────────────────

export const SOCTimeline: React.FC<SOCTimelineProps> = ({ incidentId }) => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newestFirst, setNewestFirst] = useState(true);

  const loadTimeline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getIncidentTimeline(incidentId);
      setEvents(data.events ?? []);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load timeline');
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  const displayed = newestFirst ? [...events].reverse() : events;

  const getEventMeta = (type: string) =>
    EVENT_META[type] ?? {
      icon: <Clock size={14} />,
      label: 'Event',
      dotClass: 'bg-slate-500',
      ringClass: 'ring-slate-500/30',
    };

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Clock size={15} className="text-sky-400" />
          Investigation Timeline
        </h3>

        <div className="flex items-center gap-2">
          {/* Newest / Oldest toggle */}
          <button
            onClick={() => setNewestFirst((v) => !v)}
            className="flex items-center gap-1 text-[10px] font-bold text-slate-500 hover:text-slate-300 px-2 py-1 rounded bg-slate-900 border border-slate-800 transition-colors"
            title={newestFirst ? 'Showing newest first' : 'Showing oldest first'}
          >
            {newestFirst ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
            {newestFirst ? 'Newest first' : 'Oldest first'}
          </button>

          <button
            onClick={loadTimeline}
            disabled={loading}
            className="p-1.5 text-slate-500 hover:text-slate-300 hover:bg-slate-800 rounded transition-colors"
            title="Refresh timeline"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Timeline body */}
      {loading ? (
        <div className="flex items-center gap-2 py-6 justify-center text-slate-500">
          <Loader2 size={18} className="animate-spin text-sky-400" />
          <span className="text-xs font-mono">Loading timeline...</span>
        </div>
      ) : error ? (
        <div className="py-4 text-center text-xs text-red-400 font-mono bg-red-500/5 border border-red-500/10 rounded-xl px-4">
          {error}
        </div>
      ) : displayed.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-600 italic">
          No timeline events available yet.
        </div>
      ) : (
        <ol className="relative flex flex-col gap-0">
          {displayed.map((event, idx) => {
            const meta = getEventMeta(event.event_type);
            const isLast = idx === displayed.length - 1;

            return (
              <li key={event.id} className="relative flex gap-4 group">
                {/* Connector line */}
                {!isLast && (
                  <div
                    className="absolute left-[15px] top-9 bottom-0 w-px bg-gradient-to-b from-slate-700 to-transparent"
                    aria-hidden="true"
                  />
                )}

                {/* Dot column */}
                <div className="flex-shrink-0 flex flex-col items-center pt-1">
                  <div
                    className={`
                      relative z-10 w-8 h-8 rounded-full flex items-center justify-center
                      ${meta.dotClass} ring-4 ${meta.ringClass}
                      text-white shadow-lg
                      transition-transform duration-200 group-hover:scale-110
                    `}
                  >
                    {meta.icon}
                  </div>
                </div>

                {/* Content card */}
                <div
                  className={`
                    flex-1 mb-5 p-4 rounded-xl border
                    bg-slate-950/80 border-slate-800/80
                    hover:border-slate-700/60 hover:bg-slate-950
                    transition-all duration-200
                    animate-fade-in
                  `}
                  style={{ animationDelay: `${idx * 60}ms` }}
                >
                  {/* Timestamp row */}
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className="text-[10px] font-mono font-bold text-sky-400 tabular-nums">
                      {formatLocalTime(event.timestamp)}
                    </span>
                    <span className="text-[9px] text-slate-600">
                      {formatLocalDateTime(event.timestamp)}
                    </span>
                    {/* Severity badge */}
                    <span
                      className={`ml-auto text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
                        SEVERITY_BADGE[event.severity] ?? SEVERITY_BADGE.info
                      }`}
                    >
                      {event.severity}
                    </span>
                  </div>

                  {/* Title */}
                  <h4 className="text-xs font-bold text-slate-200 mb-1">
                    {event.title}
                  </h4>

                  {/* Description */}
                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    {event.description}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
};

export default SOCTimeline;
