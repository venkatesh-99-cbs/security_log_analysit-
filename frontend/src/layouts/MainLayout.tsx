import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { Shield, LayoutDashboard, FileUp, AlertTriangle, MessageSquare, FileText, Settings } from 'lucide-react';

const MainLayout: React.FC = () => {
  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 flex items-center gap-2 font-bold text-xl border-b border-slate-800">
          <Shield className="text-blue-400" />
          <span>SOC Assistant</span>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <Link to="/" className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded">
            <LayoutDashboard size={20} /> Dashboard
          </Link>
          <Link to="/logs" className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded">
            <FileUp size={20} /> Log Upload
          </Link>
          <Link to="/incidents" className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded">
            <AlertTriangle size={20} /> Incidents
          </Link>
          <Link to="/copilot" className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded">
            <MessageSquare size={20} /> AI Copilot
          </Link>
          <Link to="/reports" className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded">
            <FileText size={20} /> Reports
          </Link>
        </nav>
        <div className="p-4 border-t border-slate-800">
          <Link to="/settings" className="flex items-center gap-2 p-2 hover:bg-slate-800 rounded">
            <Settings size={20} /> Settings
          </Link>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
