'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import MetadataEditDialog from './MetadataEditDialog'
import BookLink from './BookLink'
import { API_URL } from '../config/api'

interface Document {
  filename: string
  total_chunks: number
  has_images: boolean
  has_code: boolean
  total_pages: number
  category?: string
  author?: string
  mc_press_url?: string
  images_processed?: number
  code_blocks_found?: number
  upload_date?: string
  file_size?: number
}

interface DocumentCardProps {
  document: Document
  onDelete: (filename: string) => void
  onEdit: (filename: string, title: string, author: string) => void
  onSelect?: (filename: string) => void
  isSelected?: boolean
  isCompact?: boolean
}

interface CategoryHeaderProps {
  category: string
  count: number
  isExpanded: boolean
  onToggle: () => void
}

function CategoryHeader({ category, count, isExpanded, onToggle }: CategoryHeaderProps) {
  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'RPG':
        return (
          <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
        )
      case 'Database':
        return (
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
          </div>
        )
      case 'Application Development':
        return (
          <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
          </div>
        )
      case 'System Administration':
        return (
          <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
        )
      case 'Management and Career':
        return (
          <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        )
      case 'Operating Systems':
        return (
          <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
        )
      default:
        return (
          <div className="w-8 h-8 bg-gray-500 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
        )
    }
  }

  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between p-3 hover:bg-gray-50 rounded-xl transition-all group"
    >
      <div className="flex items-center gap-3">
        {getCategoryIcon(category)}
        <div className="text-left">
          <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">
            {category}
          </h3>
          <p className="text-sm text-gray-500">{count} {count === 1 ? 'book' : 'books'}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full font-medium">
          {count}
        </span>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${
            isExpanded ? 'rotate-90' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </button>
  )
}

