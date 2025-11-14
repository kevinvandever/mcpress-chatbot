/**
 * Export Modal Component for Story-012
 * Allows users to export conversations to PDF or Markdown
 */

import React, { useState } from 'react'
import {
  exportConversation,
  downloadBlob,
  type ExportOptions,
} from '@/services/exportService'

interface ExportModalProps {
  conversationId: string
  conversationTitle: string
  onClose: () => void
}

export default function ExportModal({
  conversationId,
  conversationTitle,
  onClose,
}: ExportModalProps) {
  const [format, setFormat] = useState<'pdf' | 'markdown'>('pdf')
  const [includeTimestamps, setIncludeTimestamps] = useState(true)
  const [includeToc, setIncludeToc] = useState(false)
  const [customTitle, setCustomTitle] = useState('')
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleExport = async () => {
    setIsExporting(true)
    setError(null)

    try {
      const options: ExportOptions = {
        include_timestamps: includeTimestamps,
        include_toc: includeToc,
        ...(customTitle && { custom_title: customTitle }),
      }

      const blob = await exportConversation(conversationId, format, options)

      // Generate filename
      const titleSlug = (customTitle || conversationTitle)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
        .substring(0, 50)
      // PDF exports are HTML files due to WeasyPrint unavailability
      const extension = format === 'pdf' ? 'html' : 'md'
      const filename = `${titleSlug}.${extension}`

      downloadBlob(blob, filename)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg p-6 max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Export Conversation</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isExporting}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Export Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setFormat('pdf')}
                className={`p-4 border-2 rounded-lg text-center transition-colors ${
                  format === 'pdf'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                disabled={isExporting}
              >
                <svg
                  className="w-8 h-8 mx-auto mb-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                  />
                </svg>
                <div className="font-medium">PDF</div>
                <div className="text-xs text-gray-500">Styled HTML document</div>
              </button>

              <button
                onClick={() => setFormat('markdown')}
                className={`p-4 border-2 rounded-lg text-center transition-colors ${
                  format === 'markdown'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                disabled={isExporting}
              >
                <svg
                  className="w-8 h-8 mx-auto mb-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <div className="font-medium">Markdown</div>
                <div className="text-xs text-gray-500">Plain text format</div>
              </button>
            </div>
          </div>

          {/* Custom Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Custom Title (Optional)
            </label>
            <input
              type="text"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              placeholder={conversationTitle}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isExporting}
            />
          </div>

          {/* Options */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Options</label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeTimestamps}
                onChange={(e) => setIncludeTimestamps(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                disabled={isExporting}
              />
              <span className="text-sm text-gray-700">Include message timestamps</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeToc}
                onChange={(e) => setIncludeToc(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                disabled={isExporting}
              />
              <span className="text-sm text-gray-700">
                Include table of contents (PDF only)
              </span>
            </label>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Export Info */}
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-600">
              Exports include all messages with syntax highlighting for code blocks and book
              references.
              {format === 'pdf' && (
                <span className="block mt-1">
                  <strong>Note:</strong> PDF exports are currently provided as styled HTML files that can be opened in any browser and printed to PDF.
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            disabled={isExporting}
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isExporting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Exporting...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                Export {format.toUpperCase()}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
