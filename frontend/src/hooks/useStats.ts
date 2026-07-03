import { useState, useEffect } from 'react';
import { api } from '../services/api';

export const useStats = (pollIntervalMs = 30000) => {
  const [logStats, setLogStats] = useState<any>(null);
  const [incidentStats, setIncidentStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<any>(null);

  const fetchStats = async () => {
    try {
      const [logs, incidents] = await Promise.all([
        api.getLogStats(),
        api.getIncidentStats(),
      ]);
      setLogStats(logs);
      setIncidentStats(incidents);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch statistics:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, pollIntervalMs);
    return () => clearInterval(interval);
  }, [pollIntervalMs]);

  return { logStats, incidentStats, loading, error, refetch: fetchStats };
};
