'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
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
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteSummary, setDeleteSummary] = useState<{
    chunks_deleted: number;
    author_associations_deleted: number;
    metadata_history_deleted: number;
  } | null>(null);

  // Bulk selection state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  // Bulk delete state
  const [showBulkDeleteDialog, setShowBulkDeleteDialog] = useState(false);
  const [bulkDeleteLoading, setBulkDeleteLoading] = useState(false);
  const [bulkDeleteError, setBulkDeleteError] = useState<string | null>(null);
  const [bulkDeleteSummary, setBulkDeleteSummary] = useState<any>(null);

  // Reindex state
  const [reindexLoading, setReindexLoading] = useState(false);
  const [showReindexDialog, setShowReindexDialog] = useState(false);
  const [reindexStatus, setReindexStatus] = useState<string | null>(null);
  const reindexPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Update indeterminate state on the "select all" checkbox
  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      const docsWithIds = documents.filter(doc => doc.id !== undefined);
      const allSelected = docsWithIds.length > 0 && docsWithIds.every(doc => selectedIds.has(doc.id!));
      const someSelected = docsWithIds.some(doc => selectedIds.has(doc.id!));
      selectAllCheckboxRef.current.indeterminate = someSelected && !allSelected;
    }
  }, [selectedIds, documents]);

  // Debounced search to avoid too many API calls
  const [searchInput, setSearchInput] = useState('');
  
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchInput !== searchTerm) {
        setSearchTerm(searchInput);
        setPagination(prev => ({ ...prev, page: 1 })); // Reset to first page when searching
        setSelectedIds(new Set()); // Clear selections on search change
      }
    }, 300); // 300ms debounce
    
    return () => clearTimeout(timer);
  }, [searchInput, searchTerm]);

  const fetchDocuments = useCallback(async (forceRefresh = false, page = 1, search = '', sortField = 'title', sortDirection = 'asc') => {
    try {
      console.log('PAGINATION_FIX_ACTIVE_v2');
      setLoading(true);
      setError(null);
      
      // Build query parameters for server-side pagination
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('per_page', pagination.perPage.toString());
      if (search) params.append('search', search);
      params.append('sort_by', sortField);
      params.append('sort_direction', sortDirection);
      if (forceRefresh) params.append('refresh', 'true');
      
      const endpoint = `${API_URL}/admin/documents?${params.toString()}`;
      console.log(`📡 Fetching documents from: ${endpoint}${forceRefresh ? ' (cache bypass)' : ''}`);
      
      const response = await apiClient.get(endpoint);
      const data = response.data;
      const docs = data.documents || [];
      
      console.log(`✅ Fetched ${docs.length} documents (page ${page})${forceRefresh ? ' (fresh from database)' : ''}`);
      
      // Update documents and pagination info from server response
      setDocuments(docs);
      setPagination({
        page: data.page || page,
        perPage: data.per_page || pagination.perPage,
        total: data.total || 0,
        totalPages: data.total_pages || 1,
      });
      
      // For compatibility, also set allDocuments (though we won't use it for pagination anymore)
      setAllDocuments(docs);
    } catch (err) {
      setError('Failed to fetch documents from server');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [pagination.perPage]);

  // Initial load
  useEffect(() => {
    fetchDocuments(false, 1, '', sortField, sortDirection);
  }, []); // Only run once on mount

  // Fetch documents when pagination, search, or sort changes (but not on initial render)
  useEffect(() => {
    // Skip if this is the initial state (page 1, no search, default sort)
    if (pagination.page === 1 && searchTerm === '' && sortField === 'title' && sortDirection === 'asc') {
      return;
    }
    
    fetchDocuments(false, pagination.page, searchTerm, sortField, sortDirection);
  }, [pagination.page, searchTerm, sortField, sortDirection]);

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
    let newDirection: 'asc' | 'desc' = 'asc';
    if (sortField === field) {
      newDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    }
    
    setSortField(field);
    setSortDirection(newDirection);
    setPagination(prev => ({ ...prev, page: 1 })); // Reset to first page when sorting
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
      
      // Force refresh to get updated data with cache bypass
      console.log('🔄 Forcing cache refresh after successful save...');
      await fetchDocuments(true, pagination.page, searchTerm, sortField, sortDirection);
      
      // Find and update the selected document to reflect changes
      setTimeout(() => {
        setAllDocuments(prev => {
          const updatedDoc = prev.find(d => d.filename === selectedDoc.filename);
          if (updatedDoc) {
            console.log('📝 Updated selected document with fresh data');
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
    if (!selectedDoc || !selectedDoc.id) return;
    
    setDeleteLoading(true);
    setDeleteError(null);
    setDeleteSummary(null);
    
    try {
      const response = await apiClient.delete(`${API_URL}/admin/documents/${selectedDoc.id}`);
      const summary = response.data;
      
      setDeleteSummary({
        chunks_deleted: summary.chunks_deleted,
        author_associations_deleted: summary.author_associations_deleted,
        metadata_history_deleted: summary.metadata_history_deleted,
      });
      
      // Refresh the document list after successful deletion
      await fetchDocuments(true, pagination.page, searchTerm, sortField, sortDirection);
      setSelectedDoc(null);
    } catch (err: unknown) {
      const errorMessage = (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail
        || (err as { message?: string })?.message
        || 'Error deleting document';
      setDeleteError(errorMessage);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;

    setBulkDeleteLoading(true);
    setBulkDeleteError(null);
    setBulkDeleteSummary(null);

    try {
      const response = await apiClient.delete(`${API_URL}/admin/documents/bulk`, {
        data: { ids: [...selectedIds] },
      });
      setBulkDeleteSummary(response.data);

      // Clear selections, close detail panel, refresh list
      setSelectedIds(new Set());
      setSelectedDoc(null);
      await fetchDocuments(true, pagination.page, searchTerm, sortField, sortDirection);
    } catch (err: unknown) {
      const errorMessage =
        (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data
          ?.detail ||
        (err as { message?: string })?.message ||
        'Error deleting documents';
      setBulkDeleteError(errorMessage);
    } finally {
      setBulkDeleteLoading(false);
    }
  };

  // Cleanup reindex polling on unmount
  useEffect(() => {
    return () => {
      if (reindexPollRef.current) {
        clearInterval(reindexPollRef.current);
        reindexPollRef.current = null;
      }
    };
  }, []);

  const handleReindex = async () => {
    setReindexLoading(true);
    setReindexStatus(null);
    setShowReindexDialog(false);

    const startTime = Date.now();

    try {
      await apiClient.post(`${API_URL}/admin/documents/reindex`);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        // Already in progress — start polling anyway
      } else {
        const errorMessage =
          (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail ||
          (err as { message?: string })?.message ||
          'Failed to start vector index rebuild';
        setReindexStatus(`Error: ${errorMessage}`);
        setReindexLoading(false);
        return;
      }
    }

    // Poll status every 3 seconds
    reindexPollRef.current = setInterval(async () => {
      try {
        const statusRes = await apiClient.get(`${API_URL}/admin/documents/reindex/status`);
        const data = statusRes.data;

        if (!data.in_progress) {
          // Rebuild finished
          if (reindexPollRef.current) {
            clearInterval(reindexPollRef.current);
            reindexPollRef.current = null;
          }
          setReindexLoading(false);

          if (data.last_duration_seconds != null) {
            setReindexStatus(`Rebuild completed in ${data.last_duration_seconds.toFixed(1)}s`);
          } else {
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            setReindexStatus(`Rebuild completed in ~${elapsed}s`);
          }
        }
      } catch {
        if (reindexPollRef.current) {
          clearInterval(reindexPollRef.current);
          reindexPollRef.current = null;
        }
        setReindexLoading(false);
        setReindexStatus('Error: Failed to check rebuild status');
      }
    }, 3000);
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

        {/* Search and Refresh */}
        <div className="flex-shrink-0 mb-4 flex gap-3">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
            placeholder="Search by title, author, or filename..."
          />
          <button
            onClick={() => setShowReindexDialog(true)}
            disabled={reindexLoading}
            className={`px-4 py-2 text-sm font-medium rounded-md border whitespace-nowrap ${
              reindexLoading
                ? 'bg-gray-100 text-gray-400 border-gray-300 cursor-not-allowed'
                : 'bg-blue-50 text-blue-700 border-blue-300 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }`}
            title="Rebuild the vector search index"
          >
            {reindexLoading ? (
              <span className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
                Rebuilding...
              </span>
            ) : (
              'Rebuild Vector Index'
            )}
          </button>
          <button
            onClick={() => {
              console.log('🔄 Manual refresh requested');
              fetchDocuments(true, pagination.page, searchTerm, sortField, sortDirection);
            }}
            disabled={loading}
            className={`px-4 py-2 text-sm font-medium rounded-md border ${
              loading
                ? 'bg-gray-100 text-gray-400 border-gray-300 cursor-not-allowed'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }`}
            title="Refresh document list"
          >
            {loading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
          </button>
        </div>

        {/* Reindex Status Message */}
        {reindexStatus && (
          <div className={`flex-shrink-0 mb-3 p-3 rounded text-sm ${
            reindexStatus.startsWith('Error')
              ? 'bg-red-50 border border-red-200 text-red-700'
              : 'bg-green-50 border border-green-200 text-green-700'
          }`}>
            {reindexStatus}
            <button
              onClick={() => setReindexStatus(null)}
              className="ml-2 text-xs underline hover:no-underline"
            >
              dismiss
            </button>
          </div>
        )}

        {/* Bulk Delete Button */}
        {selectedIds.size > 0 && (
          <div className="flex-shrink-0 mb-3">
            <button
              onClick={() => setShowBulkDeleteDialog(true)}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              Delete {selectedIds.size} selected
            </button>
          </div>
        )}

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
                      <th className="w-10 px-2 py-3">
                        <input
                          ref={selectAllCheckboxRef}
                          type="checkbox"
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          checked={documents.filter(doc => doc.id !== undefined).length > 0 && documents.filter(doc => doc.id !== undefined).every(doc => selectedIds.has(doc.id!))}
                          onChange={(e) => {
                            if (e.target.checked) {
                              const newSelected = new Set(selectedIds);
                              documents.forEach(doc => { if (doc.id !== undefined) newSelected.add(doc.id); });
                              setSelectedIds(newSelected);
                            } else {
                              const newSelected = new Set(selectedIds);
                              documents.forEach(doc => { if (doc.id !== undefined) newSelected.delete(doc.id); });
                              setSelectedIds(newSelected);
                            }
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </th>
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
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Chunks
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
                        <td className="w-10 px-2 py-2">
                          <input
                            type="checkbox"
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            checked={doc.id !== undefined && selectedIds.has(doc.id)}
                            onChange={(e) => {
                              if (doc.id === undefined) return;
                              const newSelected = new Set(selectedIds);
                              if (e.target.checked) {
                                newSelected.add(doc.id);
                              } else {
                                newSelected.delete(doc.id);
                              }
                              setSelectedIds(newSelected);
                            }}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
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
                        <td className="px-4 py-2 text-sm text-gray-700">
                          {doc.chunk_count !== undefined ? doc.chunk_count : 'N/A'}
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
                  onClick={() => {
                    const newPage = Math.max(1, pagination.page - 1);
                    setPagination(prev => ({ ...prev, page: newPage }));
                    setSelectedIds(new Set()); // Clear selections on page change
                  }}
                  disabled={pagination.page <= 1}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Prev
                </button>
                <span className="px-3 py-1 text-sm">
                  {pagination.page} / {pagination.totalPages || 1}
                </span>
                <button
                  onClick={() => {
                    const newPage = Math.min(pagination.totalPages, pagination.page + 1);
                    setPagination(prev => ({ ...prev, page: newPage }));
                    setSelectedIds(new Set()); // Clear selections on page change
                  }}
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

            {/* Document details */}
            <div className="mt-3 mb-4 p-3 bg-gray-50 rounded border border-gray-200">
              <p className="text-sm font-medium text-gray-900 mb-2">{selectedDoc?.title || selectedDoc?.filename}</p>
              <div className="flex items-center gap-3">
                <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                  selectedDoc?.document_type === 'article'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {selectedDoc?.document_type || 'book'}
                </span>
                <span className="text-xs text-gray-600">
                  {selectedDoc?.chunk_count !== undefined ? `${selectedDoc.chunk_count} chunks` : 'N/A chunks'}
                </span>
              </div>
            </div>

            <p className="text-sm text-gray-500">
              Are you sure you want to delete this document and all its associated data? This action cannot be undone.
            </p>

            {/* Error message */}
            {deleteError && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                {deleteError}
              </div>
            )}

            {/* Success summary */}
            {deleteSummary && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                <p className="font-medium mb-1">Document deleted successfully</p>
                <ul className="text-xs space-y-0.5">
                  <li>Chunks deleted: {deleteSummary.chunks_deleted}</li>
                  <li>Author associations removed: {deleteSummary.author_associations_deleted}</li>
                  <li>Metadata history entries removed: {deleteSummary.metadata_history_deleted}</li>
                </ul>
              </div>
            )}

            <div className="mt-4 flex space-x-3 justify-end">
              {deleteSummary ? (
                <button
                  onClick={() => {
                    setShowDeleteDialog(false);
                    setDeleteSummary(null);
                    setDeleteError(null);
                  }}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
                >
                  Close
                </button>
              ) : (
                <>
                  <button
                    onClick={() => {
                      setShowDeleteDialog(false);
                      setDeleteError(null);
                    }}
                    disabled={deleteLoading}
                    className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDelete}
                    disabled={deleteLoading}
                    className={`px-4 py-2 text-sm font-medium text-white rounded ${
                      deleteLoading
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-red-600 hover:bg-red-700'
                    }`}
                  >
                    {deleteLoading ? 'Deleting...' : 'Delete'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Bulk Delete Confirmation Dialog */}
      {showBulkDeleteDialog && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-lg w-full mx-6 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Confirm Bulk Delete</h3>

            {!bulkDeleteSummary && (
              <>
                {/* Selected documents list */}
                <div className="mt-3 mb-4 p-3 bg-gray-50 rounded border border-gray-200">
                  <p className="text-xs font-medium text-gray-500 uppercase mb-2">
                    {selectedIds.size} document{selectedIds.size !== 1 ? 's' : ''} selected
                  </p>
                  <div className="max-h-40 overflow-y-auto space-y-1">
                    {documents
                      .filter((doc) => doc.id !== undefined && selectedIds.has(doc.id))
                      .map((doc) => (
                        <div key={doc.id} className="text-sm text-gray-900 truncate">
                          {doc.title || doc.filename}
                        </div>
                      ))}
                  </div>
                  <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-600">
                    Total chunks:{' '}
                    {documents
                      .filter((doc) => doc.id !== undefined && selectedIds.has(doc.id))
                      .reduce((sum, doc) => sum + (doc.chunk_count || 0), 0)}
                  </div>
                </div>

                <p className="text-sm text-red-600 font-medium">
                  This action cannot be undone. All selected documents and their associated data will be permanently deleted.
                </p>
              </>
            )}

            {/* Error message */}
            {bulkDeleteError && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                {bulkDeleteError}
              </div>
            )}

            {/* Success summary */}
            {bulkDeleteSummary && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                <p className="font-medium mb-1">Bulk delete completed</p>
                <ul className="text-xs space-y-0.5">
                  <li>Documents deleted: {bulkDeleteSummary.deleted_count}</li>
                  <li>Total chunks deleted: {bulkDeleteSummary.total_chunks_deleted}</li>
                  <li>Author associations removed: {bulkDeleteSummary.total_author_associations_deleted}</li>
                  <li>Metadata history entries removed: {bulkDeleteSummary.total_metadata_history_deleted}</li>
                  {bulkDeleteSummary.not_found_ids && bulkDeleteSummary.not_found_ids.length > 0 && (
                    <li className="text-yellow-700">
                      Not found IDs: {bulkDeleteSummary.not_found_ids.join(', ')}
                    </li>
                  )}
                </ul>
              </div>
            )}

            <div className="mt-4 flex space-x-3 justify-end">
              {bulkDeleteSummary ? (
                <button
                  onClick={() => {
                    setShowBulkDeleteDialog(false);
                    setBulkDeleteSummary(null);
                    setBulkDeleteError(null);
                  }}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
                >
                  Close
                </button>
              ) : (
                <>
                  <button
                    onClick={() => {
                      setShowBulkDeleteDialog(false);
                      setBulkDeleteError(null);
                    }}
                    disabled={bulkDeleteLoading}
                    className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleBulkDelete}
                    disabled={bulkDeleteLoading}
                    className={`px-4 py-2 text-sm font-medium text-white rounded ${
                      bulkDeleteLoading
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-red-600 hover:bg-red-700'
                    }`}
                  >
                    {bulkDeleteLoading ? 'Deleting...' : `Delete ${selectedIds.size} document${selectedIds.size !== 1 ? 's' : ''}`}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
      {/* Reindex Confirmation Dialog */}
      {showReindexDialog && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-md w-full mx-6 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Rebuild Vector Index</h3>
            <p className="text-sm text-gray-600 mb-4">
              This will rebuild the vector search index. The operation may take a few minutes but search will remain available during the rebuild.
            </p>
            <div className="flex space-x-3 justify-end">
              <button
                onClick={() => setShowReindexDialog(false)}
                className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleReindex}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
              >
                Rebuild Index
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminLayout>
  );
}