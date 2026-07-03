import React from 'react';
import { useStats } from '../hooks/useStats';
import { StatCard } from '../components/StatCard';
import { SeverityBadge } from '../components/SeverityBadge';
import { Link } from 'react-router-dom';
import { 
  ShieldAlert, 
  FileCode, 
  Activity, 
  Terminal, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  ExternalLink,
  Bot
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip 
} from 'recharts';

const SEVERITY_COLORS = {
  critical: '#f87171', // Red
  high: '#fb923c',     // Orange
  medium: '#fbbf24',   // Yellow
  low: '#4ade80',      // Green
  info: '#38bdf8',     // Sky Blue
};

const Dashboard: React.FC = () => {
  const { logStats, incidentStats, loading, error } = useStats();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] gap-3">
        <Loader2 size={36} className="text-sky-400 animate-spin" />
        <span className="text-sm text-slate-500 font-medium font-mono">Loading telemetry database...</span>
      </div>
    );
  }

  // Calculate values
  const totalLogs = logStats?.total_logs || 0;
  const openIncidents = incidentStats?.open || 0;
  const totalFiles = logStats?.total_files || 0;
  const filesProcessing = logStats?.files_processing || 0;

  // Pie chart data
  const pieData = Object.entries(logStats?.severity_breakdown || {}).map(([key, value]) => ({
    name: key.toUpperCase(),
    value,
    color: (SEVERITY_COLORS as any)[key] || '#64748b',
  })).filter((d) => d.value > 0);

  // Fallback if empty
  const hasPieData = pieData.length > 0;
  const dummyPieData = [
    { name: 'INFO', value: 1, color: '#38bdf8' }
  ];

  // Dummy activity chart data
  const activityData = [
    { time: '02:00', events: 12 },
    { time: '04:00', events: 19 },
    { time: '06:00', events: 3 },
    { time: '08:00', events: 45 },
    { time: '10:00', events: totalLogs > 0 ? Math.min(totalLogs, 150) : 10 },
  ];

  // Determine system threat level
  let threatLevel = 'LOW';
  let threatColor = 'text-green-400 border-green-500/20 bg-green-500/5';
  
  if (openIncidents > 3) {
    threatLevel = 'CRITICAL';
    threatColor = 'text-red-400 border-red-500/20 bg-red-500/5';
  } else if (openIncidents > 0) {
    threatLevel = 'ELEVATED';
    threatColor = 'text-amber-400 border-amber-500/20 bg-amber-500/5';
  }

  return (
    <div className="p-8 max-w-7xl mx-auto flex flex-col gap-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex justify-between items-center pb-4 border-b border-slate-900">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight flex items-center gap-2">
            SOC Operations Command
          </h1>
          <p className="text-slate-500 text-sm mt-1 font-medium font-mono">
            Security Log Analysis Assistant &bull; Offline AI Copilot Enabled
          </p>
        </div>

        <div className={`flex items-center gap-3 px-4 py-2 border rounded-xl font-bold font-mono text-sm ${threatColor}`}>
          <ShieldAlert size={18} />
          SYSTEM THREAT LEVEL: {threatLevel}
        </div>
      </div>

      {/* Grid Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard 
          title="Total Parsed Log Events" 
          value={totalLogs.toLocaleString()}
          icon={<Terminal size={22} />}
          description="Consolidated log records"
        />
        <StatCard 
          title="Active Investigations" 
          value={openIncidents}
          icon={<ShieldAlert size={22} />}
          description="Open incidents requiring action"
        />
        <StatCard 
          title="Total Files Uploaded" 
          value={totalFiles}
          icon={<FileCode size={22} />}
          description={filesProcessing > 0 ? `${filesProcessing} files processing...` : 'All files processed'}
        />
        <div className="stat-card">
          <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">AI Copilot Status</p>
          <div className="flex justify-between items-center mt-3">
            <span className="flex items-center gap-2 text-sm font-bold text-slate-200">
              <Bot size={18} className="text-sky-400" />
              Ollama Core
            </span>
            <span className="flex items-center gap-1.5 text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700/60">
              <span className="status-dot status-dot-online"></span>
              ONLINE
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-3 font-mono">Model: qwen3:8b (Local)</p>
        </div>
      </div>

      {/* Charts section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Activity chart */}
        <div className="glass-card p-6 lg:col-span-2 flex flex-col gap-4">
          <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
            <Activity size={18} className="text-sky-400" />
            Ingestion Traffic Timeline
          </h3>
          <div className="h-64 mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activityData}>
                <defs>
                  <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="#475569" fontSize={11} tickLine={false} />
                <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
                  labelClassName="text-slate-400 font-mono text-xs font-bold"
                  itemStyle={{ color: '#38bdf8', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="events" stroke="#0ea5e9" strokeWidth={2} fillOpacity={1} fill="url(#colorEvents)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Severity distribution */}
        <div className="glass-card p-6 flex flex-col gap-4">
          <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
            <ShieldAlert size={18} className="text-sky-400" />
            Severity Breakdown
          </h3>
          <div className="h-56 mt-2 relative flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={hasPieData ? pieData : dummyPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {(hasPieData ? pieData : dummyPieData).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px' }}
                  itemStyle={{ fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
            
            {/* Center label */}
            <div className="absolute flex flex-col items-center justify-center">
              <span className="text-2xl font-extrabold text-slate-100 font-mono">
                {hasPieData ? pieData.length : 0}
              </span>
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Categories</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-x-4 gap-y-2 justify-center text-xs mt-2">
            {(hasPieData ? pieData : []).map((d) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }}></span>
                <span className="text-slate-400 font-medium">{d.name}: {d.value}</span>
              </div>
            ))}
            {!hasPieData && (
              <span className="text-slate-500 italic">No logs categorized yet.</span>
            )}
          </div>
        </div>
      </div>

      {/* Navigation Quicklinks */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t border-slate-900">
        <Link 
          to="/logs" 
          className="glass-card-hover p-5 flex items-center justify-between group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-sky-500/10 border border-sky-500/20 text-sky-400 rounded-lg">
              <FileCode size={20} />
            </div>
            <div>
              <h4 className="font-bold text-slate-200 group-hover:text-sky-400 transition-colors">Log Ingestion</h4>
              <p className="text-xs text-slate-500 mt-0.5">Upload new log sources for threat audit</p>
            </div>
          </div>
          <ExternalLink size={16} className="text-slate-600 group-hover:text-sky-400 transition-colors" />
        </Link>

        <Link 
          to="/incidents" 
          className="glass-card-hover p-5 flex items-center justify-between group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg">
              <ShieldAlert size={20} />
            </div>
            <div>
              <h4 className="font-bold text-slate-200 group-hover:text-red-400 transition-colors">Incident Queue</h4>
              <p className="text-xs text-slate-500 mt-0.5">Investigate correlated security events</p>
            </div>
          </div>
          <ExternalLink size={16} className="text-slate-600 group-hover:text-red-400 transition-colors" />
        </Link>

        <Link 
          to="/copilot" 
          className="glass-card-hover p-5 flex items-center justify-between group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-lg">
              <Bot size={20} />
            </div>
            <div>
              <h4 className="font-bold text-slate-200 group-hover:text-indigo-400 transition-colors">AI Copilot Chat</h4>
              <p className="text-xs text-slate-500 mt-0.5">Query security database with local AI</p>
            </div>
          </div>
          <ExternalLink size={16} className="text-slate-600 group-hover:text-indigo-400 transition-colors" />
        </Link>
      </div>
    </div>
  );
};

export default Dashboard;
