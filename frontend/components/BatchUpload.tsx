'use client'

import { useCallback, useState, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'

interface BatchUploadProps {
  onUploadComplete: () => void
}

interface FileStatus {
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  message: string
  stats?: {
    chunks_created: number
    images_processed: number
    code_blocks_found: number
    total_pages: number
    category: string
  }
}

interface BatchProgress {
  batch_id: string
  total_files: number
  processed_files: number
  current_file: string | null
  files_status: Record<string, FileStatus>
  overall_progress: number
  status: string
  summary?: {
    successful: number
    failed: number
    total: number
  }
}

export default function BatchUpload({ onUploadComplete }: BatchUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  // Poll for batch status
  useEffect(() => {
    if (!batchProgress || batchProgress.status === 'completed') return

    const interval = setInterval(async () => {
      try {
        const response = await axios.get(
          `http://localhost:8000/batch-upload/status/${batchProgress.batch_id}`
        )
        setBatchProgress(response.data)
        
        if (response.data.status === 'completed') {
          setIsUploading(false)
          onUploadComplete()
        }
      } catch (error) {
        console.error('Error fetching batch status:', error)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [batchProgress, onUploadComplete])

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Validate file sizes
    const maxFileSize = 100 * 1024 * 1024 // 100MB
    const invalidFiles = acceptedFiles.filter(file => file.size > maxFileSize)
    
    if (invalidFiles.length > 0) {
      alert(`The following files exceed the 100MB limit:\n${invalidFiles.map(f => `${f.name} (${(f.size / 1024 / 1024).toFixed(2)}MB)`).join('\n')}`)
      return
    }
    
    setSelectedFiles(acceptedFiles)
  }, [])

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return

    setIsUploading(true)
    const formData = new FormData()
    
    selectedFiles.forEach((file) => {
      formData.append('files', file)
    })

    try {
      const response = await axios.post('http://localhost:8000/batch-upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      })

      setBatchProgress({
        batch_id: response.data.batch_id,
        total_files: selectedFiles.length,
        processed_files: 0,
        current_file: null,
        files_status: {},
        overall_progress: 0,
        status: 'processing'
      })
    } catch (error: any) {
      console.error('Error uploading files:', error)
      setIsUploading(false)
      alert(error.response?.data?.detail || 'Upload failed')
    }
  }

  const handleReset = () => {
    setSelectedFiles([])
    setBatchProgress(null)
    setIsUploading(false)
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: true,
    disabled: isUploading,
  })

  const getFileStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading':
      case 'processing':
        return '⏳'
      case 'completed':
        return '✅'
      case 'error':
        return '❌'
      default:
        return '📄'
    }
  }

  const getFileStatusColor = (status: string) => {
    switch (status) {
      case 'uploading':
      case 'processing':
        return 'text-blue-600'
      case 'completed':
        return 'text-green-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className="space-y-6">
      {/* Drop Zone */}
      {!isUploading && !batchProgress && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
            isDragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }`}
        >
          <input {...getInputProps()} />
          <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          {isDragActive ? (
            <p className="text-blue-600 font-medium text-lg">Drop the PDFs here...</p>
          ) : (
            <div>
              <p className="text-gray-600 font-medium text-lg">Drag & drop multiple PDFs here</p>
              <p className="text-sm text-gray-500 mt-1">or click to select files</p>
              <p className="text-xs text-gray-400 mt-2">You can upload up to 113 PDFs at once (max 100MB each)</p>
            </div>
          )}
        </div>
      )}

      {/* Selected Files */}
      {selectedFiles.length > 0 && !isUploading && !batchProgress && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-800">
              Selected Files ({selectedFiles.length})
            </h3>
            <button
              onClick={handleReset}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              Clear all
            </button>
          </div>
          <div className="max-h-48 overflow-y-auto space-y-1">
            {selectedFiles.map((file, index) => (
              <div key={index} className="flex items-center gap-2 text-sm text-gray-600">
                <span>📄</span>
                <span className="truncate">{file.name}</span>
                <span className="text-xs text-gray-400">
                  ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </span>
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            className="mt-4 w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Upload {selectedFiles.length} Files
          </button>
        </div>
      )}

      {/* Upload Progress */}
      {batchProgress && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-800">
                Batch Upload Progress
              </h3>
              <span className="text-sm text-gray-600">
                {batchProgress.processed_files} / {batchProgress.total_files} files
              </span>
            </div>
            
            {/* Overall Progress Bar */}
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="h-3 bg-blue-600 rounded-full transition-all duration-300"
                style={{ width: `${batchProgress.overall_progress}%` }}
              ></div>
            </div>
            <p className="text-sm text-gray-600 mt-1">
              {batchProgress.overall_progress}% complete
            </p>
          </div>

          {/* Current File */}
          {batchProgress.current_file && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm font-medium text-blue-800">
                Currently processing: {batchProgress.current_file}
              </p>
            </div>
          )}

          {/* File List */}
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {Object.entries(batchProgress.files_status).map(([filename, fileStatus]) => (
              <div key={filename} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="flex items-center gap-2 flex-1">
                  <span>{getFileStatusIcon(fileStatus.status)}</span>
                  <span className={`text-sm ${getFileStatusColor(fileStatus.status)} truncate`}>
                    {filename}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {fileStatus.status === 'completed' && fileStatus.stats && (
                    <div className="flex items-center gap-2 text-xs text-gray-600">
                      <span className="bg-gray-200 px-2 py-1 rounded">
                        {fileStatus.stats.category}
                      </span>
                      <span>{fileStatus.stats.total_pages}p</span>
                      <span>{fileStatus.stats.chunks_created}ch</span>
                      {fileStatus.stats.images_processed > 0 && (
                        <span>🖼️ {fileStatus.stats.images_processed}</span>
                      )}
                      {fileStatus.stats.code_blocks_found > 0 && (
                        <span>💻 {fileStatus.stats.code_blocks_found}</span>
                      )}
                    </div>
                  )}
                  {fileStatus.status === 'error' && (
                    <span className="text-xs text-red-600">{fileStatus.message}</span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          {batchProgress.status === 'completed' && batchProgress.summary && (
            <div className="mt-4 p-4 bg-green-50 rounded-lg">
              <h4 className="font-semibold text-green-800 mb-2">Upload Complete!</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <p className="text-green-600 font-semibold text-lg">
                    {batchProgress.summary.successful}
                  </p>
                  <p className="text-gray-600">Successful</p>
                </div>
                <div className="text-center">
                  <p className="text-red-600 font-semibold text-lg">
                    {batchProgress.summary.failed}
                  </p>
                  <p className="text-gray-600">Failed</p>
                </div>
                <div className="text-center">
                  <p className="text-gray-800 font-semibold text-lg">
                    {batchProgress.summary.total}
                  </p>
                  <p className="text-gray-600">Total</p>
                </div>
              </div>
              <button
                onClick={handleReset}
                className="mt-4 w-full bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
              >
                Upload More Files
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}