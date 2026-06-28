import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import './index.css';

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          {/* Add other routes here */}
          <Route path="logs" element={<div>Log Upload Placeholder</div>} />
          <Route path="incidents" element={<div>Incident List Placeholder</div>} />
          <Route path="copilot" element={<div>AI Copilot Placeholder</div>} />
          <Route path="reports" element={<div>Reports Placeholder</div>} />
          <Route path="settings" element={<div>Settings Placeholder</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
