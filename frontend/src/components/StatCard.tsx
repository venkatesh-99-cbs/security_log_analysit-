import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  description?: string;
  trend?: {
    value: string | number;
    isPositive: boolean;
  };
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, icon, description, trend }) => {
  return (
    <div className="stat-card">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">{title}</p>
          <h3 className="text-3xl font-bold text-slate-100 mt-2">{value}</h3>
        </div>
        <div className="p-3 bg-slate-800/80 rounded-lg text-sky-400 border border-slate-700/50">
          {icon}
        </div>
      </div>
      {trend && (
        <div className="flex items-center gap-1.5 mt-2 text-xs">
          <span className={trend.isPositive ? 'text-green-400' : 'text-red-400'}>
            {trend.value}
          </span>
          <span className="text-slate-500">vs last period</span>
        </div>
      )}
      {description && !trend && (
        <p className="text-xs text-slate-500 mt-2">{description}</p>
      )}
    </div>
  );
};
