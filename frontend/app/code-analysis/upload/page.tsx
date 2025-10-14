'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { API_URL } from '../../../config/api'
import CodeUploadZone, { CodeFile } from '../../../components/CodeUploadZone'
import CodeFileList from '../../../components/CodeFileList'
import CodeFilePreview from '../../../components/CodeFilePreview'
import UploadQuotaIndicator from '../../../components/UploadQuotaIndicator'
import { Alert, Button } from '../../../components/design-system'

interface UploadSession {
  session_id: string
  expires_at: string
}

/**
 * Code Analysis Upload Page
 *
 * Allows users to upload IBM i code files for analysis
 * Features:
 * - Drag-and-drop file upload
 * - File management (preview, delete)
 * - Quota tracking
 * - 24-hour auto-deletion
 */
export default function CodeAnalysisUploadPage() {
  const router = useRouter()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [files, setFiles] = useState<CodeFile[]>([])
  const [previewFile, setPreviewFile] = useState<CodeFile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create upload session on mount
  useEffect(() => {
    createSession()
  }, [])

  // Fetch files after session is created
  useEffect(() => {
    if (sessionId) {
      fetchFiles()
    }
  }, [sessionId])

  const createSession = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await axios.post<UploadSession>(`${API_URL}/api/code/session`)
      setSessionId(response.data.session_id)
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to create upload session'
      setError(errorMsg)
      console.error('Session creation error:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchFiles = async () => {
    try {
      const response = await axios.get<CodeFile[]>(`${API_URL}/api/code/files`)
      setFiles(response.data)
    } catch (err: any) {
      console.error('File fetch error:', err)
      // Don't show error for file fetch - just log it
    }
  }

  const handleUploadSuccess = (newFiles: CodeFile[]) => {
    setFiles(prev => [...prev, ...newFiles])
  }

  const handleFileDeleted = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }

  const handleFilePreview = (file: CodeFile) => {
    setPreviewFile(file)
  }

  const handleAnalyze = () => {
    if (files.length === 0) {
      alert('Please upload at least one file before analyzing')
      return
    }
    // TODO: Story-007 will implement analysis
    alert('Code analysis feature coming in Story-007!')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Code Analysis</h1>
              <p className="mt-1 text-sm text-gray-600">
                Upload your IBM i code files for AI-powered analysis and optimization
              </p>
            </div>
            <Button variant="secondary" onClick={() => router.push('/')}>
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Chat
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-600">Initializing upload session...</p>
          </div>
        )}

        {error && (
          <Alert variant="danger">
            <div>
              <p className="font-semibold">Session Error</p>
              <p className="text-sm mt-1">{error}</p>
              <Button variant="secondary" size="sm" onClick={createSession} className="mt-3">
                Retry
              </Button>
            </div>
          </Alert>
        )}

        {!loading && !error && sessionId && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Upload & Files */}
            <div className="lg:col-span-2 space-y-6">
              {/* Upload Zone */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Code Files</h2>
                <CodeUploadZone
                  sessionId={sessionId}
                  onUploadSuccess={handleUploadSuccess}
                  onUploadError={(err) => console.error('Upload error:', err)}
                />
              </div>

              {/* File List */}
              <div>
                <CodeFileList
                  files={files}
                  onFileDeleted={handleFileDeleted}
                  onFilePreview={handleFilePreview}
                  onRefresh={fetchFiles}
                />
              </div>

              {/* Analyze Button */}
              {files.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-grow">
                      <h3 className="text-lg font-semibold text-blue-900">Ready to Analyze</h3>
                      <p className="text-sm text-blue-700 mt-1">
                        You have {files.length} file(s) ready for AI-powered code analysis
                      </p>
                    </div>
                    <Button variant="primary" onClick={handleAnalyze} className="ml-4">
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                      </svg>
                      Analyze Code
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column - Quota & Info */}
            <div className="space-y-6">
              {/* Quota Indicator */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Quota</h2>
                <UploadQuotaIndicator />
              </div>

              {/* Info Card */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">ℹ️ How it Works</h3>
                <ol className="space-y-3 text-sm text-gray-600">
                  <li className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-semibold">1</span>
                    <span>Upload your RPG, CL, or SQL files (up to 10MB each)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-semibold">2</span>
                    <span>Preview and manage your uploaded files</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-semibold">3</span>
                    <span>Click "Analyze Code" for AI-powered insights</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-semibold">4</span>
                    <span>Get modernization suggestions, security audits, and optimization tips</span>
                  </li>
                </ol>
              </div>

              {/* Security Notice */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  <div className="text-xs text-green-800">
                    <p className="font-semibold mb-1">Secure & Private</p>
                    <p>Your code is encrypted in transit and automatically deleted after 24 hours. We never store your code permanently.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* File Preview Modal */}
      <CodeFilePreview
        file={previewFile}
        isOpen={previewFile !== null}
        onClose={() => setPreviewFile(null)}
      />
    </div>
  )
}