function DocumentCard({ document, onDelete, onEdit, onSelect, isSelected = false, isCompact = false }: DocumentCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const getFileIcon = () => {
    return (
      <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
        <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
    )
  }

  const getCategoryIcon = (category?: string) => {
    switch (category) {
      case 'RPG':
        return '🔧'
      case 'Database':
        return '🗄️'
      case 'Application Development':
        return '🔨'
      case 'System Administration':
        return '🔒'
      case 'Management and Career':
        return '📊'
      case 'Operating Systems':
        return '💻'
      case 'Programming':
      default:
        return '⚙️'
    }
  }

  const getCategoryColor = (category?: string) => {
    switch (category) {
      case 'RPG':
        return 'bg-orange-100 text-orange-700'
      case 'Database':
        return 'bg-blue-100 text-blue-700'
      case 'Application Development':
        return 'bg-green-100 text-green-700'
      case 'System Administration':
        return 'bg-red-100 text-red-700'
      case 'Management and Career':
        return 'bg-purple-100 text-purple-700'
      case 'Operating Systems':
        return 'bg-indigo-100 text-indigo-700'
      case 'Programming':
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const getContentTypeIndicators = () => {
    const indicators = []
    
    // Add category indicator first
    if (document.category) {
      indicators.push(
        <span key="category" className={`px-2 py-1 rounded text-xs font-medium ${getCategoryColor(document.category)}`}>
          {getCategoryIcon(document.category)} {document.category}
        </span>
      )
    }
    
    if (document.has_images) {
      indicators.push(
        <span key="images" className="content-type-image px-2 py-1 rounded text-xs font-medium">
          🖼️ {document.images_processed || 'Images'}
        </span>
      )
    }
    
    if (document.has_code) {
      indicators.push(
        <span key="code" className="content-type-code px-2 py-1 rounded text-xs font-medium">
          💻 {document.code_blocks_found || 'Code'}
        </span>
      )
    }
    
    indicators.push(
      <span key="text" className="content-type-text px-2 py-1 rounded text-xs font-medium">
        📝 Text
      </span>
    )
    
    return indicators
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return ''
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return ''
    return new Date(dateString).toLocaleDateString()
  }

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${document.filename}"?`)) return
    
    setIsDeleting(true)
    try {
      await onDelete(document.filename)
    } finally {
      setIsDeleting(false)
    }
  }

  const getFileName = () => {
    const name = document.filename.replace(/\.[^/.]+$/, '')
    return name.length > 25 ? name.substring(0, 25) + '...' : name
  }

  if (isCompact) {
    return (
      <div 
        className={`pl-4 border-l-2 transition-all cursor-pointer ${
          isSelected 
            ? 'border-indigo-500 bg-indigo-50' 
            : 'border-gray-200 hover:border-indigo-300 hover:bg-gray-50'
        }`}
        onClick={() => onSelect?.(document.filename)}
      >
        <div className="py-3 px-3 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <div className="w-6 h-6 bg-red-100 rounded-md flex items-center justify-center flex-shrink-0">
                <svg className="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <span className={`text-sm font-medium truncate ${
                isSelected ? 'text-indigo-700' : 'text-gray-700'
              }`}>
                {getFileName()}
              </span>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0 ml-2">
              <span className="text-xs text-gray-500">{document.total_pages}p</span>
              {isSelected && (
                <svg className="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              )}
            </div>
          </div>
          {isSelected && (
            <div className="mt-3 pt-3 border-t border-indigo-200 space-y-2 text-xs text-gray-600">
              {document.author && (
                <div className="mb-1 flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span className="font-medium">By:</span> {document.author}
                </div>
              )}
              <BookLink 
                url={document.mc_press_url} 
                title={document.filename.replace('.pdf', '')}
                className="text-xs mb-2"
              />
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {document.total_pages} pages
                </span>
                <span className="flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  {document.total_chunks} chunks
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
                {document.has_images && (
                  <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs">🖼️ Images</span>
                )}
                {document.has_code && (
                  <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded text-xs">💻 Code</span>
                )}
                <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs">📝 Text</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onEdit(document.filename, document.filename.replace('.pdf', ''), document.author || '')
                  }}
                  className="text-blue-600 hover:text-blue-800 text-xs underline"
                >
                  Edit
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete()
                  }}
                  disabled={isDeleting}
                  className="text-red-600 hover:text-red-800 text-xs underline"
                >
                  {isDeleting ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="card card-hover group">
      <div className="flex items-start gap-3">
        {getFileIcon()}
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h3 
              className="font-semibold text-sm text-gray-900 truncate cursor-pointer hover:text-blue-600 transition-colors"
              onClick={() => onSelect?.(document.filename)}
              title={document.filename}
            >
              {getFileName()}
            </h3>
            
            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                title={isExpanded ? 'Collapse' : 'Expand'}
              >
                <svg className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onEdit(document.filename, document.filename.replace('.pdf', ''), document.author || '')
                }}
                className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
                title="Edit metadata"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="p-1 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                title="Delete document"
              >
                {isDeleting ? (
                  <div className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Quick stats */}
          <div className="flex items-center gap-4 text-xs text-gray-600 mb-2">
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {document.total_pages} pages
            </span>
            <span className="flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              {document.total_chunks} chunks
            </span>
          </div>

          {/* Content type indicators */}
          <div className="flex flex-wrap gap-1 mb-2">
            {getContentTypeIndicators()}
          </div>

          {/* Author and MC Press Link */}
          <div className="flex items-center gap-4 mb-2">
            {document.author && (
              <span className="text-xs text-gray-600">
                <span className="font-medium">Author:</span> {document.author}
              </span>
            )}
            <BookLink 
              url={document.mc_press_url} 
              title={document.filename.replace('.pdf', '')}
              className="text-xs"
            />
          </div>

          {/* Expanded details */}
          {isExpanded && (
            <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                <div>
                  <span className="font-medium">File name:</span>
                  <p className="break-all">{document.filename}</p>
                </div>
                {document.file_size && (
                  <div>
                    <span className="font-medium">File size:</span>
                    <p>{formatFileSize(document.file_size)}</p>
                  </div>
                )}
                {document.upload_date && (
                  <div>
                    <span className="font-medium">Uploaded:</span>
                    <p>{formatDate(document.upload_date)}</p>
                  </div>
                )}
                <div>
                  <span className="font-medium">Processing:</span>
                  <p>✅ Complete</p>
                </div>
              </div>
              
              {(document.has_images || document.has_code) && (
                <div className="bg-gray-50 p-2 rounded text-xs">
                  <p className="font-medium text-gray-700 mb-1">Content Analysis:</p>
                  {document.has_images && (
                    <p className="text-gray-600">
                      🖼️ {document.images_processed || 'Multiple'} images processed with OCR
                    </p>
                  )}
                  {document.has_code && (
                    <p className="text-gray-600">
                      💻 {document.code_blocks_found || 'Multiple'} code blocks detected
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface DocumentListProps {
  onDocumentChange?: (count: number) => void
}

export default function DocumentList({ onDocumentChange }: DocumentListProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null)
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [editingDocument, setEditingDocument] = useState<{filename: string, title: string, author: string} | null>(null)

  useEffect(() => {
    fetchDocuments()
  }, [])

  const fetchDocuments = async () => {
    try {
      setError(null)
      const response = await axios.get(`${API_URL}/documents`)
      const documents = response.data.documents || []
      setDocuments(documents)
      onDocumentChange?.(documents.length)
    } catch (error) {
      console.error('Error fetching documents:', error)
      setError('Failed to load documents')
      onDocumentChange?.(0)
    } finally {
      setLoading(false)
    }
  }

  const deleteDocument = async (filename: string) => {
    try {
      await axios.delete(`${API_URL}/documents/${filename}`)
      await fetchDocuments()
    } catch (error) {
      console.error('Error deleting document:', error)
      setError('Failed to delete document')
    }
  }

  const handleDocumentSelect = (filename: string) => {
    setSelectedDocument(selectedDocument === filename ? null : filename)
    console.log('Selected document:', filename)
  }

  const handleEdit = (filename: string, title: string, author: string) => {
    setEditingDocument({ filename, title, author })
    setShowEditDialog(true)
  }

  const handleEditSuccess = async () => {
    await fetchDocuments()
  }

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories)
    if (newExpanded.has(category)) {
      newExpanded.delete(category)
    } else {
      newExpanded.add(category)
    }
    setExpandedCategories(newExpanded)
  }

  const groupDocumentsByCategory = (docs: Document[]) => {
    const grouped = docs.reduce((acc, doc) => {
      const category = doc.category || 'Uncategorized'
      if (!acc[category]) {
        acc[category] = []
      }
      acc[category].push(doc)
      return acc
    }, {} as Record<string, Document[]>)

    // Sort categories alphabetically, but put 'Programming' first if it exists
    const sortedCategories = Object.keys(grouped).sort((a, b) => {
      if (a === 'Programming') return -1
      if (b === 'Programming') return 1
      return a.localeCompare(b)
    })

    return sortedCategories.map(category => ({
      category,
      documents: grouped[category].sort((a, b) => a.filename.localeCompare(b.filename)),
      count: grouped[category].length
    }))
  }

  const handleResetDatabase = async () => {
    if (!confirm('Are you sure you want to delete ALL documents? This action cannot be undone.')) {
      return
    }
    
    try {
      const response = await axios.post(`${API_URL}/reset`)
      if (response.data.status === 'success') {
        await fetchDocuments()
        alert('Database reset successfully!')
      }
    } catch (error) {
      console.error('Error resetting database:', error)
      setError('Failed to reset database')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex items-center gap-2 text-gray-500">
          <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
          <span className="text-sm">Loading documents...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-2 text-red-700">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium">{error}</span>
        </div>
        <button
          onClick={fetchDocuments}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Try again
        </button>
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 mx-auto mb-3 bg-gray-100 rounded-full flex items-center justify-center">
          <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-gray-500 text-sm">No documents uploaded yet</p>
        <p className="text-gray-400 text-xs mt-1">Upload a PDF to get started</p>
      </div>
    )
  }

  const categorizedDocuments = groupDocumentsByCategory(documents)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">
            MC Press Library
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            {documents.length} books across {categorizedDocuments.length} categories
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={fetchDocuments}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            title="Refresh documents"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          {documents.length > 0 && (
            <button
              onClick={handleResetDatabase}
              className="p-1 text-gray-400 hover:text-red-600 transition-colors"
              title="Reset database (delete all documents)"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>
      
      <div className="space-y-2 overflow-y-auto scrollbar-thin max-h-96">
        {categorizedDocuments.map(({ category, documents: categoryDocs, count }) => (
          <div key={category} className="border border-gray-200 rounded-xl overflow-hidden">
            <CategoryHeader
              category={category}
              count={count}
              isExpanded={expandedCategories.has(category)}
              onToggle={() => toggleCategory(category)}
            />
            {expandedCategories.has(category) && (
              <div className="border-t border-gray-100 bg-gray-50/50">
                <div className="space-y-1 p-2">
                  {categoryDocs.map((doc) => (
                    <DocumentCard
                      key={doc.filename}
                      document={doc}
                      onDelete={deleteDocument}
                      onEdit={handleEdit}
                      onSelect={handleDocumentSelect}
                      isSelected={selectedDocument === doc.filename}
                      isCompact={true}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Metadata Edit Dialog */}
      {editingDocument && (
        <MetadataEditDialog
          isOpen={showEditDialog}
          onClose={() => {
            setShowEditDialog(false)
            setEditingDocument(null)
          }}
          onSuccess={handleEditSuccess}
          filename={editingDocument.filename}
          currentTitle={editingDocument.title}
          currentAuthor={editingDocument.author}
          currentUrl={editingDocument.mc_press_url}
        />
      )}
    </div>
  )
}