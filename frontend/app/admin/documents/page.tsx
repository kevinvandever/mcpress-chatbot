'use client';

import { useEffect, useState, useCallback } from 'react';
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
  const [allDocuments, setAllDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<keyof Document>('title');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [pagination, setPagination] = useState<PaginationInfo>({
    page: 1,
    perPage: 20,
    total: 0,
    totalPages: 0,
  });
  
  // Edit form state
  const [editForm, setEditForm] = useState({
    title: '',
    author: '',
    mc_press_url: '',
    article_url: '',
    author_site_url: '',
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const fetchDocuments = useCallback(async (forceRefresh = false) => {
    try {
      console.log('PAGINATION_FIX_ACTIVE_v2');
      setLoading(true);
      // Use refresh parameter to bypass cache
      const endpoint = `${API_URL}/admin/documents${forceRefresh ? '?refresh=true' : ''}`;
      const response = await apiClient.get(endpoint);
      const data = response.data;
      const docs = data.documents || [];
      setAllDocuments(docs);
    } catch (err) {
      setError('Failed to fetch documents from server');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Filter, sort, and paginate documents when dependencies change
  useEffect(() => {
    let filteredDocs = [...allDocuments];
    
    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filteredDocs = filteredDocs.filter((doc: Document) =>
        doc.title?.toLowerCase().includes(term) ||
        doc.filename?.toLowerCase().includes(term) ||
        doc.author?.toLowerCase().includes(term) ||
        doc.authors?.some(author => author.name.toLowerCase().includes(term))
      );
    }

    // Sort documents
    filteredDocs.sort((a: Document, b: Document) => {
      const aVal = String(a[sortField] || '').toLowerCase();
      const bVal = String(b[sortField] || '').toLowerCase();
      const comparison = aVal.localeCompare(bVal);
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    // Calculate pagination info
    const totalPages = Math.ceil(filteredDocs.length / pagination.perPage);
    const currentPage = Math.min(pagination.page, totalPages || 1);
    
    // Paginate
    const start = (currentPage - 1) * pagination.perPage;
    const paginatedDocs = filteredDocs.slice(start, start + pagination.perPage);

    setDocuments(paginatedDocs);
    setPagination(prev => ({
      ...prev,
      page: currentPage,
      total: filteredDocs.length,
      totalPages,
    }));
  }, [allDocuments, searchTerm, sortField, sortDirection, pagination.perPage]);

  // Update edit form when selected document changes
  useEffect(() => {
    if (selectedDoc) {
      // Get primary author's site URL
      const primaryAuthorSiteUrl = selectedDoc.authors?.[0]?.site_url || '';
      
      setEditForm({
        title: selectedDoc.title || '',
        author: selectedDoc.authors?.[0]?.name || selectedDoc.author || '',
        mc_press_url: selectedDoc.mc_press_url || '',
        article_url: selectedDoc.article_url || '',
        author_site_url: primaryAuthorSiteUrl,
      });
      setSaveError(null);
      setSaveSuccess(null);
    }
  }, [selectedDoc]);

  const handleSort = (field: keyof Document) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
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

  const validateForm = () => {
    if (!editForm.title.trim()) {
      return 'Title is required';
    }
    if (editForm.mc_press_url.trim() && !editForm.mc_press_url.startsWith('http')) {
      return 'MC Press URL must start with http:// or https://';
    }
    if (editForm.article_url.trim() && !editForm.article_url.startsWith('http')) {
      return 'Article URL must start with http:// or https://';
    }
    if (editForm.author_site_url.trim() && !editForm.author_site_url.startsWith('http')) {
      return 'Author URL must start with http:// or https://';
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
      
      // Update document metadata (title, author name, URLs)
      await apiClient.put(`${API_URL}/documents/${encodedFilename}/metadata`, {
        filename: selectedDoc.filename,
        title: editForm.title.trim(),
        author: editForm.author.trim(),
        category: selectedDoc.category || null,
        mc_press_url: editForm.mc_press_url.trim() || null,
        article_url: editForm.article_url.trim() || null
      });
      
      // If author site URL changed and we have an author ID, update it separately
      if (selectedDoc.authors?.[0]?.id && editForm.author_site_url !== (selectedDoc.authors[0].site_url || '')) {
        try {
          await apiClient.patch(`${API_URL}/api/authors/${selectedDoc.authors[0].id}`, {
            site_url: editForm.author_site_url.trim() || null
          });
        } catch (authorErr) {
          console.warn('Could not update author site URL:', authorErr);
          // Don't fail the whole operation if author URL update fails
        }
      }

      setSaveSuccess('Changes saved successfully!');
      
      // Force refresh to get updated data
      await fetchDocuments(true);
      
      // Find and update the selected document to reflect changes
      setTimeout(() => {
        setAllDocuments(prev => {
          const updatedDoc = prev.find(d => d.filename === selectedDoc.filename);
          if (updatedDoc) {
            setSelectedDoc(updatedDoc);
          }
          return prev;
        });
      }, 100);
      
    } catch (err: unknown) {
      const errorMessage = (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail 
        || (err as { message?: string })?.message 
        || 'Error saving changes';
      setSaveError(errorMessage);
      console.error('Save error:', err);
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
      await fetchDocuments(true);
    } catch (err) {
      setError('Error deleting document');
      console.error('Delete error:', err);
    }
  };

  // Helper function to format author display - FIXED MULTI-AUTHOR LOGIC
  const formatAuthorDisplay = (doc: Document) => {
    if (doc.authors && doc.authors.length > 0) {
      if (doc.authors.length === 1) {
        // Single author - no "Multi-author:" prefix
        return doc.authors[0].name;
      } else {
        // Multiple authors - show "Multi-author:" prefix
        return `Multi-author: ${doc.authors.map(a => a.name).join(', ')}`;
      }
    }
    // Fallback to legacy author field
    return doc.author || 'Unknown Author';
  };

  return (
    <AdminLayout>
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Document Management</h2>
          <p className="text-sm text-gray-600">
            {selectedDoc ? 'Edit document details in the panel below' : 'Click a document to view and edit details'}
          </p>
        </div>

        {/* Search */}
        <div className="flex-shrink-0 mb-4">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPagination(prev => ({ ...prev, page: 1 }));
            }}
            className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
            placeholder="Search by title, author, or filename..."
          />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 min-h-0 flex flex-col">
          {/* Documents Table */}
          <div className={`bg-white rounded-lg shadow flex-1 min-h-0 ${selectedDoc ? 'mb-4' : ''}`}>
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-600 text-sm">Loading documents...</p>
              </div>
            ) : error ? (
              <div className="p-8 text-center">
                <p className="text-red-600 mb-4">{error}</p>
                <button onClick={() => fetchDocuments()} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                  Try Again
                </button>
              </div>
            ) : (
              <div className="overflow-auto h-full">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th
                        onClick={() => handleSort('title')}
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      >
                        Title {sortField === 'title' && (sortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th
                        onClick={() => handleSort('author')}
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      >
                        Author {sortField === 'author' && (sortDirection === 'asc' ? '↑' : '↓')}
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
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
                        <td className="px-4 py-2">
                          <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                            {doc.title || doc.filename}
                          </div>
                        </td>
                        <td className="px-4 py-2">
                          <div className="text-sm text-gray-900 truncate max-w-xs">
                            {formatAuthorDisplay(doc)}
                          </div>
                        </td>
                        <td className="px-4 py-2">
                          <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                            doc.document_type === 'article'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}>
                            {doc.document_type || 'book'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Pagination */}
          {!loading && !error && (
            <div className="flex-shrink-0 flex items-center justify-between py-3 bg-white border-t border-gray-200">
              <span className="text-sm text-gray-700">
                {pagination.total} documents
              </span>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setPagination(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
                  disabled={pagination.page <= 1}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Prev
                </button>
                <span className="px-3 py-1 text-sm">
                  {pagination.page} / {pagination.totalPages || 1}
                </span>
                <button
                  onClick={() => setPagination(prev => ({ ...prev, page: Math.min(prev.totalPages, prev.page + 1) }))}
                  disabled={pagination.page >= pagination.totalPages}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {/* Edit Panel */}
          {selectedDoc && (
            <div className="flex-shrink-0 bg-white rounded-lg shadow-lg border border-gray-200">
              {/* Panel Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
                <h3 className="font-semibold text-gray-900">Edit Document</h3>
                <button
                  onClick={closePanel}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Panel Content */}
              <div className="p-4">
                {/* Status Messages */}
                {saveError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                    {saveError}
                  </div>
                )}
                {saveSuccess && (
                  <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                    {saveSuccess}
                  </div>
                )}

                {/* Form Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Left Column */}
                  <div className="space-y-4">
                    {/* Filename (read-only) */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                        Filename
                      </label>
                      <div className="text-sm text-gray-900 bg-gray-50 p-2 rounded">
                        {selectedDoc.filename}
                      </div>
                    </div>

                    {/* Title (editable) */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                        Title *
                      </label>
                      <input
                        type="text"
                        value={editForm.title}
                        onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                        className="w-full rounded border-gray-300 text-sm focus:border-blue-500 focus:ring-blue-500"
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
                        className="w-full rounded border-gray-300 text-sm focus:border-blue-500 focus:ring-blue-500"
                      />
                      {selectedDoc.authors && selectedDoc.authors.length > 1 && (
                        <p className="mt-1 text-xs text-gray-500">
                          Additional authors: {selectedDoc.authors.slice(1).map(a => a.name).join(', ')}
                        </p>
                      )}
                    </div>

                    {/* Author Website URL (editable) - FIXED */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                        Author Website URL
                      </label>
                      <input
                        type="url"
                        value={editForm.author_site_url}
                        onChange={(e) => setEditForm({ ...editForm, author_site_url: e.target.value })}
                        className="w-full rounded border-gray-300 text-sm focus:border-blue-500 focus:ring-blue-500"
                        placeholder="https://author-website.com"
                      />
                    </div>
                  </div>

                  {/* Right Column */}
                  <div className="space-y-4">
                    {/* Document Type (read-only) */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                        Type
                      </label>
                      <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                        selectedDoc.document_type === 'article'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {selectedDoc.document_type || 'book'}
                      </span>
                    </div>

                    {/* MC Press URL (editable) */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                        MC Press URL (Purchase Link)
                      </label>
                      <input
                        type="url"
                        value={editForm.mc_press_url}
                        onChange={(e) => setEditForm({ ...editForm, mc_press_url: e.target.value })}
                        className="w-full rounded border-gray-300 text-sm focus:border-blue-500 focus:ring-blue-500"
                        placeholder="https://mcpress.link/..."
                      />
                    </div>

                    {/* Article URL (editable) */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
                        Article URL
                      </label>
                      <input
                        type="url"
                        value={editForm.article_url}
                        onChange={(e) => setEditForm({ ...editForm, article_url: e.target.value })}
                        className="w-full rounded border-gray-300 text-sm focus:border-blue-500 focus:ring-blue-500"
                        placeholder="https://..."
                      />
                    </div>

                    {/* Metadata (read-only) */}
                    <div className="pt-2 border-t border-gray-200">
                      <label className="block text-xs font-medium text-gray-500 uppercase mb-2">
                        Metadata
                      </label>
                      <div className="space-y-1 text-xs text-gray-600">
                        <div>
                          <span className="text-gray-500">Pages: </span>
                          <span className="text-gray-900">{selectedDoc.total_pages || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Chunks: </span>
                          <span className="text-gray-900">{selectedDoc.chunk_count || 'N/A'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Panel Footer with Actions */}
                <div className="flex justify-between items-center pt-4 border-t border-gray-200 mt-6">
                  <button
                    onClick={() => setShowDeleteDialog(true)}
                    className="px-4 py-2 text-sm font-medium text-red-600 border border-red-300 rounded hover:bg-red-50"
                  >
                    Delete
                  </button>
                  
                  <div className="flex space-x-3">
                    <button
                      onClick={closePanel}
                      className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-100"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={saveChanges}
                      disabled={isSaving}
                      className={`px-6 py-2 text-sm font-medium text-white rounded ${
                        isSaving
                          ? 'bg-gray-400 cursor-not-allowed'
                          : 'bg-blue-600 hover:bg-blue-700'
                      }`}
                    >
                      {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteDialog && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-md w-full mx-6 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Confirm Delete</h3>
            <p className="text-sm text-gray-500 mt-2">
              Are you sure you want to delete &quot;{selectedDoc?.title}&quot;? This action cannot be undone.
            </p>
            <div className="mt-4 flex space-x-3 justify-end">
              <button
                onClick={() => setShowDeleteDialog(false)}
                className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  );
}