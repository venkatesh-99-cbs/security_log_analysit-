import React, { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { api } from '../services/api';
import { 
  Shield, 
  LayoutDashboard, 
  FileUp, 
  AlertTriangle, 
  MessageSquare, 
  FileText, 
  Settings,
  Server,
  Loader2
} from 'lucide-react';

const MainLayout: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<'healthy' | 'unhealthy' | 'loading'>('loading');
  const [ollamaStatus, setOllamaStatus] = useState<string>('disconnected');

  const checkHealth = async () => {
    try {
      const response = await api.getHealth();
      setHealthStatus('healthy');
      setOllamaStatus(response.ollama === 'connected' ? 'connected' : 'disconnected');
    } catch {
      setHealthStatus('unhealthy');
      setOllamaStatus('disconnected');
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 overflow-hidden font-sans">
      
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 border-r border-slate-850 flex flex-col justify-between flex-shrink-0">
        <div>
          {/* Brand header */}
          <div className="p-6 flex items-center gap-2.5 font-extrabold text-lg border-b border-slate-850">
            <div className="p-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Shield size={20} />
            </div>
            <span className="tracking-tight text-slate-100">SOC ASSISTANT</span>
          </div>
          
          {/* Links list */}
          <nav className="flex-1 p-4 space-y-1.5 flex flex-col">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-3 mb-2 block">Commands</span>
            
            <NavLink 
              to="/" 
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
            >
              <LayoutDashboard size={18} />
              Operations Room
            </NavLink>
            
            <NavLink 
              to="/logs" 
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
            >
              <FileUp size={18} />
              Log Ingestion
            </NavLink>
            
            <NavLink 
              to="/incidents" 
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
            >
              <AlertTriangle size={18} />
              Incident Queue
            </NavLink>
            
            <NavLink 
              to="/copilot" 
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
            >
              <MessageSquare size={18} />
              AI Copilot
            </NavLink>
            
            <NavLink 
              to="/reports" 
              className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
            >
              <FileText size={18} />
              Reports Archive
            </NavLink>
          </nav>
        </div>

        {/* Sidebar Footer / System status */}
        <div className="p-4 border-t border-slate-850 flex flex-col gap-3">
          <NavLink 
            to="/settings" 
            className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
          >
            <Settings size={18} />
            System Settings
          </NavLink>

          <div className="mt-2 bg-slate-950/60 p-3 rounded-lg border border-slate-850 flex flex-col gap-2">
            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1">
              <Server size={10} />
              Infrastructure Status
            </span>
            <div className="flex flex-col gap-1.5 mt-1">
              <div className="flex justify-between items-center text-[10px] font-mono">
                <span className="text-slate-400">Backend Server:</span>
                <span className="flex items-center gap-1 font-bold">
                  {healthStatus === 'loading' ? (
                    <Loader2 size={10} className="animate-spin text-slate-500" />
                  ) : healthStatus === 'healthy' ? (
                    <>
                      <span className="status-dot status-dot-online"></span>
                      ONLINE
                    </>
                  ) : (
                    <>
                      <span className="status-dot status-dot-offline"></span>
                      OFFLINE
                    </>
                  )}
                </span>
              </div>
              <div className="flex justify-between items-center text-[10px] font-mono">
                <span className="text-slate-400">AI Inference:</span>
                <span className="flex items-center gap-1 font-bold">
                  {ollamaStatus === 'connected' ? (
                    <>
                      <span className="status-dot status-dot-online"></span>
                      CONNECTED
                    </>
                  ) : (
                    <>
                      <span className="status-dot status-dot-offline"></span>
                      DISCONNECTED
                    </>
                  )}
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main panel */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>

    </div>
  );
};

export default MainLayout;
