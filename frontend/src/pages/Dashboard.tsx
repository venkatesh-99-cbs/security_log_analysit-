import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Security Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded shadow">
          <h2 className="font-semibold">Total Logs</h2>
          <p className="text-3xl">0</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <h2 className="font-semibold">Open Incidents</h2>
          <p className="text-3xl">0</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <h2 className="font-semibold">Threat Level</h2>
          <p className="text-3xl text-green-500">Low</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
