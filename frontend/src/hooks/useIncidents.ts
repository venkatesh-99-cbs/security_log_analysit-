import { useState, useEffect, useCallback } from 'react';
import { Incident } from '../types';
import { api } from '../services/api';

export const useIncidents = (initialFilters?: { status?: string; severity?: string }) => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<any>(null);
  const [filters, setFilters] = useState({
    status: initialFilters?.status || '',
    severity: initialFilters?.severity || '',
    skip: 0,
    limit: 50,
  });

  const fetchIncidents = useCallback(async () => {
    setLoading(true);
    try {
      const cleanParams: any = {
        skip: filters.skip,
        limit: filters.limit,
      };
      if (filters.status) cleanParams.status = filters.status;
      if (filters.severity) cleanParams.severity = filters.severity;
      
      const response = await api.getIncidents(cleanParams);
      // Keep the queue resilient to both the paginated API response and a
      // plain array response (useful while the backend is being upgraded).
      const items = Array.isArray(response) ? response : (response?.items || []);
      setIncidents(items);
      setTotal(Array.isArray(response) ? items.length : (response?.total ?? items.length));
      setError(null);
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  const updateFilters = (newFilters: Partial<typeof filters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters, skip: 0 })); // Reset page to 0 on filter change
  };

  const deleteIncident = async (id: number) => {
    try {
      await api.deleteIncident(id);
      await fetchIncidents();
    } catch (err) {
      console.error('Failed to delete incident:', err);
      throw err;
    }
  };

  const bulkDeleteIncidents = async (ids?: number[], deleteAll = false) => {
    try {
      await api.bulkDeleteIncidents(ids, deleteAll);
      await fetchIncidents();
    } catch (err) {
      console.error('Failed to bulk delete incidents:', err);
      throw err;
    }
  };

  return { 
    incidents, 
    total, 
    loading, 
    error, 
    filters, 
    updateFilters, 
    refetch: fetchIncidents,
    deleteIncident,
    bulkDeleteIncidents
  };
};
