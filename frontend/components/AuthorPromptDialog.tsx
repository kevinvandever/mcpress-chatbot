'use client'

import { useState, useEffect } from 'react'

interface AuthorPromptDialogProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (author: string) => void
  filename: string
}

export default function AuthorPromptDialog({ 
  isOpen, 
  onClose, 
  onSubmit, 
  filename 
}: AuthorPromptDialogProps) {
  const [author, setAuthor] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setAuthor('')
    }
  }, [isOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!author.trim()) return

    setIsSubmitting(true)
    await onSubmit(author.trim())
    setIsSubmitting(false)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
        <div className="flex items-center gap-3 mb-4">
          <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900">Author Information Required</h3>
        </div>
        
        <p className="text-sm text-gray-600 mb-4">
          The PDF <span className="font-medium">"{filename}"</span> doesn't contain author metadata. 
          Please provide the author information to complete the upload.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="author" className="block text-sm font-medium text-gray-700 mb-1">
              Author(s)
            </label>
            <input
              type="text"
              id="author"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="e.g., John Doe or John Doe, Jane Smith"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              autoFocus
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">
              For multiple authors, separate with commas
            </p>
          </div>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!author.trim() || isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Completing...
                </>
              ) : (
                'Complete Upload'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}