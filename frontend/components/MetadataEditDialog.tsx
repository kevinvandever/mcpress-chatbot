'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import MultiAuthorInput from './MultiAuthorInput'
import DocumentTypeSelector, { DocumentType } from './DocumentTypeSelector'
import { API_URL } from '../config/api'

interface Author {
  id?: number
  name: string
  site_url?: string
  order: number
}

interface Document {
  id?: number
  filename: string
  title?: string
  authors?: Author[]
  author?: string // Legacy field
  mc_press_url?: string
  article_url?: string
  document_type?: 'book' | 'article'
}

interface MetadataEditDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  document: Document
}

export default function MetadataEditDialog({
  isOpen,
  onClose,
  onSuccess,
  document
}: MetadataEditDialogProps) {
  const [title, setTitle] = useState('')
  const [authors, setAuthors] = useState<Author[]>([])
  const [documentType, setDocumentType] = useState<DocumentType>('book')
  const [mcPressUrl, setMcPressUrl] = useState('')
  const [articleUrl, setArticleUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isOpen && document) {
      setTitle(document.title || document.filename.replace('.pdf', ''))
      
      // Handle authors - convert from legacy format if needed
      if (document.authors && document.authors.length > 0) {
        setAuthors(document.authors)
      } else if (document.author) {
        // Convert legacy single author to new format
        setAuthors([{
          name: document.author,
          order: 0
        }])
      } else {
        // Default to at least one empty author
        setAuthors([{
          name: '',
          order: 0
        }])
      }
      
      setDocumentType(document.document_type || 'book')
      setMcPressUrl(document.mc_press_url || '')
      setArticleUrl(document.article_url || '')
      setError('')
    }
  }, [isOpen, document])

  const handleDocumentTypeChange = (data: {
    documentType: DocumentType
    mcPressUrl?: string
    articleUrl?: string
  }) => {
    setDocumentType(data.documentType)
    setMcPressUrl(data.mcPressUrl || '')
    setArticleUrl(data.articleUrl || '')
  }

  const handleSubmit = async (e: any) => {
    e.preventDefault()
    
    if (!title.trim()) {
      setError('Title is required')
      return
    }

    if (authors.length === 0 || !authors.some(author => author.name.trim())) {
      setError('At least one author is required')
      return
    }

    // Validate that all authors have names
    const invalidAuthors = authors.filter(author => !author.name.trim())
    if (invalidAuthors.length > 0) {
      setError('All authors must have names')
      return
    }

    setIsSubmitting(true)
    setError('')

    try {
      const documentId = document.id

      if (!documentId) {
        throw new Error('Document ID is required')
      }

      // Update basic document metadata using admin endpoint (for title, type, URLs)
      await axios.patch(`${API_URL}/api/admin/documents/${documentId}`, {
        title: title.trim(),
        document_type: documentType,
        mc_press_url: documentType === 'book' ? (mcPressUrl.trim() || null) : null,
        article_url: documentType === 'article' ? (articleUrl.trim() || null) : null
      })

      // Get current document authors to compare
      const currentDocResponse = await axios.get(`${API_URL}/api/documents/${documentId}`)
      const currentAuthors = currentDocResponse.data.authors || []

      // Filter out empty authors
      const validAuthors = authors.filter(author => author.name.trim())

      // Add new authors using document-author relationship endpoint
      const newAuthorIds: number[] = []
      for (let i = 0; i < validAuthors.length; i++) {
        const author = validAuthors[i]
        try {
          const response = await axios.post(`${API_URL}/api/documents/${documentId}/authors`, {
            author_name: author.name.trim(),
            author_site_url: author.site_url?.trim() || null,
            order: i
          })
          newAuthorIds.push(response.data.author_id)
        } catch (error: any) {
          // If author already exists, we'll handle reordering later
          if (error.response?.status === 409) {
            // Find existing author ID
            const existingAuthor = currentAuthors.find((ca: any) => ca.name === author.name.trim())
            if (existingAuthor) {
              newAuthorIds.push(existingAuthor.id)
            }
          } else {
            throw error
          }
        }
      }

      // Remove authors that are no longer in the list
      for (const currentAuthor of currentAuthors) {
        const stillExists = validAuthors.some(author => 
          author.name.trim() === currentAuthor.name
        )
        if (!stillExists) {
          try {
            await axios.delete(`${API_URL}/api/documents/${documentId}/authors/${currentAuthor.id}`)
          } catch (error: any) {
            // Ignore errors for removing authors (might be last author)
            console.warn('Could not remove author:', error.response?.data?.detail)
          }
        }
      }

      // Reorder authors using PUT /api/documents/{document_id}/authors/order
      if (newAuthorIds.length > 0) {
        await axios.put(`${API_URL}/api/documents/${documentId}/authors/order`, {
          author_ids: newAuthorIds
        })
      }

      onSuccess()
      onClose()
    } catch (error: any) {
      console.error('Error updating metadata:', error)
      setError(error.response?.data?.detail || 'Failed to update metadata')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-gray-800">Edit Document Metadata</h2>
          </div>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 max-h-[70vh] overflow-y-auto">
          {/* Filename display */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              File
            </label>
            <div className="p-2 bg-gray-50 rounded border text-sm text-gray-600 truncate">
              {document.filename}
            </div>
          </div>

          {/* Title input */}
          <div className="mb-4">
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
              Title *
            </label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              placeholder="Enter document title"
            />
          </div>

          {/* Document Type Selector */}
          <div className="mb-6">
            <DocumentTypeSelector
              documentType={documentType}
              mcPressUrl={mcPressUrl}
              articleUrl={articleUrl}
              onChange={handleDocumentTypeChange}
              disabled={isSubmitting}
            />
          </div>

          {/* Multi-Author Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Authors *
            </label>
            <MultiAuthorInput
              authors={authors}
              onChange={setAuthors}
              disabled={isSubmitting}
              placeholder="Search for authors or add new ones..."
            />
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !title.trim() || authors.length === 0 || !authors.some(author => author.name.trim())}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSubmitting && (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {isSubmitting ? 'Updating...' : 'Update Metadata'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}