import React from 'react';

interface StatusBadgeProps {
  status: 'open' | 'in_progress' | 'resolved' | 'closed' | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const stat = status.toLowerCase();
  
  let className = 'badge-closed';
  let dotColor = 'bg-slate-400';
  let label = 'Closed';

  if (stat === 'open') {
    className = 'badge-open';
    dotColor = 'bg-red-400 animate-pulse';
    label = 'Open';
  } else if (stat === 'in_progress') {
    className = 'badge-in_progress';
    dotColor = 'bg-amber-400 animate-pulse';
    label = 'In Progress';
  } else if (stat === 'resolved') {
    className = 'badge-resolved';
    dotColor = 'bg-green-400';
    label = 'Resolved';
  }

  return (
    <span className={`badge ${className} gap-1.5`}>
      <span className={`status-dot ${dotColor}`}></span>
      {label}
    </span>
  );
};
