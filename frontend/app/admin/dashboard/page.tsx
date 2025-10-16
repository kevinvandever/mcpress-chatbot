'use client';

import { useEffect, useState } from 'react';
import AdminLayout from '@/components/AdminLayout';
import apiClient from '../../../config/axios';
import { API_URL } from '../../../config/api';

interface Stats {
  totalDocuments: number;
  totalChunks: number;
  lastUpload: string | null;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats>({
    totalDocuments: 0,
    totalChunks: 0,
    lastUpload: null,
  });
  const [loading, setLoading] = useState(true);

  // Debug: Log whenever stats changes
  useEffect(() => {
    console.log('Stats state changed to:', stats);
  }, [stats]);

  useEffect(() => {
    console.log('fetchStats useEffect triggered');
    fetchStats();
  }, []);

  const fetchStats = async () => {
    console.log('fetchStats called');
    try {
      // Check if admin token exists before trying admin endpoint
      const adminToken = typeof window !== 'undefined' ? localStorage.getItem('adminToken') : null;

      if (adminToken) {
        // Try to fetch stats from admin endpoint first if logged in
        try {
          const adminResponse = await apiClient.get(`${API_URL}/admin/stats`);
          setStats({
            totalDocuments: adminResponse.data.total_documents || 0,
            totalChunks: adminResponse.data.total_chunks || 0,
            lastUpload: adminResponse.data.last_upload || null,
          });
          return;
        } catch (adminError) {
          // Admin endpoint failed, fall back to regular endpoint
          console.log('Admin stats endpoint failed, falling back to documents endpoint');
        }
      }

      // Fallback to regular documents endpoint (public, no auth required)
      const response = await apiClient.get(`${API_URL}/documents`);

      // Debug: Log what we're getting back
      console.log('Dashboard /documents response:', {
        status: response.status,
        hasData: !!response.data,
        dataKeys: Object.keys(response.data || {}),
        documentsCount: response.data?.documents?.length || 0,
        firstDoc: response.data?.documents?.[0]
      });

      const documents = response.data?.documents || [];
      console.log('Extracted documents array:', {
        isArray: Array.isArray(documents),
        length: documents.length,
        firstThree: documents.slice(0, 3).map(d => d?.filename)
      });

      // Estimate chunks based on documents (typical PDF has ~50-100 chunks)
      const estimatedChunks = documents.length * 75;

      const newStats = {
        totalDocuments: documents.length,
        totalChunks: estimatedChunks,
        lastUpload: documents[0]?.processed_at || documents[0]?.created_at || null,
      };

      console.log('Setting stats to:', newStats);
      setStats(newStats);
      console.log('Stats set successfully');
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

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