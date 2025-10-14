'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { API_URL } from '../config/api'
import { Alert } from './design-system'
import FileTypeIndicator from './FileTypeIndicator'

export interface CodeFile {
  id: string
  filename: string
  file_type: string
  file_size: number
  uploaded_at: string
  expires_at: string
}

interface CodeUploadZoneProps {
  sessionId: string | null
  onUploadSuccess: (files: CodeFile[]) => void
  onUploadError?: (error: string) => void
  disabled?: boolean
  maxFiles?: number
}

interface UploadState {
  status: 'idle' | 'uploading' | 'success' | 'error'
  progress: number
  message: string
  uploadingFiles: string[]
}

const ALLOWED_EXTENSIONS = ['.rpg', '.rpgle', '.sqlrpgle', '.cl', '.clle', '.sql', '.txt']
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const MAX_FILES_PER_UPLOAD = 10

/**
 * CodeUploadZone Component
 *
 * Drag-and-drop zone for uploading IBM i code files
 * Supports multiple files, validation, and progress tracking
 *
 * @example
 * <CodeUploadZone
 *   sessionId={sessionId}
 *   onUploadSuccess={(files) => console.log('Uploaded:', files)}
 * />
 */
export default function CodeUploadZone({
  sessionId,
  onUploadSuccess,
  onUploadError,
  disabled = false,
  maxFiles = MAX_FILES_PER_UPLOAD
}: CodeUploadZoneProps) {
  const [uploadState, setUploadState] = useState<UploadState>({
    status: 'idle',
    progress: 0,
    message: '',
    uploadingFiles: []
  })

  const validateFile = (file: File): string | null => {
    // Check extension
    const extension = file.name.toLowerCase().match(/\.(rpg|rpgle|sqlrpgle|cl|clle|sql|txt)$/)?.[0]
    if (!extension || !ALLOWED_EXTENSIONS.includes(extension)) {
      return `Invalid file type. Supported: ${ALLOWED_EXTENSIONS.join(', ')}`
    }

    // Check size
    if (file.size > MAX_FILE_SIZE) {
      return `File size exceeds 10MB limit (${(file.size / (1024 * 1024)).toFixed(2)}MB)`
    }

    return null
  }

  const onDrop = useCallback(async (acceptedFiles: File[], rejectedFiles: any[]) => {
    if (!sessionId) {
      setUploadState({
        status: 'error',
        progress: 0,
        message: 'No upload session. Please refresh the page.',
        uploadingFiles: []
      })
      onUploadError?.('No upload session')
      return
    }

    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const error = `Cannot upload ${rejectedFiles.length} file(s). Check file type and size.`
      setUploadState({
        status: 'error',
        progress: 0,
        message: error,
        uploadingFiles: []
      })
      onUploadError?.(error)
      setTimeout(() => {
        setUploadState({ status: 'idle', progress: 0, message: '', uploadingFiles: [] })
      }, 5000)
      return
    }

    if (acceptedFiles.length === 0) return

    // Check max files
    if (acceptedFiles.length > maxFiles) {
      const error = `Maximum ${maxFiles} files per upload`
      setUploadState({
        status: 'error',
        progress: 0,
        message: error,
        uploadingFiles: []
      })
      onUploadError?.(error)
      setTimeout(() => {
        setUploadState({ status: 'idle', progress: 0, message: '', uploadingFiles: [] })
      }, 5000)
      return
    }

    // Validate all files
    const validationErrors: string[] = []
    acceptedFiles.forEach(file => {
      const error = validateFile(file)
      if (error) validationErrors.push(`${file.name}: ${error}`)
    })

    if (validationErrors.length > 0) {
      const error = validationErrors.join('\n')
      setUploadState({
        status: 'error',
        progress: 0,
        message: error,
        uploadingFiles: []
      })
      onUploadError?.(error)
      setTimeout(() => {
        setUploadState({ status: 'idle', progress: 0, message: '', uploadingFiles: [] })
      }, 5000)
      return
    }

    // Upload files
    setUploadState({
      status: 'uploading',
      progress: 0,
      message: `Uploading ${acceptedFiles.length} file(s)...`,
      uploadingFiles: acceptedFiles.map(f => f.name)
    })

    const uploadedFiles: CodeFile[] = []
    const errors: string[] = []

    for (let i = 0; i < acceptedFiles.length; i++) {
      const file = acceptedFiles[i]
      const formData = new FormData()
      formData.append('file', file)
      formData.append('session_id', sessionId)

      try {
        const response = await axios.post<CodeFile>(`${API_URL}/api/code/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const fileProgress = ((i / acceptedFiles.length) + (progressEvent.loaded / (progressEvent.total || progressEvent.loaded)) / acceptedFiles.length) * 100
            setUploadState(prev => ({
              ...prev,
              progress: Math.round(fileProgress),
              message: `Uploading ${file.name}... (${i + 1}/${acceptedFiles.length})`
            }))
          }
        })

        uploadedFiles.push(response.data)
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || `Failed to upload ${file.name}`
        errors.push(errorMsg)
      }
    }

    if (uploadedFiles.length > 0) {
      setUploadState({
        status: 'success',
        progress: 100,
        message: `✓ Successfully uploaded ${uploadedFiles.length} file(s)`,
        uploadingFiles: []
      })
      onUploadSuccess(uploadedFiles)

      // Reset after 3 seconds
      setTimeout(() => {
        setUploadState({ status: 'idle', progress: 0, message: '', uploadingFiles: [] })
      }, 3000)
    }

    if (errors.length > 0) {
      const errorMsg = errors.join('\n')
      setUploadState({
        status: 'error',
        progress: 0,
        message: errorMsg,
        uploadingFiles: []
      })
      onUploadError?.(errorMsg)

      // Reset after 5 seconds
      setTimeout(() => {
        setUploadState({ status: 'idle', progress: 0, message: '', uploadingFiles: [] })
      }, 5000)
    }
  }, [sessionId, onUploadSuccess, onUploadError, maxFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ALLOWED_EXTENSIONS,
      'application/octet-stream': ALLOWED_EXTENSIONS,
    },
    maxFiles,
    disabled: disabled || uploadState.status === 'uploading' || !sessionId,
  })

  const getStatusColor = () => {
    switch (uploadState.status) {
      case 'uploading':
        return 'border-blue-500 bg-blue-50'
      case 'success':
        return 'border-green-500 bg-green-50'
      case 'error':
        return 'border-red-500 bg-red-50'
      default:
        return isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
    }
  }

  const getStatusIcon = () => {
    if (uploadState.status === 'uploading') {
      return (
        <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      )
    }
    if (uploadState.status === 'success') {
      return (
        <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      )
    }
    if (uploadState.status === 'error') {
      return (
        <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )
    }
    return (
      <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    )
  }

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200 ${getStatusColor()} ${
          (disabled || uploadState.status === 'uploading' || !sessionId)
            ? 'opacity-50 cursor-not-allowed'
            : ''
        }`}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-4">
          {getStatusIcon()}

          {uploadState.status === 'idle' ? (
            isDragActive ? (
              <p className="text-blue-600 font-medium text-lg">Drop your code files here...</p>
            ) : (
              <div>
                <p className="text-gray-700 font-medium text-lg">Drag & drop code files here</p>
                <p className="text-sm text-gray-500 mt-2">or click to select files</p>
                <div className="mt-4 space-y-1 text-xs text-gray-400">
                  <p>Supported: .rpg, .rpgle, .sqlrpgle, .cl, .clle, .sql, .txt</p>
                  <p>Max file size: 10MB • Max {maxFiles} files per upload</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 justify-center">
                  <FileTypeIndicator fileName="example.rpgle" />
                  <FileTypeIndicator fileName="example.cl" />
                  <FileTypeIndicator fileName="example.sql" />
                </div>
              </div>
            )
          ) : (
            <div className="w-full max-w-md">
              <p className={`font-medium mb-2 ${
                uploadState.status === 'success' ? 'text-green-600' :
                uploadState.status === 'error' ? 'text-red-600' :
                'text-blue-600'
              }`}>
                {uploadState.message}
              </p>

              {uploadState.status === 'uploading' && (
                <>
                  <div className="w-full bg-gray-200 rounded-full h-3 mb-3">
                    <div
                      className="h-3 rounded-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${uploadState.progress}%` }}
                    ></div>
                  </div>
                  {uploadState.uploadingFiles.length > 0 && (
                    <div className="text-xs text-gray-500 space-y-1">
                      {uploadState.uploadingFiles.map((name, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                          <span className="truncate">{name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {uploadState.status === 'error' && (
        <Alert variant="error">
          <div className="whitespace-pre-line">{uploadState.message}</div>
        </Alert>
      )}

      {/* No Session Warning */}
      {!sessionId && (
        <Alert variant="warning">
          No upload session active. Please refresh the page to create a new session.
        </Alert>
      )}
    </div>
  )
}
