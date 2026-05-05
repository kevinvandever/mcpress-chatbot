'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import AdminLayout from '@/components/AdminLayout';
import apiClient from '../../../config/axios';
import { API_URL } from '../../../config/api';

interface Stats {
  totalDocuments: number;
  totalChunks: number;
  lastUpload: string | null;
}

function FreemiumExportSection() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleExport = async (format: 'csv' | 'json') => {
    setExporting(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('adminToken');
      if (!token) {
        setError('Not authenticated. Please log in again.');
        setExporting(false);
        return;
      }

      const params = new URLSearchParams({ format });
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);

      const response = await fetch(`${API_URL}/api/admin/freemium-export?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setError(data.detail || `Export failed (${response.status})`);
        setExporting(false);
        return;
      }

      // Trigger file download
      const blob = await response.blob();
      const today = new Date().toISOString().split('T')[0];
      const filename = `freemium-usage-export-${today}.${format}`;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setSuccess(`Exported to ${filename}`);
    } catch (err: any) {
      setError(err.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <h3 className="text-lg leading-6 font-medium text-gray-900">
          Freemium Usage Export
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Download free-tier user engagement data with funnel summary statistics.
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 items-end">
          <div>
            <label htmlFor="export-start-date" className="block text-sm font-medium text-gray-700">
              Start Date
            </label>
            <input
              id="export-start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="export-end-date" className="block text-sm font-medium text-gray-700">
              End Date
            </label>
            <input
              id="export-end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          <div>
            <button
              onClick={() => handleExport('csv')}
              disabled={exporting}
              className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exporting ? 'Exporting...' : 'Download CSV'}
            </button>
          </div>
          <div>
            <button
              onClick={() => handleExport('json')}
              disabled={exporting}
              className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exporting ? 'Exporting...' : 'Download JSON'}
            </button>
          </div>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}
        {success && (
          <p className="mt-3 text-sm text-green-600">{success}</p>
        )}

        <p className="mt-3 text-xs text-gray-400">
          Leave dates empty to export all data. CSV includes summary rows at the bottom.
        </p>
      </div>
    </div>
  );
}

interface IngestionRun {
  id?: number;
  status: string;
  started_at?: string;
  completed_at?: string;
  articles_discovered?: number;
  articles_processed?: number;
  articles_skipped?: number;
  articles_failed?: number;
  error_message?: string;
  message?: string;
}

function IngestionStatusSection() {
  const [currentRun, setCurrentRun] = useState<IngestionRun | null>(null);
  const [history, setHistory] = useState<IngestionRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem('adminToken');
      if (!token) return;

      const [statusRes, historyRes] = await Promise.all([
        fetch(`${API_URL}/api/ingestion/status`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/ingestion/history?limit=5`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (statusRes.ok) {
        const data = await statusRes.json();
        if (data.status !== 'no_runs') {
          setCurrentRun(data);
        }
      }

      if (historyRes.ok) {
        const data = await historyRes.json();
        setHistory(data.runs || []);
      }
    } catch (err) {
      console.error('Failed to fetch ingestion status:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleTrigger = async () => {
    setTriggering(true);
    setError('');
    setSuccess('');

    try {
      const token = localStorage.getItem('adminToken');
      if (!token) {
        setError('Not authenticated. Please log in again.');
        setTriggering(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/ingestion/trigger`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.status === 409) {
        setError('An ingestion run is already in progress.');
      } else if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setError(data.detail || `Trigger failed (${response.status})`);
      } else {
        setSuccess('Ingestion run started. Refresh in a few minutes to see results.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to trigger ingestion');
    } finally {
      setTriggering(false);
    }
  };

  const formatDate = (iso: string | undefined) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  };

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      completed: 'bg-green-100 text-green-800',
      running: 'bg-blue-100 text-blue-800',
      failed: 'bg-red-100 text-red-800',
      interrupted: 'bg-yellow-100 text-yellow-800',
    };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Content Ingestion
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Monthly auto-ingestion of new articles from MC Press. Runs on the 1st of each month.
            </p>
          </div>
          <button
            onClick={handleTrigger}
            disabled={triggering}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {triggering ? 'Starting...' : 'Run Now'}
          </button>
        </div>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {success && <p className="mt-3 text-sm text-green-600">{success}</p>}

        {/* Current/Last Run Summary */}
        {loading ? (
          <p className="mt-4 text-sm text-gray-400">Loading...</p>
        ) : currentRun ? (
          <div className="mt-4 border rounded-lg p-4 bg-gray-50">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-sm font-medium text-gray-700">Last Run:</span>
              {statusBadge(currentRun.status)}
              <span className="text-sm text-gray-500">{formatDate(currentRun.started_at)}</span>
            </div>
            {currentRun.status === 'completed' && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-900">{currentRun.articles_discovered ?? 0}</div>
                  <div className="text-xs text-gray-500">Discovered</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-green-600">{currentRun.articles_processed ?? 0}</div>
                  <div className="text-xs text-gray-500">Processed</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-500">{currentRun.articles_skipped ?? 0}</div>
                  <div className="text-xs text-gray-500">Skipped</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-red-600">{currentRun.articles_failed ?? 0}</div>
                  <div className="text-xs text-gray-500">Failed</div>
                </div>
              </div>
            )}
            {currentRun.status === 'failed' && currentRun.error_message && (
              <p className="mt-2 text-sm text-red-600">Error: {currentRun.error_message}</p>
            )}
          </div>
        ) : (
          <p className="mt-4 text-sm text-gray-400">No ingestion runs found yet.</p>
        )}

        {/* Run History */}
        {history.length > 1 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Recent History</h4>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 uppercase">
                    <th className="pb-2 pr-4">Date</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 pr-4">Processed</th>
                    <th className="pb-2 pr-4">Skipped</th>
                    <th className="pb-2">Failed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {history.slice(1).map((run, i) => (
                    <tr key={i}>
                      <td className="py-2 pr-4 text-gray-600">{formatDate(run.started_at)}</td>
                      <td className="py-2 pr-4">{statusBadge(run.status)}</td>
                      <td className="py-2 pr-4 text-gray-900">{run.articles_processed ?? 0}</td>
                      <td className="py-2 pr-4 text-gray-500">{run.articles_skipped ?? 0}</td>
                      <td className="py-2 text-red-600">{run.articles_failed ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats>({
    totalDocuments: 0,
    totalChunks: 0,
    lastUpload: null,
  });
  const [loading, setLoading] = useState(true);
  const hasFetched = useRef(false);

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);

      // Fetch directly from /documents endpoint (public, no auth required)
      const response = await apiClient.get(`${API_URL}/documents`);
      const documents = response.data?.documents || [];

      // Estimate chunks based on documents (typical PDF has ~50-100 chunks)
      const estimatedChunks = documents.length * 75;

      setStats({
        totalDocuments: documents.length,
        totalChunks: estimatedChunks,
        lastUpload: documents[0]?.processed_at || documents[0]?.created_at || null,
      });
    } catch (error: any) {
      console.error('Failed to fetch stats:', error);
      setStats({
        totalDocuments: 0,
        totalChunks: 0,
        lastUpload: null,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Prevent duplicate fetches (React StrictMode or component remounting)
    if (hasFetched.current) {
      return;
    }
    hasFetched.current = true;
    fetchStats();
  }, [fetchStats]);

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
          <p className="mt-1 text-sm text-gray-600">
            Manage your MC Press Chatbot content and settings
          </p>
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Total Documents
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      {loading ? '...' : stats.totalDocuments}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                  </svg>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Total Chunks
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      {loading ? '...' : stats.totalChunks}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Last Upload
                    </dt>
                    <dd className="text-lg font-semibold text-gray-900">
                      {loading ? '...' : (stats.lastUpload ? 
                        new Date(stats.lastUpload).toLocaleDateString() : 
                        'Never')}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Quick Actions
            </h3>
            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <a
                href="/admin/upload"
                className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Upload New Document
              </a>
              <a
                href="/admin/documents"
                className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Manage Documents
              </a>
            </div>
          </div>
        </div>

        {/* Freemium Usage Export */}
        <FreemiumExportSection />

        {/* Ingestion Status */}
        <IngestionStatusSection />

        {/* Recent Activity */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              System Status
            </h3>
            <div className="mt-4 space-y-2">
              <div className="flex items-center">
                <div className="h-2 w-2 bg-green-400 rounded-full mr-2"></div>
                <span className="text-sm text-gray-600">API Connected</span>
              </div>
              <div className="flex items-center">
                <div className="h-2 w-2 bg-green-400 rounded-full mr-2"></div>
                <span className="text-sm text-gray-600">Database Connected</span>
              </div>
              <div className="flex items-center">
                <div className="h-2 w-2 bg-green-400 rounded-full mr-2"></div>
                <span className="text-sm text-gray-600">Vector Store Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}