import React, { useState } from 'react';
import { SecurityLog } from '../types';
import { SeverityBadge } from './SeverityBadge';
import { ChevronDown, ChevronRight, Eye } from 'lucide-react';

interface LogTableProps {
  logs: SecurityLog[];
}

export const LogTable: React.FC<LogTableProps> = ({ logs }) => {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const toggleRow = (id: number) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleString();
    } catch {
      return dateStr;
    }
  };

  if (!logs || logs.length === 0) {
    return (
      <div className="glass-card p-8 text-center text-slate-500">
        No security logs found matching the current filters.
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="table">
        <thead>
          <tr>
            <th className="w-10"></th>
            <th className="w-48">Timestamp</th>
            <th className="w-24">Severity</th>
            <th className="w-36">Source</th>
            <th className="w-36">Category</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => {
            const isExpanded = expandedRow === log.id;
            return (
              <React.Fragment key={log.id}>
                <tr 
                  className={`cursor-pointer ${isExpanded ? 'bg-slate-800/20' : ''}`}
                  onClick={() => toggleRow(log.id)}
                >
                  <td className="text-center">
                    {isExpanded ? (
                      <ChevronDown size={16} className="text-slate-500" />
                    ) : (
                      <ChevronRight size={16} className="text-slate-500" />
                    )}
                  </td>
                  <td className="font-mono text-xs">{formatDate(log.timestamp)}</td>
                  <td>
                    <SeverityBadge severity={log.severity} />
                  </td>
                  <td className="font-medium text-slate-300">{log.source}</td>
                  <td>
                    <span className="px-2 py-0.5 bg-slate-800 border border-slate-700/60 rounded text-xs text-slate-400">
                      {log.category}
                    </span>
                  </td>
                  <td className="max-w-md truncate text-slate-300" title={log.message}>
                    {log.message}
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td></td>
                    <td colSpan={5} className="bg-slate-900/60 px-6 py-4">
                      <div className="flex flex-col gap-3">
                        <div className="flex items-center gap-2 text-xs font-semibold text-sky-400">
                          <Eye size={14} />
                          Raw Event Data Details
                        </div>
                        <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-xs font-mono text-slate-400 overflow-x-auto max-h-96">
                          {JSON.stringify(log.raw_data || log, null, 2)}
                        </pre>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
