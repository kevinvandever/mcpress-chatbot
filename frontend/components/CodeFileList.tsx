'use client'

import { useState } from 'react'
import axios from 'axios'
import { API_URL } from '../config/api'
import { Card, Button, Alert } from './design-system'
import FileTypeIndicator from './FileTypeIndicator'
import type { CodeFile } from './CodeUploadZone'

interface CodeFileListProps {
  files: CodeFile[]
  onFileDeleted: (fileId: string) => void
  onFilePreview: (file: CodeFile) => void
  onRefresh?: () => void
  className?: string
}

/**
 * CodeFileList Component
 *
 * Displays list of uploaded code files with actions
 * Shows file details, expiration time, and allows preview/delete
 *
 * @example
 * <CodeFileList
 *   files={uploadedFiles}
 *   onFileDeleted={(id) => removeFile(id)}
 *   onFilePreview={(file) => showPreview(file)}
 * />
 */
export default function CodeFileList({
  files,
  onFileDeleted,
  onFilePreview,
  onRefresh,
  className = ''
}: CodeFileListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const formatExpirationTime = (expiresAt: string): string => {
    const now = new Date()
    const expires = new Date(expiresAt)
    const diffMs = expires.getTime() - now.getTime()

    if (diffMs < 0) return 'Expired'

    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

    if (diffHours > 0) {
      return `${diffHours}h ${diffMinutes}m remaining`
    }
    return `${diffMinutes}m remaining`
  }

  const handleDelete = async (fileId: string) => {
    if (!confirm('Are you sure you want to delete this file?')) return

    setDeletingId(fileId)
    setError(null)

    try {
      await axios.delete(`${API_URL}/api/code/file/${fileId}`)
      onFileDeleted(fileId)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to delete file'
      setError(errorMsg)
      console.error('Delete error:', err)
    } finally {
      setDeletingId(null)
    }
  }

  if (files.length === 0) {
    return (
      <Card className={className}>
        <div className="text-center py-8 text-gray-500">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-sm font-medium">No files uploaded</p>
          <p className="text-xs mt-1">Upload code files to get started</p>
        </div>
      </Card>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {error && (
        <Alert variant="danger" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <div className="flex justify-between items-center">
        <h3 className="text-sm font-semibold text-gray-900">
          Uploaded Files ({files.length})
        </h3>
        {onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            className="text-xs"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </Button>
        )}
      </div>

      <div className="space-y-3">
        {files.map((file) => {
          const isDeleting = deletingId === file.id
          const expirationText = formatExpirationTime(file.expires_at)
          const isExpiringSoon = expirationText.includes('m remaining') && !expirationText.includes('h')

          return (
            <Card key={file.id} className="hover:shadow-md transition-shadow">
              <div className="flex items-start gap-4">
                {/* File Icon */}
                <div className="flex-shrink-0 mt-1">
                  <svg className="w-10 h-10 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>

                {/* File Details */}
                <div className="flex-grow min-w-0">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div className="flex-grow min-w-0">
                      <h4 className="text-sm font-medium text-gray-900 truncate">
                        {file.filename}
                      </h4>
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                        <span>{formatFileSize(file.file_size)}</span>
                        <span>•</span>
                        <span className={isExpiringSoon ? 'text-orange-600 font-medium' : ''}>
                          {expirationText}
                        </span>
                      </div>
                    </div>
                    <FileTypeIndicator fileName={file.filename} />
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 mt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onFilePreview(file)}
                      disabled={isDeleting}
                    >
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      Preview
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(file.id)}
                      disabled={isDeleting}
                      className="text-red-600 hover:bg-red-50 hover:border-red-300"
                    >
                      {isDeleting ? (
                        <>
                          <div className="w-4 h-4 mr-1 border-2 border-red-400 border-t-transparent rounded-full animate-spin"></div>
                          Deleting...
                        </>
                      ) : (
                        <>
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Delete
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Expiration Notice */}
      <Alert variant="info">
        <div className="text-xs">
          <p className="font-medium mb-1">🕒 Files expire after 24 hours</p>
          <p>All uploaded files are automatically deleted after 24 hours for security. Download any analysis results before expiration.</p>
        </div>
      </Alert>
    </div>
  )
}
