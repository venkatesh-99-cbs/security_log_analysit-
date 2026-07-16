import React from 'react';

interface SeverityBadgeProps {
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical' | string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const safeSeverity = severity ? String(severity) : 'info';
  const sev = safeSeverity.toLowerCase();
  
  let className = 'badge-info';
  if (sev === 'critical') className = 'badge-critical';
  else if (sev === 'high') className = 'badge-high';
  else if (sev === 'medium') className = 'badge-medium';
  else if (sev === 'low') className = 'badge-low';

  return (
    <span className={`badge ${className}`}>
      {safeSeverity.toUpperCase()}
    </span>
  );
};
