'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import AuthorPromptDialog from './AuthorPromptDialog'

interface FileUploadProps {
  onUploadSuccess: (filename: string) => void
}

interface UploadProgress {
  status: 'idle' | 'uploading' | 'processing' | 'success' | 'error' | 'needs_metadata'
  progress: number
  message: string
  filename?: string
  stats?: {
    chunks_created: number
    images_processed: number
    code_blocks_found: number
    total_pages: number
  }
  needsAuthor?: boolean
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    status: 'idle',
    progress: 0,
    message: ''
  })
  const [showAuthorPrompt, setShowAuthorPrompt] = useState(false)
  const [pendingFile, setPendingFile] = useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setUploadProgress({
      status: 'uploading',
      progress: 0,
      message: 'Uploading...',
      filename: file.name
    })

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post('http://localhost:8000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / (progressEvent.total || progressEvent.loaded)
          )
          setUploadProgress(prev => ({
            ...prev,
            progress: percentCompleted * 0.3, // Upload is 30% of total process
            message: `Uploading... ${percentCompleted}%`
          }))
        }
      })

      // Processing phase
      setUploadProgress(prev => ({
        ...prev,
        status: 'processing',
        progress: 30,
        message: 'Processing PDF...'
      }))

      // Simulate processing progress
      const processingInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev.progress >= 90) {
            clearInterval(processingInterval)
            return prev
          }
          return {
            ...prev,
            progress: prev.progress + 5,
            message: prev.progress < 60 ? 'Extracting text...' : 
                    prev.progress < 80 ? 'Processing images...' : 
                    'Creating embeddings...'
          }
        })
      }, 200)

      if (response.data.status === 'success') {
        clearInterval(processingInterval)
        
        setUploadProgress({
          status: 'success',
          progress: 100,
          message: 'Processing complete!',
          filename: file.name,
          stats: {
            chunks_created: response.data.chunks_created,
            images_processed: response.data.images_processed,
            code_blocks_found: response.data.code_blocks_found,
            total_pages: response.data.total_pages
          }
        })

        onUploadSuccess(file.name)
        
        // Reset after 3 seconds
        setTimeout(() => {
          setUploadProgress({
            status: 'idle',
            progress: 0,
            message: ''
          })
        }, 3000)
      } else if (response.data.status === 'needs_metadata') {
        clearInterval(processingInterval)
        
        setUploadProgress({
          status: 'needs_metadata',
          progress: 90,
          message: 'Please provide author information',
          filename: file.name,
          stats: {
            chunks_created: response.data.chunks_created,
            images_processed: response.data.images_processed,
            code_blocks_found: response.data.code_blocks_found,
            total_pages: response.data.total_pages
          },
          needsAuthor: true
        })
        
        setPendingFile(file.name)
        setShowAuthorPrompt(true)
      }
    } catch (err: any) {
      setUploadProgress({
        status: 'error',
        progress: 0,
        message: err.response?.data?.detail || 'Upload failed',
        filename: file.name
      })
      
      // Reset after 5 seconds
      setTimeout(() => {
        setUploadProgress({
          status: 'idle',
          progress: 0,
          message: ''
        })
      }, 5000)
    }
  }, [onUploadSuccess])

  const handleAuthorSubmit = async (author: string) => {
    if (!pendingFile) return
    
    try {
      const response = await axios.post('http://localhost:8000/complete-upload', {
        filename: pendingFile,
        author: author
      })
      
      if (response.data.status === 'success') {
        setUploadProgress({
          status: 'success',
          progress: 100,
          message: 'Processing complete!',
          filename: pendingFile,
          stats: uploadProgress.stats
        })
        
        onUploadSuccess(pendingFile)
        setShowAuthorPrompt(false)
        setPendingFile(null)
        
        // Reset after 3 seconds
        setTimeout(() => {
          setUploadProgress({
            status: 'idle',
            progress: 0,
            message: ''
          })
        }, 3000)
      }
    } catch (err: any) {
      setUploadProgress({
        status: 'error',
        progress: 0,
        message: err.response?.data?.detail || 'Failed to complete upload',
        filename: pendingFile
      })
      setShowAuthorPrompt(false)
      setPendingFile(null)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    disabled: uploadProgress.status === 'uploading' || uploadProgress.status === 'processing' || uploadProgress.status === 'needs_metadata',
  })

  const getStatusColor = () => {
    switch (uploadProgress.status) {
      case 'uploading':
      case 'processing':
        return 'text-blue-600'
      case 'needs_metadata':
        return 'text-yellow-600'
      case 'success':
        return 'text-green-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusIcon = () => {
    switch (uploadProgress.status) {
      case 'uploading':
      case 'processing':
        return (
          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        )
      case 'needs_metadata':
        return (
          <svg className="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      case 'success':
        return (
          <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )
      case 'error':
        return (
          <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )
      default:
        return (
          <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        )
    }
  }

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all-smooth ${
          isDragActive 
            ? 'border-blue-500 bg-blue-50' 
            : uploadProgress.status === 'idle'
            ? 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
            : 'border-gray-300 bg-gray-50'
        } ${
          uploadProgress.status === 'uploading' || uploadProgress.status === 'processing' || uploadProgress.status === 'needs_metadata'
            ? 'opacity-75 cursor-not-allowed' 
            : ''
        }`}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center gap-3">
          {getStatusIcon()}
          
          {uploadProgress.status === 'idle' ? (
            isDragActive ? (
              <p className="text-blue-600 font-medium">Drop the PDF here...</p>
            ) : (
              <div>
                <p className="text-gray-600 font-medium">Drag & drop a PDF here</p>
                <p className="text-sm text-gray-500 mt-1">or click to select</p>
                <p className="text-xs text-gray-400 mt-2">Max file size: 100MB</p>
              </div>
            )
          ) : (
            <div className="w-full max-w-xs">
              <div className="flex items-center justify-between mb-2">
                <span className={`text-sm font-medium ${getStatusColor()}`}>
                  {uploadProgress.message}
                </span>
                {uploadProgress.status !== 'error' && (
                  <span className="text-xs text-gray-500">
                    {uploadProgress.progress}%
                  </span>
                )}
              </div>
              
              {uploadProgress.filename && (
                <p className="text-xs text-gray-500 truncate mb-2">
                  {uploadProgress.filename}
                </p>
              )}
              
              {uploadProgress.status !== 'error' && (
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      uploadProgress.status === 'success' ? 'bg-green-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${uploadProgress.progress}%` }}
                  ></div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Success Stats */}
      {uploadProgress.status === 'success' && uploadProgress.stats && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-green-800 mb-2">
            ✅ Processing Complete!
          </h4>
          <div className="grid grid-cols-2 gap-2 text-xs text-green-700">
            <div className="flex items-center gap-1">
              <span>📄</span>
              <span>{uploadProgress.stats.total_pages} pages</span>
            </div>
            <div className="flex items-center gap-1">
              <span>📝</span>
              <span>{uploadProgress.stats.chunks_created} chunks</span>
            </div>
            <div className="flex items-center gap-1">
              <span>🖼️</span>
              <span>{uploadProgress.stats.images_processed} images</span>
            </div>
            <div className="flex items-center gap-1">
              <span>💻</span>
              <span>{uploadProgress.stats.code_blocks_found} code blocks</span>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {uploadProgress.status === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="text-sm font-semibold text-red-800">Upload Failed</h4>
              <p className="text-sm text-red-700 mt-1">{uploadProgress.message}</p>
            </div>
          </div>
        </div>
      )}

      {/* Author Prompt Dialog */}
      {showAuthorPrompt && (
        <AuthorPromptDialog
          isOpen={showAuthorPrompt}
          onClose={() => {
            setShowAuthorPrompt(false)
            setPendingFile(null)
            setUploadProgress({
              status: 'idle',
              progress: 0,
              message: ''
            })
          }}
          onSubmit={handleAuthorSubmit}
          filename={pendingFile || ''}
        />
      )}
    </div>
  )
}