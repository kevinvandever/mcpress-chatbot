'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'
import { API_URL } from '../config/api'

interface MetadataEditDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  filename: string
  currentTitle: string
  currentAuthor: string
  currentUrl?: string
}

export default function MetadataEditDialog({
  isOpen,
  onClose,
  onSuccess,
  filename,
  currentTitle,
  currentAuthor,
  currentUrl
}: MetadataEditDialogProps) {
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [mcPressUrl, setMcPressUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (isOpen) {
      setTitle(currentTitle)
      setAuthor(currentAuthor)
      setMcPressUrl(currentUrl || '')
      setError('')
    }
  }, [isOpen, currentTitle, currentAuthor, currentUrl])

  const validateUrl = (url: string): boolean => {
    if (!url.trim()) return true // Empty URL is valid (optional field)
    
    try {
      const urlObj = new URL(url)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      return false
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!title.trim() || !author.trim()) {
      setError('Both title and author are required')
      return
    }

    if (mcPressUrl.trim() && !validateUrl(mcPressUrl.trim())) {
      setError('Please enter a valid URL (must start with http:// or https://)')
      return
    }

    setIsSubmitting(true)
    setError('')

    try {
      await axios.put(`${API_URL}/documents/${encodeURIComponent(filename)}/metadata`, {
        filename: filename,
        title: title.trim(),
        author: author.trim(),
        mc_press_url: mcPressUrl.trim() || null
      })

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
        <form onSubmit={handleSubmit} className="p-6">
          {/* Filename display */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              File
            </label>
            <div className="p-2 bg-gray-50 rounded border text-sm text-gray-600 truncate">
              {filename}
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

          {/* Author input */}
          <div className="mb-4">
            <label htmlFor="author" className="block text-sm font-medium text-gray-700 mb-1">
              Author(s) *
            </label>
            <input
              type="text"
              id="author"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              placeholder="Enter author name(s), separate multiple with commas"
            />
          </div>

          {/* MC Press URL input */}
          <div className="mb-6">
            <label htmlFor="mcPressUrl" className="block text-sm font-medium text-gray-700 mb-1">
              MC Press URL
            </label>
            <input
              type="url"
              id="mcPressUrl"
              value={mcPressUrl}
              onChange={(e) => setMcPressUrl(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              placeholder="https://www.mc-press.com/product/book-name"
            />
            <p className="mt-1 text-xs text-gray-500">
              Optional: Link to this book on the MC Press website
            </p>
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
              disabled={isSubmitting || !title.trim() || !author.trim()}
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