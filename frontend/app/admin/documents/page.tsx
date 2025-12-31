'use client';

import { useEffect, useState } from 'react';
import AdminLayout from '@/components/AdminLayout';
import apiClient from '../../../config/axios';
import { API_URL } from '../../../config/api';

interface Author {
  id: number | null;
  name: string;
  site_url?: string | null;
}

interface Document {
  id?: number;
  filename: string;
  title: string;
  author?: string;
  authors?: Author[];
  category?: string;
  total_pages?: string | number;
  uploaded_at?: string;
  mc_press_url?: string;
  article_url?: string;
  document_type?: 'book' | 'article';
  chunk_count?: number;
}

interface PaginationInfo {
  page: number;
  perPage: number;
  total: number;
  totalPages: number;
}

export default function DocumentsManagement() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<keyof Document>('title');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    perPage: 25,
    total: 0,
    totalPages: 0,
  });
  
  // Edit form state
  const [editForm, setEditForm] = useState({
    title: '',
    author: '',
    mc_press_url: '',
    article_url: '',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  
  // Delete state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  useEffect(() => {
    fetchDocuments();
  }, [pagination.page, searchTerm, sortField, sortDirection]);

  // Update edit form when selected document changes
  useEffect(() => {
    if (selectedDoc) {
      setEditForm({
        title: selectedDoc.title || '',
        author: selectedDoc.author || '',
        mc_press_url: selectedDoc.mc_press_url || '',
        article_url: selectedDoc.article_url || '',
      });
      setSaveError(null);
      setSaveSuccess(null);
    }
  }, [selectedDoc]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`${API_URL}/documents`);
      const data = response.data;
      const docs = data.documents || [];

      // Apply client-side filtering and sorting
      let filteredDocs = docs;
      if (searchTerm) {
        filteredDocs = filteredDocs.filter((doc: Document) =>
          doc.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          doc.author?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          doc.filename?.toLowerCase().includes(searchTerm.toLowerCase())
        );
      }

      // Sort documents
      filteredDocs.sort((a: Document, b: Document) => {
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

  const selectDocument = (doc: Document) => {
    setSelectedDoc(doc);
  };

  const closePanel = () => {
    setSelectedDoc(null);
    setSaveError(null);
    setSaveSuccess(null);
  };

  const validateForm = (): string | null => {
    if (!editForm.title.trim()) {
      return 'Title is required';
    }
    if (editForm.mc_press_url.trim() && !editForm.mc_press_url.startsWith('http')) {
      return 'MC Press URL must start with http:// or https://';
    }
    if (editForm.article_url.trim() && !editForm.article_url.startsWith('http')) {
      return 'Article URL must start with http:// or https://';
    }
    return null;
  };

  const saveChanges = async () => {
    if (!selectedDoc) return;

    const validationError = validateForm();
    if (validationError) {
      setSaveError(validationError);
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    try {
      const encodedFilename = encodeURIComponent(selectedDoc.filename);
      await apiClient.put(`${API_URL}/documents/${encodedFilename}/metadata`, {
        filename: selectedDoc.filename,
        title: editForm.title.trim(),
        author: editForm.author.trim(),
        category: null,
        mc_press_url: editForm.mc_press_url.trim() || null,
        article_url: editForm.article_url.trim() || null,
      });
      
      setSaveSuccess('Changes saved successfully!');
      await fetchDocuments();
      
      // Update selected doc with new values
      setSelectedDoc(prev => prev ? {
        ...prev,
        title: editForm.title.trim(),
        author: editForm.author.trim(),
        mc_press_url: editForm.mc_press_url.trim() || undefined,
        article_url: editForm.article_url.trim() || undefined,
      } : null);
      
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Error updating document';
      setSaveError(errorMessage);
      console.error('Update error:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedDoc) return;
    
    try {
      const encodedFilename = encodeURIComponent(selectedDoc.filename);
      await apiClient.delete(`${API_URL}/documents/${encodedFilename}`);
      setShowDeleteDialog(false);
      setSelectedDoc(null);
      await fetchDocuments();
    } catch (err) {
      setError('Error deleting document');
      console.error('Delete error:', err);
    }
  };

  return (
    <AdminLayout>
      <div className="flex h-full">
        {/* Main List Panel */}
        <div className={`flex-1 ${selectedDoc ? 'pr-4' : ''}`}>
          <div className="space-y-4">
            {/* Header */}
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Documents</h2>
              <p className="text-sm text-gray-600">Click a document to view and edit details</p>
            </div>

            {/* Search */}
            <div>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                placeholder="Search by title, author, or filename..."
              />
            </div>

            {/* Documents List */}
            <div className="bg-white shadow rounded-lg overflow-hidden">
              {loading ? (
                <div className="p-8 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-gray-600 text-sm">Loading...</p>
                </div>
              ) : error ? (
                <div className="p-8 text-center">
                  <p className="text-red-600">{error}</p>
                  <button onClick={fetchDocuments} className="mt-2 text-blue-600 hover:text-blue-500 text-sm">
                    Try Again
                  </button>
                </div>
              ) : (
                <>
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th
                          onClick={() => handleSort('title')}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        >
                          Title {sortField === 'title' && (sortDirection === 'asc' ? '↑' : '↓')}
                        </th>
                        <th
                          onClick={() => handleSort('author')}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                        >
                          Author {sortField === 'author' && (sortDirection === 'asc' ? '↑' : '↓')}
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Type
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {documents.map((doc) => (
                        <tr
                          key={doc.filename}
                          onClick={() => selectDocument(doc)}
                          className={`cursor-pointer hover:bg-blue-50 ${
                            selectedDoc?.filename === doc.filename ? 'bg-blue-100' : ''
                          }`}
                        >
                          <td className="px-4 py-3">
                            <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                              {doc.title}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-sm text-gray-600 truncate max-w-xs">
                              {doc.authors && doc.authors.length > 0
                                ? doc.authors.map(a => a.name).join(', ')
                                : doc.author || '-'}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                              doc.document_type === 'article'
                                ? 'bg-purple-100 text-purple-800'
                                : 'bg-blue-100 text-blue-800'
                            }`}>
                              {doc.document_type || 'book'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* Pagination */}
                  <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 flex items-center justify-between">
                    <span className="text-sm text-gray-700">
                      {pagination.total} documents
                    </span>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setPagination(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
                        disabled={pagination.page === 1}
                        className="px-3 py-1 text-sm border rounded disabled:opacity-50"
                      >
                        Prev
                      </button>
                      <span className="px-3 py-1 text-sm">
                        {pagination.page} / {pagination.totalPages || 1}
                      </span>
                      <button
                        onClick={() => setPagination(prev => ({ ...prev, page: Math.min(prev.totalPages, prev.page + 1) }))}
                        disabled={pagination.page >= pagination.totalPages}
                        className="px-3 py-1 text-sm border rounded disabled:opacity-50"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Detail Panel */}
        {selectedDoc && (
          <div className="w-96 bg-white shadow-lg rounded-lg border-l border-gray-200 overflow-y-auto">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
              <h3 className="font-semibold text-gray-900">Document Details</h3>
              <button
                onClick={closePanel}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* Status Messages */}
              {saveError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                  {saveError}
                </div>
              )}
              {saveSuccess && (
                <div className="p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                  {saveSuccess}
                </div>
              )}

              {/* Filename (read-only) */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                  Filename
                </label>
                <div className="text-sm text-gray-900 bg-gray-50 p-2 rounded break-all">
                  {selectedDoc.filename}
                </div>
              </div>

              {/* Document Type (read-only) */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                  Type
                </label>
                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                  selectedDoc.document_type === 'article'
                    ? 'bg-purple-100 text-purple-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {selectedDoc.document_type || 'book'}
                </span>
              </div>

              {/* Title (editable) */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                  Title
                </label>
                <input
                  type="text"
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="w-full rounded border-gray-300 text-sm"
                />
              </div>

              {/* Author (editable) */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                  Author
                </label>
                <input
                  type="text"
                  value={editForm.author}
                  onChange={(e) => setEditForm({ ...editForm, author: e.target.value })}
                  className="w-full rounded border-gray-300 text-sm"
                  placeholder="Author name"
                />
                {selectedDoc.authors && selectedDoc.authors.length > 0 && (
                  <p className="mt-1 text-xs text-gray-500">
                    Multi-author: {selectedDoc.authors.map(a => a.name).join(', ')}
                  </p>
                )}
              </div>

              {/* Author URLs (read-only for now) */}
              {selectedDoc.authors && selectedDoc.authors.some(a => a.site_url) && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                    Author URLs
                  </label>
                  <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded space-y-1">
                    {selectedDoc.authors.map((author, idx) => (
                      <div key={idx} className="break-all">
                        <span className="font-medium">{author.name}:</span>{' '}
                        {author.site_url || '-'}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Article URL (editable for articles) */}
              {selectedDoc.document_type === 'article' && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                    Article URL
                  </label>
                  <input
                    type="url"
                    value={editForm.article_url}
                    onChange={(e) => setEditForm({ ...editForm, article_url: e.target.value })}
                    className="w-full rounded border-gray-300 text-sm"
                    placeholder="https://..."
                  />
                </div>
              )}

              {/* MC Press URL (editable) */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                  MC Press URL
                </label>
                <input
                  type="url"
                  value={editForm.mc_press_url}
                  onChange={(e) => setEditForm({ ...editForm, mc_press_url: e.target.value })}
                  className="w-full rounded border-gray-300 text-sm"
                  placeholder="https://mcpress.link/..."
                />
              </div>

              {/* Additional Info (read-only) */}
              <div className="pt-2 border-t border-gray-200">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500">Pages:</span>{' '}
                    <span className="text-gray-900">{selectedDoc.total_pages || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Chunks:</span>{' '}
                    <span className="text-gray-900">{selectedDoc.chunk_count || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Category:</span>{' '}
                    <span className="text-gray-900">{selectedDoc.category || 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-gray-200 space-y-2">
                <button
                  onClick={saveChanges}
                  disabled={isSaving}
                  className={`w-full py-2 px-4 rounded font-medium text-white ${
                    isSaving
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
                <button
                  onClick={() => setShowDeleteDialog(true)}
                  className="w-full py-2 px-4 rounded font-medium text-red-600 border border-red-300 hover:bg-red-50"
                >
                  Delete Document
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        {showDeleteDialog && (
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-medium text-gray-900">Confirm Delete</h3>
              <p className="mt-2 text-sm text-gray-500">
                Are you sure you want to delete "{selectedDoc?.title}"? This action cannot be undone.
              </p>
              <div className="mt-4 flex space-x-3">
                <button
                  onClick={handleDelete}
                  className="flex-1 inline-flex justify-center rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
                >
                  Delete
                </button>
                <button
                  onClick={() => setShowDeleteDialog(false)}
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
