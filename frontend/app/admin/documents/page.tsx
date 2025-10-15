'use client';

import { useEffect, useState, useCallback } from 'react';
import AdminLayout from '@/components/AdminLayout';
import apiClient from '../../../config/axios';
import { API_URL } from '../../../config/api';

interface Document {
  id: number;
  filename: string;
  title: string;
  author?: string;
  category: string;
  subcategory?: string;
  total_pages: number;
  file_hash: string;
  processed_at: string;
  mc_press_url?: string;
  description?: string;
  tags?: string[];
}

interface PaginationInfo {
  page: number;
  perPage: number;
  total: number;
  totalPages: number;
}

export default function DocumentsManagement() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingData, setEditingData] = useState<Partial<Document>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortField, setSortField] = useState<keyof Document>('title');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    perPage: 20,
    total: 0,
    totalPages: 0,
  });
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<number | 'bulk' | null>(null);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [bulkAction, setBulkAction] = useState('');
  const [bulkValue, setBulkValue] = useState('');

  const categories = [
    'Programming', 'System Administration', 'Database',
    'Business Intelligence', 'Development Tools', 'Other'
  ];

  useEffect(() => {
    fetchDocuments();
  }, [pagination.page, searchTerm, categoryFilter, sortField, sortDirection]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);

      const params = new URLSearchParams({
        page: pagination.page.toString(),
        per_page: pagination.perPage.toString(),
        search: searchTerm,
        category: categoryFilter,
        sort_by: sortField,
        sort_direction: sortDirection,
      });

      try {
        const response = await apiClient.get(`${API_URL}/admin/documents?${params}`);
        const data = response.data;
        setDocuments(data.documents || []);
        setPagination(prev => ({
          ...prev,
          total: data.total || 0,
          totalPages: data.total_pages || 0,
        }));
      } catch (adminErr: any) {
        // Fallback to regular documents endpoint if admin endpoint doesn't exist yet
        if (adminErr.response?.status === 404) {
          const fallbackResponse = await apiClient.get(`${API_URL}/documents`);
          const data = fallbackResponse.data;
          const docs = data.documents || [];

          // Apply client-side filtering and sorting
          let filteredDocs = docs;
          if (searchTerm) {
            filteredDocs = filteredDocs.filter((doc: any) =>
              doc.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
              doc.author?.toLowerCase().includes(searchTerm.toLowerCase())
            );
          }
          if (categoryFilter) {
            filteredDocs = filteredDocs.filter((doc: any) =>
              doc.category === categoryFilter
            );
          }

          // Sort documents
          filteredDocs.sort((a: any, b: any) => {
            const aVal = a[sortField] || '';
            const bVal = b[sortField] || '';
            const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            return sortDirection === 'asc' ? comparison : -comparison;
          });

          // Paginate
          const start = (pagination.page - 1) * pagination.perPage;
          const paginatedDocs = filteredDocs.slice(start, start + pagination.perPage);

          setDocuments(paginatedDocs);
          setPagination(prev => ({
            ...prev,
            total: filteredDocs.length,
            totalPages: Math.ceil(filteredDocs.length / prev.perPage),
          }));
        } else {
          throw adminErr;
        }
      }
    } catch (err) {
      setError('Error connecting to server');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (field: keyof Document) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleSelectAll = () => {
    if (selectedIds.size === documents.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(documents.map(doc => doc.id)));
    }
  };

  const handleSelectOne = (id: number) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const startEditing = (doc: Document) => {
    setEditingId(doc.id);
    setEditingData({
      title: doc.title,
      author: doc.author,
      category: doc.category,
      subcategory: doc.subcategory,
      mc_press_url: doc.mc_press_url,
      description: doc.description,
      tags: doc.tags,
    });
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditingData({});
  };

  const saveEditing = async () => {
    if (!editingId) return;

    try {
      try {
        await apiClient.patch(`${API_URL}/admin/documents/${editingId}`, editingData);
        await fetchDocuments();
        cancelEditing();
      } catch (adminErr: any) {
        // Fallback to regular endpoint
        if (adminErr.response?.status === 404) {
          await apiClient.put(`${API_URL}/documents/${documents.find(d => d.id === editingId)?.filename}/metadata`, {
            title: editingData.title,
            author: editingData.author,
            category: editingData.category,
          });
          await fetchDocuments();
          cancelEditing();
        } else {
          throw adminErr;
        }
      }
    } catch (err) {
      setError('Error updating document');
      console.error('Update error:', err);
    }
  };

  const handleDelete = async () => {
    try {
      if (deleteTarget === 'bulk') {
        // Bulk delete
        try {
          await apiClient.delete(`${API_URL}/admin/documents/bulk`, {
            data: { ids: Array.from(selectedIds) },
          });
          setSelectedIds(new Set());
          await fetchDocuments();
        } catch (bulkErr: any) {
          // If bulk endpoint doesn't exist, delete one by one
          if (bulkErr.response?.status === 404) {
            for (const id of selectedIds) {
              const doc = documents.find(d => d.id === id);
              if (doc) {
                await apiClient.delete(`${API_URL}/documents/${doc.filename}`);
              }
            }
            setSelectedIds(new Set());
            await fetchDocuments();
          } else {
            throw bulkErr;
          }
        }
      } else if (typeof deleteTarget === 'number') {
        // Single delete
        const doc = documents.find(d => d.id === deleteTarget);
        if (doc) {
          await apiClient.delete(`${API_URL}/documents/${doc.filename}`);
          await fetchDocuments();
        }
      }
    } catch (err) {
      setError('Error deleting documents');
      console.error('Delete error:', err);
    } finally {
      setShowDeleteDialog(false);
      setDeleteTarget(null);
    }
  };

  const handleBulkAction = async () => {
    if (!bulkAction || selectedIds.size === 0) return;

    try {
      try {
        await apiClient.patch(`${API_URL}/admin/documents/bulk`, {
          ids: Array.from(selectedIds),
          action: bulkAction,
          value: bulkValue,
        });
        setSelectedIds(new Set());
        setBulkAction('');
        setBulkValue('');
        await fetchDocuments();
      } catch (bulkErr: any) {
        // If bulk endpoint doesn't exist, update one by one
        if (bulkErr.response?.status === 404) {
          for (const id of selectedIds) {
            const doc = documents.find(d => d.id === id);
            if (doc) {
              const updateData: any = {};
              if (bulkAction === 'category') updateData.category = bulkValue;
              if (bulkAction === 'author') updateData.author = bulkValue;

              await apiClient.put(`${API_URL}/documents/${doc.filename}/metadata`, updateData);
            }
          }
          setSelectedIds(new Set());
          setBulkAction('');
          setBulkValue('');
          await fetchDocuments();
        } else {
          throw bulkErr;
        }
      }
    } catch (err) {
      setError('Error performing bulk action');
      console.error('Bulk action error:', err);
    }
  };

  const exportToCSV = async () => {
    try {
      try {
        const response = await apiClient.get(`${API_URL}/admin/documents/export`, {
          responseType: 'blob',
        });
        const blob = response.data;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `documents_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
      } catch (exportErr: any) {
        // Fallback: generate CSV client-side
        if (exportErr.response?.status === 404) {
          const allDocsResponse = await apiClient.get(`${API_URL}/documents`);
          const data = allDocsResponse.data;
          const docs = data.documents || [];

          const csv = [
            'id,filename,title,author,category,subcategory,total_pages,processed_at',
            ...docs.map((doc: any) =>
              `${doc.id},"${doc.filename}","${doc.title || ''}","${doc.author || ''}","${doc.category || ''}","${doc.subcategory || ''}",${doc.total_pages || 0},"${doc.processed_at || ''}"`
            )
          ].join('\n');

          const blob = new Blob([csv], { type: 'text/csv' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `documents_${new Date().toISOString().split('T')[0]}.csv`;
          a.click();
        } else {
          throw exportErr;
        }
      }
    } catch (err) {
      setError('Error exporting documents');
      console.error('Export error:', err);
    }
  };

  const handleImportCSV = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      await apiClient.post(`${API_URL}/admin/documents/import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      await fetchDocuments();
      setShowImportDialog(false);
    } catch (err) {
      setError('Error importing CSV');
      console.error('Import error:', err);
    }
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="sm:flex sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Documents Management</h2>
            <p className="mt-1 text-sm text-gray-600">
              Manage document metadata and organization
            </p>
          </div>
          <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <div className="space-x-2">
              <button
                onClick={exportToCSV}
                className="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
              >
                Export CSV
              </button>
              <button
                onClick={() => setShowImportDialog(true)}
                className="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
              >
                Import CSV
              </button>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white shadow rounded-lg p-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label htmlFor="search" className="block text-sm font-medium text-gray-700">
                Search
              </label>
              <input
                type="text"
                id="search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                placeholder="Search by title or author..."
              />
            </div>
            <div>
              <label htmlFor="category" className="block text-sm font-medium text-gray-700">
                Category
              </label>
              <select
                id="category"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="">All Categories</option>
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Bulk Actions */}
        {selectedIds.size > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-blue-700">
                {selectedIds.size} document(s) selected
              </span>
              <div className="flex items-center space-x-2">
                <select
                  value={bulkAction}
                  onChange={(e) => setBulkAction(e.target.value)}
                  className="rounded-md border-gray-300 text-sm"
                >
                  <option value="">Select Action</option>
                  <option value="category">Update Category</option>
                  <option value="author">Update Author</option>
                  <option value="delete">Delete Selected</option>
                </select>
                {bulkAction && bulkAction !== 'delete' && (
                  <>
                    <input
                      type="text"
                      value={bulkValue}
                      onChange={(e) => setBulkValue(e.target.value)}
                      placeholder={`New ${bulkAction}...`}
                      className="rounded-md border-gray-300 text-sm"
                    />
                    <button
                      onClick={handleBulkAction}
                      className="inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700"
                    >
                      Apply
                    </button>
                  </>
                )}
                {bulkAction === 'delete' && (
                  <button
                    onClick={() => {
                      setDeleteTarget('bulk');
                      setShowDeleteDialog(true);
                    }}
                    className="inline-flex items-center justify-center rounded-md bg-red-600 px-3 py-1 text-sm font-medium text-white hover:bg-red-700"
                  >
                    Delete Selected
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Documents Table */}
        <div className="bg-white shadow rounded-lg overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading documents...</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center">
              <p className="text-red-600">{error}</p>
              <button
                onClick={fetchDocuments}
                className="mt-4 text-blue-600 hover:text-blue-500"
              >
                Try Again
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={selectedIds.size === documents.length && documents.length > 0}
                        onChange={handleSelectAll}
                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </th>
                    <th
                      onClick={() => handleSort('title')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Title {sortField === 'title' && (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                    <th
                      onClick={() => handleSort('author')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Author {sortField === 'author' && (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                    <th
                      onClick={() => handleSort('category')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Category {sortField === 'category' && (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Pages
                    </th>
                    <th
                      onClick={() => handleSort('processed_at')}
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      Uploaded {sortField === 'processed_at' && (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(doc.id)}
                          onChange={() => handleSelectOne(doc.id)}
                          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {editingId === doc.id ? (
                          <input
                            type="text"
                            value={editingData.title || ''}
                            onChange={(e) => setEditingData({ ...editingData, title: e.target.value })}
                            className="rounded-md border-gray-300 text-sm"
                          />
                        ) : (
                          <div>
                            <div className="text-sm font-medium text-gray-900">{doc.title}</div>
                            <div className="text-sm text-gray-500">{doc.filename}</div>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {editingId === doc.id ? (
                          <input
                            type="text"
                            value={editingData.author || ''}
                            onChange={(e) => setEditingData({ ...editingData, author: e.target.value })}
                            className="rounded-md border-gray-300 text-sm"
                          />
                        ) : (
                          <div className="text-sm text-gray-900">{doc.author || '-'}</div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {editingId === doc.id ? (
                          <select
                            value={editingData.category || ''}
                            onChange={(e) => setEditingData({ ...editingData, category: e.target.value })}
                            className="rounded-md border-gray-300 text-sm"
                          >
                            {categories.map(cat => (
                              <option key={cat} value={cat}>{cat}</option>
                            ))}
                          </select>
                        ) : (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                            {doc.category}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {doc.total_pages || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(doc.processed_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {editingId === doc.id ? (
                          <div className="space-x-2">
                            <button
                              onClick={saveEditing}
                              className="text-green-600 hover:text-green-900"
                            >
                              Save
                            </button>
                            <button
                              onClick={cancelEditing}
                              className="text-gray-600 hover:text-gray-900"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="space-x-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                startEditing(doc);
                              }}
                              className="text-blue-600 hover:text-blue-900"
                            >
                              Edit
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteTarget(doc.id);
                                setShowDeleteDialog(true);
                              }}
                              className="text-red-600 hover:text-red-900"
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {!loading && documents.length > 0 && (
            <div className="bg-white px-4 py-3 border-t border-gray-200 sm:px-6">
              <div className="flex items-center justify-between">
                <div className="flex-1 flex justify-between sm:hidden">
                  <button
                    onClick={() => setPagination(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
                    disabled={pagination.page === 1}
                    className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPagination(prev => ({ ...prev, page: Math.min(prev.totalPages, prev.page + 1) }))}
                    disabled={pagination.page === pagination.totalPages}
                    className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
                <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-gray-700">
                      Showing{' '}
                      <span className="font-medium">{(pagination.page - 1) * pagination.perPage + 1}</span>
                      {' '}to{' '}
                      <span className="font-medium">
                        {Math.min(pagination.page * pagination.perPage, pagination.total)}
                      </span>
                      {' '}of{' '}
                      <span className="font-medium">{pagination.total}</span>
                      {' '}documents
                    </p>
                  </div>
                  <div>
                    <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                      <button
                        onClick={() => setPagination(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
                        disabled={pagination.page === 1}
                        className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setPagination(prev => ({ ...prev, page: Math.min(prev.totalPages, prev.page + 1) }))}
                        disabled={pagination.page === pagination.totalPages}
                        className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                      >
                        Next
                      </button>
                    </nav>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Delete Confirmation Dialog */}
        {showDeleteDialog && (
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-medium text-gray-900">Confirm Delete</h3>
              <p className="mt-2 text-sm text-gray-500">
                {deleteTarget === 'bulk'
                  ? `Are you sure you want to delete ${selectedIds.size} document(s)? This action cannot be undone.`
                  : 'Are you sure you want to delete this document? This action cannot be undone.'}
              </p>
              <div className="mt-4 flex space-x-3">
                <button
                  onClick={handleDelete}
                  className="flex-1 inline-flex justify-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
                >
                  Delete
                </button>
                <button
                  onClick={() => {
                    setShowDeleteDialog(false);
                    setDeleteTarget(null);
                  }}
                  className="flex-1 inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Import CSV Dialog */}
        {showImportDialog && (
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-medium text-gray-900">Import CSV</h3>
              <p className="mt-2 text-sm text-gray-500">
                Select a CSV file to import document metadata. The file should contain columns for filename, title, author, category, etc.
              </p>
              <div className="mt-4">
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      handleImportCSV(file);
                    }
                  }}
                  className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50"
                />
              </div>
              <div className="mt-4 flex space-x-3">
                <button
                  onClick={() => setShowImportDialog(false)}
                  className="flex-1 inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}