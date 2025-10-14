'use client'

import { useEffect, useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import axios from 'axios'
import { API_URL } from '../config/api'
import { Modal, Button, Alert, Spinner } from './design-system'
import FileTypeIndicator from './FileTypeIndicator'
import type { CodeFile } from './CodeUploadZone'

interface CodeFilePreviewProps {
  file: CodeFile | null
  isOpen: boolean
  onClose: () => void
}

/**
 * CodeFilePreview Component
 *
 * Displays code file content in a modal with syntax highlighting
 * Supports RPG, CL, SQL, and other IBM i file types
 *
 * @example
 * <CodeFilePreview
 *   file={selectedFile}
 *   isOpen={showPreview}
 *   onClose={() => setShowPreview(false)}
 * />
 */
export default function CodeFilePreview({ file, isOpen, onClose }: CodeFilePreviewProps) {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || !file) {
      setContent('')
      setError(null)
      return
    }

    const fetchContent = async () => {
      setLoading(true)
      setError(null)

      try {
        const response = await axios.get<{ content: string }>(`${API_URL}/api/code/file/${file.id}`)
        setContent(response.data.content || '')
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || 'Failed to load file content'
        setError(errorMsg)
        console.error('File fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchContent()
  }, [file, isOpen])

  const getLanguageFromExtension = (filename: string): string => {
    const extension = filename.toLowerCase().match(/\.(rpg|rpgle|sqlrpgle|cl|clle|sql|txt)$/)?.[1]

    // Map IBM i file extensions to closest syntax highlighter language
    const languageMap: Record<string, string> = {
      rpg: 'cobol',        // RPG is similar to COBOL
      rpgle: 'cobol',      // RPGLE is similar to COBOL
      sqlrpgle: 'sql',     // SQL RPG uses SQL syntax
      cl: 'bash',          // CL commands are similar to shell
      clle: 'bash',        // CLLE is similar to shell
      sql: 'sql',          // SQL is SQL
      txt: 'text',         // Plain text
    }

    return languageMap[extension || 'txt'] || 'text'
  }

  const handleDownload = () => {
    if (!file || !content) return

    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleCopy = async () => {
    if (!content) return

    try {
      await navigator.clipboard.writeText(content)
      alert('Code copied to clipboard!')
    } catch (err) {
      console.error('Copy failed:', err)
      alert('Failed to copy code')
    }
  }

  if (!file) return null

  const language = getLanguageFromExtension(file.filename)
  const lineCount = content.split('\n').length

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-3">
          <span className="truncate">{file.filename}</span>
          <FileTypeIndicator fileName={file.filename} />
        </div>
      }
      size="xl"
      footer={
        <div className="flex justify-between items-center w-full">
          <div className="text-xs text-gray-500">
            {lineCount.toLocaleString()} lines • {(file.file_size / 1024).toFixed(1)} KB
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCopy} disabled={loading || !!error}>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy
            </Button>
            <Button variant="outline" size="sm" onClick={handleDownload} disabled={loading || !!error}>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </Button>
            <Button variant="secondary" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      }
    >
      <div className="max-h-[70vh] overflow-auto">
        {loading && (
          <div className="flex flex-col items-center justify-center py-16">
            <Spinner size="lg" />
            <p className="mt-4 text-sm text-gray-600">Loading file content...</p>
          </div>
        )}

        {error && (
          <Alert variant="danger">
            <div>
              <p className="font-semibold">Failed to load file</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          </Alert>
        )}

        {!loading && !error && content && (
          <div className="rounded-lg overflow-hidden border border-gray-200">
            <SyntaxHighlighter
              language={language}
              style={vscDarkPlus}
              showLineNumbers
              lineNumberStyle={{ minWidth: '3em', paddingRight: '1em', color: '#6e7681' }}
              customStyle={{
                margin: 0,
                fontSize: '0.875rem',
                lineHeight: '1.5',
              }}
              wrapLines
              wrapLongLines
            >
              {content}
            </SyntaxHighlighter>
          </div>
        )}

        {!loading && !error && !content && (
          <Alert variant="warning">
            File appears to be empty
          </Alert>
        )}
      </div>
    </Modal>
  )
}
